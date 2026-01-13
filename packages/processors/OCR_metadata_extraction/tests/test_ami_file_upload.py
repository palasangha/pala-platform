#!/usr/bin/env python3
"""
Test script for AMI-style file upload to Archipelago
Demonstrates the PHP pattern: upload files first, then create metadata with FIDs
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.archipelago_service import ArchipelagoService


def test_ami_file_upload():
    """Test uploading files using AMI pattern (files first, then metadata)"""

    print("=" * 80)
    print("Testing AMI-Style File Upload to Archipelago")
    print("Pattern: Upload files FIRST → Get FIDs → Create metadata with FIDs")
    print("=" * 80)

    # Initialize service
    service = ArchipelagoService()

    if not service.enabled:
        print("❌ Archipelago service is disabled")
        print("Please set ARCHIPELAGO_ENABLED=true in your .env file")
        return False

    print(f"\n✓ Archipelago service initialized")
    print(f"  URL: {service.base_url}")
    print(f"  Username: {service.username}")

    # Test files to upload
    test_files = [
        "eng-typed/sample1.pdf",  # Will be mapped to 'documents'
        "eng-typed/sample2.jpg",  # Will be mapped to 'images'
    ]

    # Prepare metadata (without file IDs - they will be added automatically)
    metadata = {
        "@context": "http://schema.org",
        "@type": "DigitalDocument",
        "label": "Test Document with Files (AMI Pattern)",
        "description": "Testing file upload before metadata creation",
        "language": ["English"],
        "owner": "Vipassana Research Institute",
        "creator": "VRI",
        "rights": "All rights reserved",

        # OCR metadata
        "ocr_text_preview": "This is a test document for AMI file upload pattern...",
        "ocr_provider": "google_vision",
        "ocr_confidence": 0.95,
        "ocr_language": "English",

        # File arrays will be populated automatically based on MIME types
        # "documents": []  ← Will be added automatically for PDF files
        # "images": []     ← Will be added automatically for image files
    }

    print(f"\n→ Creating digital object with files (AMI pattern)")
    print(f"  Files to upload: {len(test_files)}")
    for file_path in test_files:
        print(f"    - {file_path}")

    # Create digital object with files
    result = service.create_digital_object_with_files(
        metadata=metadata,
        file_paths=test_files
    )

    if result and result.get('success'):
        print(f"\n{'=' * 80}")
        print("✅ SUCCESS! Digital object created with files")
        print(f"{'=' * 80}")
        print(f"\nDigital Object Details:")
        print(f"  Node ID: {result['node_id']}")
        print(f"  URL: {result['url']}")
        print(f"  Files attached: {result['files_attached']}")

        print(f"\nFile ID Mapping (by MIME type):")
        for field_name, fids in result['file_mapping'].items():
            print(f"  {field_name}: {fids}")

        print(f"\nUploaded Files:")
        for file_info in result['uploaded_files']:
            print(f"  - {file_info['filename']}")
            print(f"    FID: {file_info['fid']}")
            print(f"    MIME: {file_info['filemime']}")
            print(f"    Size: {file_info['filesize']} bytes")
            print(f"    Mapped to: {file_info['field_name']}")

        print(f"\n{'=' * 80}")
        print("How it works:")
        print("1. Each file is uploaded individually to Archipelago")
        print("2. Archipelago returns a drupal_internal__fid for each file")
        print("3. MIME type determines the metadata field (documents, images, etc.)")
        print("4. FIDs are added to the appropriate metadata arrays")
        print("5. Digital object is created with file IDs already in metadata")
        print(f"{'=' * 80}")

        return True
    else:
        print(f"\n❌ FAILED to create digital object with files")
        return False


def test_single_file_upload():
    """Test uploading a single file before creating metadata"""

    print("\n" + "=" * 80)
    print("Testing Single File Upload (Before Metadata)")
    print("=" * 80)

    service = ArchipelagoService()

    # Login first
    csrf_token = service._login()
    if not csrf_token:
        print("❌ Failed to login")
        return False

    print(f"✓ Logged in successfully")

    # Upload a single file
    test_file = "eng-typed/sample1.pdf"

    print(f"\n→ Uploading file: {test_file}")

    result = service.upload_file_before_metadata(
        file_path=test_file,
        csrf_token=csrf_token
    )

    if result:
        print(f"\n✅ File uploaded successfully!")
        print(f"  FID: {result['fid']}")
        print(f"  Filename: {result['filename']}")
        print(f"  MIME type: {result['filemime']}")
        print(f"  Size: {result['filesize']} bytes")
        print(f"  Mapped field: {result['field_name']}")
        print(f"  URI: {result['uri']}")

        print(f"\nYou can now use this FID in your metadata:")
        print(f"  metadata['{result['field_name']}'] = [{result['fid']}]")

        return True
    else:
        print(f"\n❌ File upload failed")
        return False


def test_mime_type_mapping():
    """Test MIME type to field name mapping"""

    print("\n" + "=" * 80)
    print("Testing MIME Type to Field Mapping")
    print("=" * 80)

    service = ArchipelagoService()

    test_cases = [
        ("application/pdf", "documents"),
        ("image/jpeg", "images"),
        ("image/png", "images"),
        ("video/mp4", "videos"),
        ("audio/mp3", "audios"),
        ("audio/mpeg", "audios"),
        ("application/zip", "documents"),
        ("text/plain", "documents"),
        ("model/gltf+json", "models"),
    ]

    print("\nMIME Type → Archipelago Field Mapping:")
    print("-" * 60)

    all_passed = True
    for mime_type, expected_field in test_cases:
        result_field = service._map_mime_to_field(mime_type)
        status = "✓" if result_field == expected_field else "✗"

        if result_field != expected_field:
            all_passed = False

        print(f"{status} {mime_type:30s} → {result_field:15s} (expected: {expected_field})")

    print("-" * 60)

    if all_passed:
        print("✅ All MIME type mappings correct")
        return True
    else:
        print("❌ Some MIME type mappings failed")
        return False


def main():
    """Run all tests"""

    print("\n" + "=" * 80)
    print("AMI File Upload Test Suite")
    print("=" * 80)

    # Test 1: MIME type mapping (doesn't require connection)
    test_mime_type_mapping()

    # Test 2: Single file upload
    # Uncomment to test (requires Archipelago connection and actual files)
    # test_single_file_upload()

    # Test 3: Full AMI pattern upload
    # Uncomment to test (requires Archipelago connection and actual files)
    # test_ami_file_upload()

    print("\n" + "=" * 80)
    print("Test suite complete!")
    print("=" * 80)
    print("\nTo run the full tests:")
    print("1. Ensure Archipelago is running and configured in .env")
    print("2. Uncomment the test functions in main()")
    print("3. Ensure test files exist in the Bhushanji folder")
    print("4. Run: python3 test_ami_file_upload.py")


if __name__ == '__main__':
    main()
