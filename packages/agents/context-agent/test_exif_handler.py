#!/usr/bin/env python3
"""
Test script for EXIF metadata handler

Tests:
1. Read EXIF from image
2. Write EXIF to image
3. Create enriched copy (image + JSON + EXIF)
4. Batch processing
5. Integration with AMI parser and metadata writer
"""

import sys
import json
import os
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from tools.exif_metadata_handler import ExifMetadataHandler
from tools.ami_metadata_parser import AMIMetadataParser
from tools.metadata_writer import MetadataWriter


def create_test_image(path: str, width: int = 800, height: int = 600):
    """Create a test JPEG image"""
    img = Image.new('RGB', (width, height), color='white')
    # Add some text/drawing to make it more realistic
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Test Image for EXIF Metadata", fill='black')
    img.save(path, 'JPEG', quality=95)
    return path


def test_read_exif():
    """Test reading EXIF from an image"""
    print("\n" + "="*60)
    print("TEST 1: Read EXIF Metadata")
    print("="*60)

    handler = ExifMetadataHandler()

    # Create test image
    test_image = '/tmp/test_read_exif.jpg'
    create_test_image(test_image)

    result = handler.read_exif(test_image)

    print(f"✓ Read EXIF Result:")
    print(json.dumps(result, indent=2, default=str))

    # Cleanup
    Path(test_image).unlink(missing_ok=True)

    return result['success']


def test_write_exif():
    """Test writing EXIF metadata to image"""
    print("\n" + "="*60)
    print("TEST 2: Write EXIF Metadata")
    print("="*60)

    handler = ExifMetadataHandler()

    # Create test image
    test_image = '/tmp/test_write_exif.jpg'
    create_test_image(test_image)

    # Metadata to write
    metadata = {
        'title': 'Historical Letter from S.N. Goenka',
        'sender': 'S.N. Goenka',
        'author': 'S.N. Goenka',
        'date': '1990-05-15T10:30:00',
        'summary': 'A letter discussing Vipassana meditation practices and upcoming courses.',
        'copyright': 'Vipassana Research Institute',
        'subjects': ['Buddhism', 'Vipassana', 'Meditation']
    }

    # Write EXIF
    output_path = '/tmp/test_write_exif_output.jpg'
    result = handler.write_exif(test_image, metadata, output_path)

    print(f"✓ Write EXIF Result:")
    print(json.dumps(result, indent=2, default=str))

    # Read back to verify
    if result['success']:
        print(f"\n✓ Reading back EXIF to verify:")
        verify_result = handler.read_exif(output_path)
        if verify_result['success']:
            exif = verify_result['exif']
            print(f"  - ImageDescription: {exif.get('ImageDescription', 'N/A')}")
            print(f"  - Artist: {exif.get('Artist', 'N/A')}")
            print(f"  - DateTime: {exif.get('DateTime', 'N/A')}")
            print(f"  - Software: {exif.get('Software', 'N/A')}")
            print(f"  - Copyright: {exif.get('Copyright', 'N/A')}")

    # Cleanup
    Path(test_image).unlink(missing_ok=True)
    Path(output_path).unlink(missing_ok=True)

    return result['success']


def test_create_enriched_copy():
    """Test creating enriched copy with EXIF and JSON"""
    print("\n" + "="*60)
    print("TEST 3: Create Enriched Copy (Image + JSON + EXIF)")
    print("="*60)

    handler = ExifMetadataHandler()

    # Create test image
    test_image = '/tmp/test_original_letter.jpg'
    create_test_image(test_image)

    # Full enriched metadata
    enriched_metadata = {
        'document_type': 'Letter',
        'sender': 'S.N. Goenka',
        'recipient': 'Student Meditator',
        'date': '1990-05-15',
        'original_date': '1990-05-15T10:30:00',
        'subjects': ['Buddhism', 'Vipassana', 'Meditation', 'Dhamma'],
        'summary': 'A letter discussing meditation practices and providing guidance for students.',
        'historical_context': 'Written during the period of Vipassana expansion in the Western world.',
        'significance': 'High historical importance - documents early teaching methods',
        'biographies': {
            'S.N. Goenka': 'Renowned Vipassana meditation teacher who brought the technique to the West.'
        },
        'language': 'English',
        'page_count': 3,
        'quality_score': 95
    }

    # Create enriched copy
    result = handler.create_copy_with_metadata(
        test_image,
        enriched_metadata,
        output_dir='/tmp',
        suffix='_enriched'
    )

    print(f"✓ Create Enriched Copy Result:")
    print(json.dumps(result, indent=2, default=str))

    # Verify files exist
    if result['success']:
        print(f"\n✓ Verification:")
        print(f"  - Original: {result['original_image']} ({result['file_sizes']['original']} bytes)")
        print(f"  - Enriched Image: {result['enriched_image']} ({result['file_sizes']['enriched_image']} bytes)")
        print(f"  - Metadata JSON: {result['metadata_json']} ({result['file_sizes']['metadata_json']} bytes)")
        print(f"  - EXIF Embedded: {result['exif_embedded']}")

        # Read the JSON to verify
        with open(result['metadata_json'], 'r') as f:
            saved_metadata = json.load(f)
            print(f"\n✓ Saved Metadata Keys: {list(saved_metadata.keys())[:10]}...")

        # Read EXIF to verify
        exif_result = handler.read_exif(result['enriched_image'])
        if exif_result['success']:
            print(f"\n✓ Embedded EXIF:")
            print(f"  - ImageDescription: {exif_result['exif'].get('ImageDescription', 'N/A')[:50]}...")
            print(f"  - Artist: {exif_result['exif'].get('Artist', 'N/A')}")

    # Cleanup
    Path(test_image).unlink(missing_ok=True)
    if result.get('success'):
        Path(result['enriched_image']).unlink(missing_ok=True)
        Path(result['metadata_json']).unlink(missing_ok=True)

    return result['success']


