#!/usr/bin/env python3
"""
Test script for metadata writer tool

Tests:
1. Write metadata to a file
2. Read metadata from a file
3. Update existing metadata
4. Batch write operations
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.metadata_writer import MetadataWriter


def test_write_metadata():
    """Test writing metadata to a file"""
    print("\n" + "="*60)
    print("TEST 1: Write Metadata")
    print("="*60)

    writer = MetadataWriter(base_path='/tmp/test_metadata')

    test_metadata = {
        'document_type': 'Letter',
        'sender': 'S.N. Goenka',
        'recipient': 'Student',
        'date': '1990-05-15',
        'subjects': ['Buddhism', 'Vipassana', 'Meditation'],
        'summary': 'A letter discussing meditation practices and upcoming courses.',
        'historical_context': 'Written during the period of Vipassana expansion in the West.',
        'language': 'English',
        'pages': 3
    }

    # Create test directory
    os.makedirs('/tmp/test_metadata', exist_ok=True)

    # Create a dummy file
    test_file = '/tmp/test_metadata/sample_letter_001.jpg'
    Path(test_file).touch()

    result = writer.write_metadata(test_file, test_metadata)

    print(f"✓ Write Result:")
    print(json.dumps(result, indent=2))

    return result['success']


def test_read_metadata():
    """Test reading metadata from a file"""
    print("\n" + "="*60)
    print("TEST 2: Read Metadata")
    print("="*60)

    writer = MetadataWriter(base_path='/tmp/test_metadata')

    metadata_file = '/tmp/test_metadata/sample_letter_001_metadata.json'
    result = writer.read_metadata(metadata_file)

    print(f"✓ Read Result:")
    print(json.dumps(result, indent=2))

    return result['success']


def test_update_metadata():
    """Test updating existing metadata"""
    print("\n" + "="*60)
    print("TEST 3: Update Metadata")
    print("="*60)

    writer = MetadataWriter(base_path='/tmp/test_metadata')

    metadata_file = '/tmp/test_metadata/sample_letter_001_metadata.json'

    updates = {
        'reviewed_by': 'Admin User',
        'review_date': '2025-01-15',
        'quality_score': 95,
        'tags': ['important', 'historical', 'teachings']
    }

    result = writer.update_metadata(metadata_file, updates, merge=True)

    print(f"✓ Update Result:")
    print(json.dumps(result, indent=2))

    # Read back to verify
    if result['success']:
        read_result = writer.read_metadata(metadata_file)
        if read_result['success']:
            print(f"\n✓ Updated Metadata:")
            print(json.dumps(read_result['metadata'], indent=2))

    return result['success']


def test_batch_write():
    """Test batch writing metadata"""
    print("\n" + "="*60)
    print("TEST 4: Batch Write Metadata")
    print("="*60)

    writer = MetadataWriter(base_path='/tmp/test_metadata')

    # Create test files
    for i in range(1, 4):
        test_file = f'/tmp/test_metadata/batch_letter_{i:03d}.jpg'
        Path(test_file).touch()

    batch = [
        {
            'file_path': '/tmp/test_metadata/batch_letter_001.jpg',
            'metadata': {
                'document_id': 'DOC001',
                'document_type': 'Letter',
                'sender': 'Teacher A',
                'date': '1985-01-01'
            }
        },
        {
            'file_path': '/tmp/test_metadata/batch_letter_002.jpg',
            'metadata': {
                'document_id': 'DOC002',
                'document_type': 'Newsletter',
                'sender': 'Organization',
                'date': '1985-02-01'
            }
        },
        {
            'file_path': '/tmp/test_metadata/batch_letter_003.jpg',
            'metadata': {
                'document_id': 'DOC003',
                'document_type': 'Diary',
                'author': 'Student',
                'date': '1985-03-01'
            }
        }
    ]

    result = writer.write_batch_metadata(batch)

    print(f"✓ Batch Write Result:")
    print(json.dumps(result, indent=2))

    return result['successful'] == result['total']


def test_ami_integration():
    """Test integration with AMI parser"""
    print("\n" + "="*60)
    print("TEST 5: AMI Parser + Metadata Writer Integration")
    print("="*60)

    from tools.ami_metadata_parser import AMIMetadataParser

    writer = MetadataWriter(base_path='/tmp/test_metadata')
    parser = AMIMetadataParser()

    # Parse an AMI filename
    test_filename = "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG"
    parsed_metadata = parser.parse(test_filename)

    print(f"✓ Parsed Metadata:")
    print(json.dumps(parsed_metadata, indent=2))

    # Create test file
    test_file = f'/tmp/test_metadata/{test_filename}'
    Path(test_file).touch()

    # Add archipelago fields
    if parsed_metadata.get('parsed'):
        parsed_metadata['archipelago_fields'] = parser.get_archipelago_fields(parsed_metadata)

    # Write the parsed metadata
    result = writer.write_metadata(test_file, parsed_metadata)

    print(f"\n✓ Write Result:")
    print(json.dumps(result, indent=2))

    return result['success']


def cleanup():
    """Clean up test files"""
    print("\n" + "="*60)
    print("Cleanup")
    print("="*60)

    import shutil
    test_dir = '/tmp/test_metadata'
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"✓ Removed test directory: {test_dir}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("METADATA WRITER TOOL TESTS")
    print("="*60)

    results = {}

    try:
        results['write'] = test_write_metadata()
        results['read'] = test_read_metadata()
        results['update'] = test_update_metadata()
        results['batch'] = test_batch_write()
        results['ami_integration'] = test_ami_integration()

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        for test_name, success in results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status}: {test_name}")

        total_pass = sum(results.values())
        total_tests = len(results)
        print(f"\nTotal: {total_pass}/{total_tests} tests passed")

        if total_pass == total_tests:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️ Some tests failed")

    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        cleanup()


if __name__ == '__main__':
    main()
