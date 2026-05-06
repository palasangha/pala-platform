#!/usr/bin/env python3
"""
Bulk reupload script for storage-agent.

Usage:
  venv/bin/python scripts/reupload_docs.py /path/to/folder

This script calls `tool_store_document` for each file in the folder. It supports:
- plain text files (.txt, .md) - stored as `processed_data.content`.
- JSON files containing a dict with `processed_data` - passed through (tool will promote nested text).

After storing each file the script runs a quick search for a unique token (inserted if missing)
to verify that the document is indexed and `matched_text` appears.
"""

import sys
import os
import asyncio
import json
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from main import tool_store_document, provider


async def store_and_verify_file(path: Path):
    print(f"\nProcessing: {path}")
    unique = f"E2E_REUPLOAD_{int(time.time())}"

    if path.suffix.lower() == '.json':
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            print('  ✗ Failed to parse JSON:', e)
            return
        params = {
            'type': payload.get('type', 'text'),
            'original_file': payload.get('original_file') or path.name,
            'file_format': payload.get('file_format', path.suffix.lstrip('.')),
            'processed_data': payload.get('processed_data', {}),
            'metadata': payload.get('metadata', {}),
            'app_data': payload.get('app_data', {'pipeline': 'reupload-bulk'}),
            'created_by': 'reupload-script'
        }
        # If there is no obvious text, add a small marker in processed_data.content for verification
        if not params['processed_data']:
            params['processed_data'] = {'content': f'Reupload placeholder {unique}'}
    else:
        text = path.read_text(encoding='utf-8', errors='ignore')
        # ensure a unique token exists for verification
        if 'E2E_REUPLOAD_' not in text:
            text = text + f"\n\n{unique}\n"
        params = {
            'type': 'text',
            'original_file': path.name,
            'file_format': path.suffix.lstrip('.') or 'txt',
            'processed_data': {'content': text},
            'metadata': {'title': path.stem},
            'app_data': {'pipeline': 'reupload-bulk'},
            'created_by': 'reupload-script'
        }

    try:
        res = await tool_store_document(params)
    except Exception as e:
        print('  ✗ tool_store_document failed:', e)
        return

    doc_id = res.get('document_id')
    print('  Stored document_id=', doc_id)

    # wait briefly for DB writes
    await asyncio.sleep(0.3)

    # search for the unique token
    q = unique
    try:
        results = await provider.search_documents(query=q, limit=5, min_confidence=0.0)
    except Exception as e:
        print('  ✗ search_documents failed:', e)
        return

    print('  Search results for token=', q)
    print(json.dumps(results, indent=2)[:2000])

    # retrieve and show indexing details
    if doc_id:
        try:
            doc = await provider.retrieve_document(doc_id)
            has_content = isinstance(doc.processed_data, dict) and ('content' in doc.processed_data)
            print('  processed_data.content present:', has_content)
            print('  app_data.search_chunk_count:', doc.app_data.get('search_chunk_count'))
            if doc.app_data.get('search_chunks'):
                print('  first chunk preview:', doc.app_data['search_chunks'][0]['text'][:200])
        except Exception as e:
            print('  ✗ retrieve_document failed:', e)


async def main(folder: str):
    p = Path(folder)
    if not p.exists() or not p.is_dir():
        print('Folder not found:', folder)
        return

    files = sorted([f for f in p.iterdir() if f.is_file()])
    if not files:
        print('No files found in', folder)
        return

    for f in files:
        await store_and_verify_file(f)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python reupload_docs.py /path/to/folder')
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