def test_batch_processing():
    """Test batch processing multiple images"""
    print("\n" + "="*60)
    print("TEST 4: Batch Processing")
    print("="*60)

    handler = ExifMetadataHandler()

    # Create multiple test images
    batch = []
    for i in range(1, 4):
        image_path = f'/tmp/batch_image_{i:03d}.jpg'
        create_test_image(image_path)

        metadata = {
            'document_id': f'DOC{i:03d}',
            'document_type': 'Letter',
            'sender': f'Sender {i}',
            'date': f'1990-0{i}-15',
            'summary': f'This is test document number {i}.'
        }

        batch.append({
            'image_path': image_path,
            'metadata': metadata,
            'suffix': '_enriched'
        })

    # Process batch
    result = handler.batch_create_copies(batch, output_dir='/tmp')

    print(f"✓ Batch Processing Result:")
    print(json.dumps({
        'total': result['total'],
        'successful': result['successful'],
        'failed': result['failed']
    }, indent=2))

    # Cleanup
    for item in batch:
        Path(item['image_path']).unlink(missing_ok=True)

    if result['successful'] > 0:
        for output in result['outputs']:
            Path(output['enriched_image']).unlink(missing_ok=True)
            Path(output['metadata_json']).unlink(missing_ok=True)

    return result['successful'] == result['total']


def test_full_pipeline_integration():
    """Test full integration: AMI parse + Enrichment + EXIF + Copy"""
    print("\n" + "="*60)
    print("TEST 5: Full Pipeline Integration")
    print("="*60)

    # Initialize handlers
    ami_parser = AMIMetadataParser()
    exif_handler = ExifMetadataHandler()
    metadata_writer = MetadataWriter()

    # 1. Parse AMI filename
    ami_filename = "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG"
    print(f"\n1. Parsing AMI filename: {ami_filename}")
    parsed = ami_parser.parse(ami_filename)

    if not parsed['parsed']:
        print("✗ AMI parsing failed")
        return False

    print(f"   ✓ Parsed: {parsed['document_type_full']} from {parsed['sender']} to {parsed['recipient']}")

    # 2. Create test image with this filename
    test_image = f'/tmp/{ami_filename}'
    create_test_image(test_image)
    print(f"\n2. Created test image: {test_image}")

    # 3. Add enrichment metadata
    enriched_metadata = {
        **parsed,
        'archipelago_fields': ami_parser.get_archipelago_fields(parsed),
        'summary': f"Letter from {parsed['sender']} to {parsed['recipient']} discussing important matters.",
        'historical_context': 'Part of the early correspondence collection.',
        'subjects': ['Letters', 'Historical Documents'],
        'enrichment_timestamp': '2026-01-29T10:00:00Z',
        'enriched_by': 'Heritage Platform AI'
    }

    print(f"\n3. Added enrichment metadata")

    # 4. Create enriched copy (image + JSON + EXIF)
    print(f"\n4. Creating enriched copy...")
    copy_result = exif_handler.create_copy_with_metadata(
        test_image,
        enriched_metadata,
        output_dir='/tmp',
        suffix='_enriched'
    )

    if copy_result['success']:
        print(f"   ✓ Enriched image: {Path(copy_result['enriched_image']).name}")
        print(f"   ✓ Metadata JSON: {Path(copy_result['metadata_json']).name}")
        print(f"   ✓ EXIF embedded: {copy_result['exif_embedded']}")
        print(f"   ✓ Total size: {sum(copy_result['file_sizes'].values())} bytes")
    else:
        print(f"   ✗ Failed: {copy_result.get('error')}")

    # Cleanup
    Path(test_image).unlink(missing_ok=True)
    if copy_result.get('success'):
        Path(copy_result['enriched_image']).unlink(missing_ok=True)
        Path(copy_result['metadata_json']).unlink(missing_ok=True)

    return copy_result['success']


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("EXIF METADATA HANDLER TESTS")
    print("="*60)

    results = {}

    try:
        results['read_exif'] = test_read_exif()
        results['write_exif'] = test_write_exif()
        results['create_enriched_copy'] = test_create_enriched_copy()
        results['batch_processing'] = test_batch_processing()
        results['full_pipeline'] = test_full_pipeline_integration()

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


if __name__ == '__main__':
    main()
