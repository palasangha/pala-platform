#!/usr/bin/env python3
"""
populate_translations.py — Pre-populate pali_translations cache for all mula paragraphs.

Strategy per paragraph:
  1. Check pages table (DB translations) — source='db', expires_at=NULL (permanent)
  2. If not found, call Ollama if available — source='ollama', 7-day TTL
  3. If Ollama unavailable or --skip-ollama, skip (will translate on-demand at query time)

Usage:
    cd backend
    python scripts/populate_translations.py
    python scripts/populate_translations.py --skip-ollama  # DB-only pass
    python scripts/populate_translations.py --dry-run      # preview without writing
    python scripts/populate_translations.py --force        # re-process all, even cached
    python scripts/populate_translations.py --limit 1000 --offset 0
"""

import sys
import os
import re
import sqlite3
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional

# ── path setup ───────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


# ── book-ID mapping (duplicated from TipitakaService to avoid Flask context) ─

VINAYA_MAP = {
    'vi1m': 'annya_pe_parajika',
    'vi2m': 'annya_pe_pacittiya',
    'vi3m': 'annya_pe_mahavagga',
    'vi4m': 'annya_pe_culavagga',
    'vi5m': 'annya_pe_parivara',
}

ABHIDHAMMA_MAP = {
    'abh01': 'annya_pe_abh01',
    'abh02': 'annya_pe_abh02',
    'abh03': 'annya_pe_abh03',
    'abh04': 'annya_pe_abh04',
    'abh05': 'annya_pe_abh05',
    'abh06': 'annya_pe_abh06',
    'abh07': 'annya_pe_abh07',
}


def get_translation_book_id(pali_book_id: str) -> Optional[str]:
    """Map Pali mula book ID to its annya_pe translation book ID."""
    if not pali_book_id:
        return None

    base_id = pali_book_id
    if base_id.endswith('m'):
        base_id = base_id[:-1]

    if base_id.startswith(('dn', 'mn', 'sn', 'an')):
        return f"annya_pe_{base_id}"

    if pali_book_id in VINAYA_MAP:
        return VINAYA_MAP[pali_book_id]

    return ABHIDHAMMA_MAP.get(pali_book_id)


def fetch_translation_from_db(cursor, pali_book_id: str, para_num: int) -> Optional[str]:
    """Fetch English translation from pages table (same logic as TipitakaService)."""
    trans_book_id = get_translation_book_id(pali_book_id)
    if not trans_book_id:
        return None

    cursor.execute("""
        SELECT content FROM pages
        WHERE bookid = ? AND paranum = ?
        LIMIT 1
    """, [trans_book_id, f'-{para_num}-'])

    result = cursor.fetchone()
    if not result:
        return None

    content = result[0]
    matches = re.findall(r'<span class="t1">([^<]+)</span>', content)
    if not matches:
        matches = re.findall(r'<span class="t5">([^<]+)</span>', content)

    if matches:
        text = " ".join(matches).strip()
        return text if text else None

    return None


# ── Ollama helpers ────────────────────────────────────────────────────────────

