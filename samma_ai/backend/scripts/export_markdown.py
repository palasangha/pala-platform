#!/usr/bin/env python3
"""
export_markdown.py — Export each sutta as a clean Markdown file.

Output: database/suttas_md/{nikaya}/{sutta_id}.md
  e.g.  database/suttas_md/dn/dn1.md
        database/suttas_md/mn/mn22.md

Format per file:
  # DN 1 — Brahmajālasutta
  *The All-Embracing Net of Views*

  **Pitaka:** Suttapiṭaka | **Nikaya:** Dīghanikāya

  ---

  ## Paragraph 1

  **Pali:** Evaṃ me sutaṃ...

  **English:** So I have heard...

  ---

Usage:
    cd backend
    python scripts/export_markdown.py
    python scripts/export_markdown.py --nikaya dn         # single nikaya
    python scripts/export_markdown.py --with-commentary    # include attha layer
    python scripts/export_markdown.py --overwrite          # overwrite existing files
    python scripts/export_markdown.py --output-dir /tmp/suttas
"""

import sys
import os
import re
import sqlite3
import argparse
import logging
from pathlib import Path

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


def strip_html(html: str) -> str:
    """Remove HTML tags and clean whitespace."""
    if not html:
        return ''
    text = re.sub(r'<[^>]+>', '', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_sutta_title(sutta_row) -> str:
    """Build a human-readable title like 'DN 1 — Brahmajālasutta'."""
    # Use abbreviation field if available (e.g. 'DN 1'), else derive from sutta_id
    abbreviation = sutta_row.get('abbreviation') or ''
    name_pali = sutta_row.get('name_pali') or ''
    title_parts = []

    if abbreviation:
        title_parts.append(abbreviation)
    else:
        sutta_id = sutta_row['id'] or ''
        m = re.search(r'(\d+)', sutta_id)
        number = m.group(1) if m else ''
        title_parts.append(f"{sutta_id.upper()}" if not number else sutta_id.upper())

    if name_pali:
        title_parts.append(name_pali)

    return ' — '.join(title_parts)


def nikaya_long_name(nikaya_id: str) -> str:
    names = {
        'dn': 'Dīghanikāya',
        'mn': 'Majjhimanikāya',
        'sn': 'Saṃyuttanikāya',
        'an': 'Aṅguttaranikāya',
        'kn': 'Khuddakanikāya',
        'vi': 'Vinayapiṭaka',
        'vinaya': 'Vinayapiṭaka',
        'abh': 'Abhidhammapiṭaka',
        'abhidhamma': 'Abhidhammapiṭaka',
    }
    return names.get((nikaya_id or '').lower(), nikaya_id or '')


def pitaka_long_name(pitaka_id: str) -> str:
    names = {
        'sut': 'Suttapiṭaka',
        'sutta': 'Suttapiṭaka',
        'vin': 'Vinayapiṭaka',
        'vinaya': 'Vinayapiṭaka',
        'abh': 'Abhidhammapiṭaka',
        'abhidhamma': 'Abhidhammapiṭaka',
    }
    return names.get((pitaka_id or '').lower(), pitaka_id or '')


def render_sutta_md(sutta_row, paragraphs) -> str:
    """Render a complete sutta to Markdown string."""
    title = format_sutta_title(sutta_row)
    subtitle = strip_html(sutta_row.get('name_english') or sutta_row.get('summary') or '')
    nikaya = nikaya_long_name(sutta_row.get('nikaya_id') or '')
    pitaka = pitaka_long_name(sutta_row.get('pitaka_id') or '')

    lines = [f"# {title}"]
    if subtitle:
        lines.append(f"*{subtitle}*")
    lines.append('')

    meta_parts = []
    if pitaka:
        meta_parts.append(f"**Pitaka:** {pitaka}")
    if nikaya:
        meta_parts.append(f"**Nikaya:** {nikaya}")
    if meta_parts:
        lines.append(' | '.join(meta_parts))
        lines.append('')

    lines.append('---')
    lines.append('')

    for para in paragraphs:
        para_num = para['paragraph_number']
        pali = (para['pali_text'] or '').strip()
        english = (para['english_translation'] or '').strip()
        layer = para.get('text_layer', 'mula')

        if layer == 'attha':
            lines.append(f"## Commentary — {para_num}")
        else:
            lines.append(f"## Paragraph {para_num}")
        lines.append('')

        if pali:
            lines.append(f"**Pali:** {pali}")
            lines.append('')

        if english:
            lines.append(f"**English:** {english}")
            lines.append('')

        lines.append('---')
        lines.append('')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Export each sutta as a clean Markdown file'
    )
    parser.add_argument('--db-path', type=str,
                        default=os.environ.get(
                            'TIPITAKA_DB_PATH',
                            os.path.join(BACKEND_DIR, '..', 'database', 'tipitaka_ultimate.db')
                        ))
    parser.add_argument('--output-dir', type=str,
                        default=os.path.join(BACKEND_DIR, '..', 'database', 'suttas_md'),
                        help='Output directory (default: ../../database/suttas_md)')
    parser.add_argument('--nikaya', type=str, default='',
                        help='Only export this nikaya (e.g. dn, mn, sn, an)')
    parser.add_argument('--with-commentary', action='store_true',
                        help='Include attha (commentary) layer paragraphs')
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite existing .md files')
    args = parser.parse_args()

    db_path = os.path.normpath(args.db_path)
    if not os.path.exists(db_path):
        logger.error("Database not found: %s", db_path)
        sys.exit(1)

    output_dir = Path(os.path.normpath(args.output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_dir)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        # Normalize nikaya filter — suttas table uses full names (e.g. 'digha', not 'dn')
        NIKAYA_ALIAS = {
            'dn': 'digha', 'mn': 'majjhima', 'sn': 'samyutta', 'an': 'anguttara',
            'kn': 'khuddaka', 'vi': 'vinaya', 'vinaya': 'vinaya',
            'abh': 'abhidhamma', 'abhidhamma': 'abhidhamma',
        }
        nikaya_filter = NIKAYA_ALIAS.get(args.nikaya.lower(), args.nikaya.lower()) if args.nikaya else ''

        # Load all suttas
        if nikaya_filter:
            cursor.execute("""
                SELECT s.id, s.name_pali, s.name_english, s.sutta_number,
                       s.abbreviation, s.summary, s.nikaya_id, b.pitaka_id
                FROM suttas s
                LEFT JOIN books b ON s.book_id = b.id
                WHERE LOWER(s.nikaya_id) = ?
                ORDER BY s.id
            """, [nikaya_filter])
        else:
            cursor.execute("""
                SELECT s.id, s.name_pali, s.name_english, s.sutta_number,
                       s.abbreviation, s.summary, s.nikaya_id, b.pitaka_id
                FROM suttas s
                LEFT JOIN books b ON s.book_id = b.id
                ORDER BY s.id
            """)
        suttas = cursor.fetchall()
        total_suttas = len(suttas)
        logger.info("Found %d suttas to export", total_suttas)

        if total_suttas == 0:
            logger.warning("No suttas found — check suttas table")
            sys.exit(0)

        # Layers to include
        layers = ['mula']
        if args.with_commentary:
            layers.append('attha')
        layer_sql = ','.join(['?' for _ in layers])

        written = 0
        skipped_no_para = 0
        skipped_exists = 0
        errors = 0

        for idx, sutta in enumerate(suttas):
            sutta_id = sutta['id']
            nikaya_id = (sutta['nikaya_id'] or 'unknown').lower()

            # Determine output path
            nikaya_dir = output_dir / nikaya_id
            nikaya_dir.mkdir(parents=True, exist_ok=True)
            out_path = nikaya_dir / f"{sutta_id}.md"

            if out_path.exists() and not args.overwrite:
                skipped_exists += 1
                continue

            try:
                # Fetch paragraphs with translations
                cursor.execute(f"""
                    SELECT
                        par.paragraph_number,
                        par.pali_text,
                        par.text_layer,
                        par.order_index,
                        pt.english_translation
                    FROM paragraphs par
                    LEFT JOIN pali_translations pt ON par.pali_text = pt.pali_text
                    WHERE par.sutta_id = ?
                      AND par.text_layer IN ({layer_sql})
                    ORDER BY par.order_index, par.paragraph_number
                """, [sutta_id] + layers)
                paragraphs = cursor.fetchall()

                if not paragraphs:
                    skipped_no_para += 1
                    continue

                md_content = render_sutta_md(dict(sutta), [dict(p) for p in paragraphs])
                out_path.write_text(md_content, encoding='utf-8')
                written += 1

            except Exception as e:
                logger.warning("Error exporting sutta '%s' — %s", sutta_id, e)
                errors += 1

            # progress every 100
            if (idx + 1) % 100 == 0 or (idx + 1) == total_suttas:
                logger.info(
                    "[%d/%d]  written=%d  skipped_no_para=%d  "
                    "skipped_exists=%d  errors=%d",
                    idx + 1, total_suttas, written,
                    skipped_no_para, skipped_exists, errors
                )

    finally:
        conn.close()

    print(f"\n✅ Export complete")
    print(f"   Written:              {written:,}")
    print(f"   Skipped (no paras):   {skipped_no_para:,}")
    print(f"   Skipped (exists):     {skipped_exists:,}")
    print(f"   Errors:               {errors:,}")
    print(f"   Output: {output_dir}")
    print(f"\nSample: {output_dir}/dn/dn1.md")


if __name__ == '__main__':
    main()
