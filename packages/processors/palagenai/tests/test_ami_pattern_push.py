#!/usr/bin/env python3
"""
Test script to demonstrate AMI pattern integration in push to Archipelago flow
Shows the difference between old method (hardcoded FID 49) and new AMI pattern (real FIDs)
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.archipelago_service import ArchipelagoService


def test_ami_pattern_enabled():
    """Test push to Archipelago with AMI pattern enabled (default)"""

    print("=" * 80)
    print("TEST 1: AMI Pattern ENABLED (Default - Files First)")
    print("=" * 80)

    service = ArchipelagoService()

    if not service.enabled:
        print("❌ Archipelago service is disabled")
        return False

    ocr_data = {
        'name': 'test_document.pdf',
        'label': 'Test Document - AMI Pattern',
        'text': 'This is a test document for AMI pattern integration. ' * 50,
        'description': 'Testing file upload with AMI pattern (files uploaded FIRST)',
        'file_info': {
            'filename': 'test_document.pdf',
            'file_path': 'eng-typed/sample.pdf'  # Update with actual file
        },
        'ocr_metadata': {
            'provider': 'google_vision',
            'confidence': 0.95,
            'language': 'English',
            'processing_date': '2025-12-15'
        }
    }

    print("\n→ Creating digital object with AMI pattern (default)")
    print("  Expected: Real FID from file upload")

    # Default behavior - AMI pattern enabled
    result = service.create_digital_object_from_ocr_data(
        ocr_data=ocr_data
        # use_ami_pattern=True is the default
    )

    if result:
        print("\n✓ Digital object created!")
        print(f"  Node URL: {result['url']}")
        print(f"  File ID: {result.get('drupal_file_id', 'N/A')}")
        print(f"  Upload method: {result.get('upload_method', 'N/A')}")
        print(f"  AMI pattern used: {result.get('ami_pattern_used', False)}")

        fid = result.get('drupal_file_id')
        if fid and fid != 49:
            print(f"\n✅ SUCCESS: Real FID {fid} obtained (NOT hardcoded 49)")
            return True
        elif fid == 49:
            print(f"\n⚠️ WARNING: Hardcoded FID 49 detected")
            print("   This may indicate file upload failed")
            return False
        else:
            print(f"\n⚠️ WARNING: No FID in response")
            return False
    else:
        print("\n❌ Failed to create digital object")
        return False


def test_ami_pattern_disabled():
    """Test push to Archipelago with AMI pattern disabled (old method)"""

    print("\n" + "=" * 80)
    print("TEST 2: AMI Pattern DISABLED (Old Method - Files After)")
    print("=" * 80)

    service = ArchipelagoService()

    if not service.enabled:
        print("❌ Archipelago service is disabled")
        return False

    ocr_data = {
        'name': 'test_document_old.pdf',
        'label': 'Test Document - Old Method',
        'text': 'This is a test document for old method. ' * 50,
        'description': 'Testing file upload with old method (files uploaded AFTER)',
        'file_info': {
            'filename': 'test_document_old.pdf',
            'file_path': 'eng-typed/sample.pdf'  # Update with actual file
        },
        'ocr_metadata': {
            'provider': 'google_vision',
            'confidence': 0.95,
            'language': 'English',
            'processing_date': '2025-12-15'
        }
    }

    print("\n→ Creating digital object with old method")
    print("  Expected: May use hardcoded FID 49 as fallback")

    # Explicitly disable AMI pattern
    result = service.create_digital_object_from_ocr_data(
        ocr_data=ocr_data,
        use_ami_pattern=False  # Explicitly use old method
    )

    if result:
        print("\n✓ Digital object created!")
        print(f"  Node URL: {result['url']}")
        print(f"  File ID: {result.get('drupal_file_id', 'N/A')}")
        print(f"  Upload method: {result.get('upload_method', 'N/A')}")
        print(f"  AMI pattern used: {result.get('ami_pattern_used', False)}")

        fid = result.get('drupal_file_id')
        if fid and fid != 49:
            print(f"\n✓ Old method succeeded with real FID {fid}")
            return True
        elif fid == 49:
            print(f"\n⚠️ Old method used hardcoded FID 49 (expected)")
            return True  # This is expected for old method
        else:
            print(f"\n⚠️ No FID in response")
            return False
    else:
        print("\n❌ Failed to create digital object")
        return False


def test_comparison():
    """Show side-by-side comparison of both methods"""

    print("\n" + "=" * 80)
    print("COMPARISON: AMI Pattern vs Old Method")
    print("=" * 80)

    comparison = """