def is_ollama_available(endpoint: str) -> bool:
    """Check if Ollama server is reachable."""
    try:
        import requests
        resp = requests.get(f"{endpoint}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def call_ollama(pali_text: str, endpoint: str, model: str, timeout: int) -> Optional[str]:
    """Call Ollama to translate a Pali passage. Returns translation or None."""
    try:
        import requests
        prompt = (
            "Translate this Pali text to English. "
            "Provide only the English translation, no explanations:\n\n"
            f"Pali: {pali_text}\n\nEnglish translation:"
        )
        payload = {"model": model, "prompt": prompt, "stream": False}
        resp = requests.post(f"{endpoint}/api/generate", json=payload, timeout=timeout)
        if resp.status_code == 200:
            translation = resp.json().get('response', '').strip()
            return translation if translation else None
        logger.warning("Ollama non-200 status=%d", resp.status_code)
        return None
    except Exception as e:
        logger.debug("Ollama call failed — %s", e)
        return None


# ── cache helpers ─────────────────────────────────────────────────────────────

def is_already_cached(cursor, pali_text: str) -> bool:
    """Return True if pali_text is already in pali_translations."""
    cursor.execute(
        "SELECT 1 FROM pali_translations WHERE pali_text = ? LIMIT 1",
        (pali_text,)
    )
    return cursor.fetchone() is not None


def save_translation(cursor, pali_text: str, english: str, reference: str,
                     source: str, model: str, cache_ttl: int, dry_run: bool) -> None:
    """Insert or replace a translation in pali_translations."""
    if dry_run:
        return

    expires_at = None
    if source == 'ollama':
        expires_at = (datetime.utcnow() + timedelta(seconds=cache_ttl)).isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO pali_translations
            (pali_text, english_translation, reference, model_used, source, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        pali_text,
        english,
        reference,
        model if source == 'ollama' else 'pages_table',
        source,
        datetime.utcnow().isoformat(),
        expires_at,
    ))


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Pre-populate pali_translations cache for all mula paragraphs'
    )
    parser.add_argument('--db-path', type=str,
                        default=os.environ.get(
                            'TIPITAKA_DB_PATH',
                            os.path.join(BACKEND_DIR, '..', 'database', 'tipitaka_ultimate.db')
                        ),
                        help='Path to tipitaka_ultimate.db')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max paragraphs to process (0 = all)')
    parser.add_argument('--offset', type=int, default=0,
                        help='Skip first N paragraphs')
    parser.add_argument('--batch-size', type=int, default=500,
                        help='Commit batch size (default 500)')
    parser.add_argument('--skip-ollama', action='store_true',
                        help='Only use pages table, never call Ollama')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview counts without writing to DB')
    parser.add_argument('--force', action='store_true',
                        help='Re-process paragraphs already in pali_translations')
    parser.add_argument('--ollama-endpoint', type=str,
                        default=os.environ.get('OLLAMA_TRANSLATION_ENDPOINT', 'http://localhost:11434'))
    parser.add_argument('--ollama-model', type=str,
                        default=os.environ.get('OLLAMA_TRANSLATION_MODEL', 'deepseek-r1:32b'))
    parser.add_argument('--ollama-timeout', type=int,
                        default=int(os.environ.get('OLLAMA_TRANSLATION_TIMEOUT', '90')))
    parser.add_argument('--cache-ttl', type=int,
                        default=int(os.environ.get('TRANSLATION_CACHE_TTL', '604800')),
                        help='Ollama translation TTL in seconds (default 7 days)')
    args = parser.parse_args()

    db_path = os.path.normpath(args.db_path)
    if not os.path.exists(db_path):
        logger.error("Database not found: %s", db_path)
        sys.exit(1)

    logger.info("Database: %s", db_path)
    logger.info("dry_run=%s  force=%s  skip_ollama=%s  batch_size=%d",
                args.dry_run, args.force, args.skip_ollama, args.batch_size)

    # ── check Ollama availability once upfront ────────────────────────────────
    ollama_available = False
    if not args.skip_ollama:
        ollama_available = is_ollama_available(args.ollama_endpoint)
        logger.info("Ollama available=%s  endpoint=%s  model=%s",
                    ollama_available, args.ollama_endpoint, args.ollama_model)
    else:
        logger.info("--skip-ollama set — skipping Ollama entirely")

    # ── load all mula paragraphs ──────────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        sql = """
            SELECT par.id, par.book_id, par.paragraph_number, par.pali_text
            FROM paragraphs par
            WHERE par.text_layer = 'mula'
            ORDER BY par.id
        """
        if args.limit > 0:
            sql += f" LIMIT {args.limit} OFFSET {args.offset}"
        elif args.offset > 0:
            sql += f" LIMIT -1 OFFSET {args.offset}"

        cursor.execute(sql)
        rows = cursor.fetchall()
        total = len(rows)
        logger.info("Loaded %d mula paragraphs from SQLite", total)

        if total == 0:
            logger.error("No mula paragraphs found — check text_layer='mula' rows in %s", db_path)
            sys.exit(1)

        # counters
        db_found = 0
        ollama_translated = 0
        skipped_cached = 0
        skipped_no_translation = 0
        errors = 0

        t0 = time.time()

        for i, row in enumerate(rows):
            pali_text = row['pali_text']
            book_id = row['book_id']
            para_num = row['paragraph_number']
            reference = f"{book_id}:{para_num}"

            # skip if already cached (unless --force)
            if not args.force and is_already_cached(cursor, pali_text):
                skipped_cached += 1
                continue

            try:
                # 1. Try pages table (DB)
                english = fetch_translation_from_db(cursor, book_id, para_num)

                if english:
                    save_translation(
                        cursor, pali_text, english, reference,
                        source='db', model='pages_table',
                        cache_ttl=args.cache_ttl, dry_run=args.dry_run
                    )
                    db_found += 1

                elif ollama_available and not args.skip_ollama:
                    # 2. Fallback to Ollama
                    translation = call_ollama(
                        pali_text, args.ollama_endpoint,
                        args.ollama_model, args.ollama_timeout
                    )
                    if translation:
                        save_translation(
                            cursor, pali_text, translation, reference,
                            source='ollama', model=args.ollama_model,
                            cache_ttl=args.cache_ttl, dry_run=args.dry_run
                        )
                        ollama_translated += 1
                    else:
                        skipped_no_translation += 1
                else:
                    skipped_no_translation += 1

            except Exception as e:
                logger.warning("Error on para id=%d book=%s para=%s — %s",
                               row['id'], book_id, para_num, e)
                errors += 1

            # commit in batches
            if not args.dry_run and (i + 1) % args.batch_size == 0:
                conn.commit()

            # progress every 1000
            if (i + 1) % 1000 == 0 or (i + 1) == total:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                logger.info(
                    "[%d/%d %.1f%%] db=%d  ollama=%d  cached_skip=%d  "
                    "no_trans=%d  errors=%d  rate=%.0f/s",
                    i + 1, total, (i + 1) / total * 100,
                    db_found, ollama_translated, skipped_cached,
                    skipped_no_translation, errors, rate
                )

        # final commit
        if not args.dry_run:
            conn.commit()

    finally:
        conn.close()

    elapsed = time.time() - t0
    mins, secs = int(elapsed // 60), int(elapsed % 60)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Processed {total:,} paragraphs in {mins}m {secs}s")
    print(f"  DB translations found:    {db_found:,}")
    print(f"  Ollama translations:       {ollama_translated:,}")
    print(f"  Skipped (already cached):  {skipped_cached:,}")
    print(f"  Skipped (no translation):  {skipped_no_translation:,}")
    print(f"  Errors:                    {errors:,}")

    if not args.dry_run:
        print(f"\nVerify: SELECT COUNT(*), source FROM pali_translations GROUP BY source;")


if __name__ == '__main__':
    main()
