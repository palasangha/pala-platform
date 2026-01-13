#!/usr/bin/env python3
"""
Script to retrieve dr:fid values from Archipelago digital objects

Usage:
    python get_file_ids.py <node_id>

Example:
    python get_file_ids.py 123
    python get_file_ids.py 6f10e775-d32d-4641-8a47-5cfe639feb1c
"""

import sys
import json
from app.services.archipelago_service import ArchipelagoService
from app.config import Config

def main():
    if len(sys.argv) < 2:
        print("Usage: python get_file_ids.py <node_id>")
        print("\nExamples:")
        print("  python get_file_ids.py 123")
        print("  python get_file_ids.py 6f10e775-d32d-4641-8a47-5cfe639feb1c")
        sys.exit(1)

    node_id = sys.argv[1]

    # Initialize Archipelago service
    service = ArchipelagoService()

    print(f"\n{'='*60}")
    print(f"Retrieving file information for digital object: {node_id}")
    print(f"{'='*60}\n")

    # Get file IDs
    result = service.get_digital_object_file_ids(node_id)

    if not result:
        print("❌ Failed to retrieve file information")
        print("Check logs for details")
        sys.exit(1)

    # Display results
    print(f"✓ Digital Object Information:")
    print(f"  Node ID: {result['node_id']}")
    print(f"  Node UUID: {result['node_uuid']}")
    print(f"  Label: {result['label']}")
    print(f"  Documents Array: {result['documents_array']}")
    print()

    print(f"✓ File Information (from as:document):")
    print()

    if not result['files']:
        print("  No files found in as:document structure")
    else:
        for idx, file in enumerate(result['files'], 1):
            print(f"  File {idx}:")
            print(f"    Name: {file['name']}")
            print(f"    dr:fid: {file['dr:fid']} ← Drupal File ID")
            print(f"    URL: {file['url']}")
            print(f"    Size: {file['dr:filesize']} bytes")
            print(f"    MIME Type: {file['dr:mimetype']}")
            print(f"    Sequence: {file['sequence']}")
            print(f"    UUID: {file['uuid']}")
            print()

    # Also print JSON format
    print(f"\n{'='*60}")
    print("JSON Format:")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
