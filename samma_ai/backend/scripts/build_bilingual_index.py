#!/usr/bin/env python3
"""
build_bilingual_index.py — Build Qdrant 'tipitaka_bilingual' collection.

Embeds English text (falling back to Pali) for each mula paragraph so that
English-language queries return semantically relevant results.

Does NOT replace the existing 'tipitaka_mula' (Pali-only) collection.

Usage:
    cd backend
    python scripts/build_bilingual_index.py
    python scripts/build_bilingual_index.py --force    # re-index even if populated
    python scripts/build_bilingual_index.py --batch-size 32

Requires:
    - Qdrant running: docker run -d --name qdrant -p 6333:6333 \\
        -v ~/.qdrant:/qdrant/storage qdrant/qdrant
    - pali_translations already populated (run populate_translations.py first)
    - sentence-transformers and torch installed
"""

import sys
import os
import time
import sqlite3
import logging
import argparse
import traceback

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


def load_bilingual_passages(db_path: str):
    """
    Load all mula paragraphs joined with pali_translations.

    Returns list of dicts with keys:
        passage_id, book_id, paragraph_number, pali_text,
        english_text, has_translation, translation_source,
        pitaka_id, nikaya_id, sutta_id
    """
    logger.info("Reading mula passages + translations from %s ...", db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                par.id            AS passage_id,
                par.book_id,
                par.sutta_id,
                par.paragraph_number,
                par.pali_text,
                pt.english_translation,
                pt.source         AS translation_source,
                b.pitaka_id,
                b.nikaya_id
            FROM paragraphs par
            LEFT JOIN books b ON par.book_id = b.id
            LEFT JOIN pali_translations pt ON par.pali_text = pt.pali_text
            WHERE par.text_layer = 'mula'
            ORDER BY par.id
        """)
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    logger.info("Loaded %d mula passages", len(rows))
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Build Qdrant bilingual (English-embedded) Tipitaka index"
    )
    parser.add_argument('--force', action='store_true',
                        help='Re-index even if collection already populated')
    parser.add_argument('--batch-size', type=int, default=64,
                        help='Embedding batch size (default 64)')
    parser.add_argument('--collection', type=str,
                        default=os.environ.get('QDRANT_BILINGUAL_COLLECTION', 'tipitaka_bilingual'))
    parser.add_argument('--db-path', type=str,
                        default=os.environ.get(
                            'TIPITAKA_DB_PATH',
                            os.path.join(BACKEND_DIR, '..', 'database', 'tipitaka_ultimate.db')
                        ))
    parser.add_argument('--qdrant-host', type=str,
                        default=os.environ.get('QDRANT_HOST', 'localhost'))
    parser.add_argument('--qdrant-port', type=int,
                        default=int(os.environ.get('QDRANT_PORT', '6333')))
    args = parser.parse_args()

    db_path = os.path.normpath(args.db_path)
    if not os.path.exists(db_path):
        logger.error("Database not found: %s", db_path)
        sys.exit(1)

    # ── connect to Qdrant ─────────────────────────────────────────────────────
    logger.info("Connecting to Qdrant at %s:%d ...", args.qdrant_host, args.qdrant_port)
    try:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(host=args.qdrant_host, port=args.qdrant_port)
        qdrant.get_collections()  # connectivity probe
        logger.info("Qdrant connected")
    except Exception as e:
        logger.error(
            "Cannot connect to Qdrant: %s\n"
            "Start with: docker run -d --name qdrant -p 6333:6333 "
            "-v ~/.qdrant:/qdrant/storage qdrant/qdrant", e
        )
        sys.exit(1)

    # ── load EmbeddingService ─────────────────────────────────────────────────
    from app.services.embedding_service import EmbeddingService
    svc = EmbeddingService()

    # ── ensure collection ─────────────────────────────────────────────────────
    svc.ensure_collection(qdrant, args.collection)

    if svc.is_collection_populated(qdrant, args.collection) and not args.force:
        info = qdrant.get_collection(args.collection)
        count = getattr(info, 'points_count', None) or getattr(info, 'vectors_count', None)
        logger.info(
            "Collection '%s' already has %s vectors. Use --force to re-index.",
            args.collection, f"{count:,}" if count else "?"
        )
        sys.exit(0)

    # ── load passages ─────────────────────────────────────────────────────────
    rows = load_bilingual_passages(db_path)
    total = len(rows)
    if total == 0:
        logger.error("No mula passages found in %s", db_path)
        sys.exit(1)

    has_translation = sum(1 for r in rows if r['english_translation'])
    logger.info(
        "Passages: %d total  |  %d with English translation (%.1f%%)",
        total, has_translation, has_translation / total * 100
    )
    logger.info("Collection: %s  |  batch_size: %d", args.collection, args.batch_size)

    # ── batch-encode and upsert ───────────────────────────────────────────────
    from qdrant_client.models import PointStruct

    t0 = time.time()
    indexed = 0
    failed_batches = 0
    total_batches = (total + args.batch_size - 1) // args.batch_size

    for batch_start in range(0, total, args.batch_size):
        batch = rows[batch_start: batch_start + args.batch_size]
        batch_num = batch_start // args.batch_size + 1

        # Use English if available, else fall back to Pali
        texts_to_embed = [
            r['english_translation'] if r['english_translation'] else r['pali_text']
            for r in batch
        ]

        # Encode
        try:
            vectors = svc.encode_passages(texts_to_embed)
        except Exception as exc:
            logger.error(
                "Encoding FAILED for batch %d/%d (passages %d–%d) — %s\n%s — SKIPPING.",
                batch_num, total_batches,
                batch_start + 1, batch_start + len(batch),
                exc, traceback.format_exc()
            )
            failed_batches += 1
            continue

        # Build point structs
        points = []
        for i, row in enumerate(batch):
            point_id = batch_start + i + 1  # stable 1-indexed integer
            points.append(PointStruct(
                id=point_id,
                vector=vectors[i].tolist(),
                payload={
                    'passage_id':        row['passage_id'],
                    'book_id':           row['book_id'],
                    'sutta_id':          row['sutta_id'],
                    'nikaya_id':         row['nikaya_id'],
                    'pitaka_id':         row['pitaka_id'],
                    'paragraph_number':  row['paragraph_number'],
                    'pali_text':         (row['pali_text'] or '')[:300],
                    'english_text':      (row['english_translation'] or '')[:300],
                    'has_translation':   bool(row['english_translation']),
                    'translation_source': row['translation_source'] or 'none',
                },
            ))

        # Upsert to Qdrant
        try:
            qdrant.upsert(collection_name=args.collection, points=points)
            indexed += len(batch)
        except Exception as exc:
            logger.error(
                "Qdrant upsert FAILED for batch %d/%d — %s\n%s — SKIPPING.",
                batch_num, total_batches, exc, traceback.format_exc()
            )
            failed_batches += 1
            continue

        # progress every 10 batches
        if batch_num % 10 == 0 or batch_num == total_batches:
            elapsed = time.time() - t0
            pct = indexed / total * 100
            rate = indexed / elapsed if elapsed > 0 else 0
            eta = (total - indexed) / rate if rate > 0 else 0
            logger.info(
                "Progress: %d/%d (%.1f%%)  elapsed=%.1fs  rate=%.0f/s  eta=%.0fs",
                indexed, total, pct, elapsed, rate, eta
            )

    # ── summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    mins, secs = int(elapsed // 60), int(elapsed % 60)

    if failed_batches:
        logger.warning(
            "FINISHED with %d failed batches. indexed=%d  total=%d",
            failed_batches, indexed, total
        )
    else:
        logger.info(
            "COMPLETE — indexed %d passages in %dm %ds  collection=%s",
            indexed, mins, secs, args.collection
        )

    print(f"\n✅ Indexed {indexed:,} passages in {mins}m {secs}s")
    print(f"   Collection: {args.collection}  |  "
          f"Host: {args.qdrant_host}:{args.qdrant_port}")
    print(f"   With English: {has_translation:,}  |  "
          f"Pali-only: {total - has_translation:,}")


if __name__ == '__main__':
    main()