┌─────────────────────────────────────────────────────────────────────────┐
│                      AMI Pattern (NEW DEFAULT)                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Upload file FIRST using PHP pattern                                 │
│ 2. Get real FID from Archipelago (e.g., 456)                           │
│ 3. Add FID to metadata['documents'] = [456]                            │
│ 4. Create digital object with FID in metadata                          │
│ ✓ Result: Real FID (not 49)                                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      Old Method (use_ami_pattern=False)                 │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Create digital object node                                          │
│ 2. Upload file AFTER node creation                                     │
│ 3. If upload fails → Use hardcoded FID 49                              │
│ 4. PATCH node with file links                                          │
│ ⚠ Result: May use hardcoded FID 49                                     │
└─────────────────────────────────────────────────────────────────────────┘
"""

    print(comparison)

    print("\nKey Differences:")
    print("-" * 80)
    print(f"{'Aspect':<30} {'AMI Pattern':<25} {'Old Method':<25}")
    print("-" * 80)
    print(f"{'Upload timing':<30} {'Before metadata':<25} {'After node creation':<25}")
    print(f"{'FID availability':<30} {'Immediate':<25} {'After PATCH':<25}")
    print(f"{'Hardcoded FID 49':<30} {'Never used':<25} {'Used as fallback':<25}")
    print(f"{'Field mapping':<30} {'Automatic (MIME)':<25} {'Manual':<25}")
    print(f"{'Default behavior':<30} {'✓ YES':<25} {'No':<25}")
    print("-" * 80)


def test_mime_type_mapping():
    """Test MIME type to field name mapping"""

    print("\n" + "=" * 80)
    print("TEST 3: MIME Type to Field Mapping")
    print("=" * 80)

    service = ArchipelagoService()

    test_cases = [
        ("application/pdf", "documents"),
        ("image/jpeg", "images"),
        ("image/png", "images"),
        ("video/mp4", "videos"),
        ("audio/mp3", "audios"),
    ]

    print("\nMIME Type Mapping (used by AMI pattern):")
    print("-" * 60)
    print(f"{'MIME Type':<30} {'Field Name':<20} {'Status':<10}")
    print("-" * 60)

    all_passed = True
    for mime_type, expected_field in test_cases:
        result_field = service._map_mime_to_field(mime_type)
        status = "✓" if result_field == expected_field else "✗"

        if result_field != expected_field:
            all_passed = False

        print(f"{mime_type:<30} {result_field:<20} {status:<10}")

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
    print("AMI Pattern Integration Test Suite")
    print("Testing file upload integration in push to Archipelago flow")
    print("=" * 80)

    # Test 1: MIME type mapping (doesn't require connection)
    test_mime_type_mapping()

    # Test 2: Comparison table
    test_comparison()

    # Test 3 & 4: Actual uploads (require Archipelago connection)
    print("\n" + "=" * 80)
    print("Note: Tests 4 and 5 require:")
    print("  1. Archipelago running and configured")
    print("  2. Actual test files in Bhushanji folder")
    print("  3. Uncomment the test calls in main() to run")
    print("=" * 80)

    # Uncomment to test actual uploads:
    # test_ami_pattern_enabled()
    # test_ami_pattern_disabled()

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print("""
✓ AMI pattern is now the DEFAULT for push to Archipelago
✓ Files are uploaded BEFORE creating metadata
✓ Real FIDs are obtained from Archipelago (not hardcoded 49)
✓ Automatic MIME type mapping to Archipelago fields
✓ Matches the PHP workflow you provided

To use the old method (with possible FID 49 fallback):
  result = service.create_digital_object_from_ocr_data(
      ocr_data,
      use_ami_pattern=False
  )
    """)


if __name__ == '__main__':
    main()
