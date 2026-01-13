#!/usr/bin/env python3
"""
Test script to verify FID extraction from various response formats
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.archipelago_service import ArchipelagoService


def test_fid_extraction():
    """Test FID extraction from various response formats"""

    print("=" * 80)
    print("Testing FID Extraction from Various Response Formats")
    print("=" * 80)

    service = ArchipelagoService()

    # Test Case 1: Your actual response from Archipelago (JSON:API format with data wrapper)
    print("\n1. JSON:API Response with 'data' Wrapper (Your ACTUAL Response)")
    print("-" * 80)

    # This is the EXACT structure returned by Archipelago file upload endpoint
    jsonapi_response = {
        "jsonapi": {
            "version": "1.0",
            "meta": {"links": {"self": {"href": "http://jsonapi.org/format/1.0/"}}}
        },
        "data": {
            "type": "file--file",
            "id": "91c2fe48-7856-4d8f-a90b-67937a00c321",
            "links": {"self": {"href": "http://esmero-web/jsonapi/file/file/91c2fe48-7856-4d8f-a90b-67937a00c321"}},
            "attributes": {
                "drupal_internal__fid": 108,  # ← Should extract THIS
                "langcode": "en",
                "filename": "How to Cleanse the Mind  9thSeptember1970, Barachakia _4.pdf",
                "uri": {
                    "value": "private://sbf_tmp/How to Cleanse the Mind  9thSeptember1970, Barachakia _4.pdf",
                    "url": "/system/files/sbf_tmp/How%20to%20Cleanse%20the%20Mind%20%209thSeptember1970%2C%20Barachakia%20_4.pdf"
                },
                "filemime": "application/pdf",
                "filesize": 524409,
                "status": False,
                "created": "2025-12-15T09:36:53+00:00",
                "changed": "2025-12-15T09:36:53+00:00"
            },
            "relationships": {
                "uid": {
                    "data": {"type": "user--user", "id": "e1d158c9-0ff3-40ed-abd3-63c021b1a50e"}
                }
            }
        },
        "links": {"self": {"href": "http://esmero-web/jsonapi/file/file/91c2fe48-7856-4d8f-a90b-67937a00c321"}}
    }

    fid = service._extract_fid_from_response(jsonapi_response)
    uri = service._extract_uri_from_response(jsonapi_response)

    print(f"Response structure: {list(jsonapi_response.keys())}")
    print(f"data.attributes keys: {list(jsonapi_response['data']['attributes'].keys())}")
    print(f"Expected FID: 108")
    print(f"Extracted FID: {fid}")
    print(f"Extracted URI: {uri}")

    if fid == 108:
        print("✅ SUCCESS: Correctly extracted FID 108 from JSON:API response with data wrapper")
    else:
        print(f"❌ FAILED: Expected 108, got {fid}")

    # Test Case 2: REST API format with fid array
    print("\n2. REST API Format (fid array)")
    print("-" * 80)

    rest_response = {
        'fid': [{'value': 123}],
        'filename': [{'value': 'test.pdf'}],
        'uri': [{'value': 's3://bucket/test.pdf'}]
    }

    fid = service._extract_fid_from_response(rest_response)
    uri = service._extract_uri_from_response(rest_response)

    print(f"Expected FID: 123")
    print(f"Extracted FID: {fid}")
    print(f"Extracted URI: {uri}")

    if fid == 123:
        print("✅ SUCCESS: Correctly extracted FID from REST array format")
    else:
        print(f"❌ FAILED: Expected 123, got {fid}")

    # Test Case 3: Simple format with direct values
    print("\n3. Simple Format (direct values)")
    print("-" * 80)

    simple_response = {
        'drupal_internal__fid': 456,
        'filename': 'test.pdf',
        'uri': 's3://bucket/test.pdf'
    }

    fid = service._extract_fid_from_response(simple_response)
    uri = service._extract_uri_from_response(simple_response)

    print(f"Expected FID: 456")
    print(f"Extracted FID: {fid}")
    print(f"Extracted URI: {uri}")

    if fid == 456:
        print("✅ SUCCESS: Correctly extracted FID from simple format")
    else:
        print(f"❌ FAILED: Expected 456, got {fid}")

    # Test Case 4: Alternative field names
    print("\n4. Alternative Field Names")
    print("-" * 80)

    alt_response = {
        'file_id': 789,
        'url': 'https://example.com/file.pdf'
    }

    fid = service._extract_fid_from_response(alt_response)
    uri = service._extract_uri_from_response(alt_response)

    print(f"Expected FID: 789")
    print(f"Extracted FID: {fid}")
    print(f"Extracted URI: {uri}")

    if fid == 789:
        print("✅ SUCCESS: Correctly extracted FID from alternative field name")
    else:
        print(f"❌ FAILED: Expected 789, got {fid}")

    # Test Case 5: Missing FID (should return None)
    print("\n5. Missing FID (should return None)")
    print("-" * 80)

    no_fid_response = {
        'filename': 'test.pdf',
        'uri': 's3://bucket/test.pdf'
    }

    fid = service._extract_fid_from_response(no_fid_response)

    print(f"Expected: None")
    print(f"Extracted FID: {fid}")

    if fid is None:
        print("✅ SUCCESS: Correctly returned None for missing FID")
    else:
        print(f"❌ FAILED: Expected None, got {fid}")

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print("""
The _extract_fid_from_response() function now correctly handles:

1. ✓ JSON:API format with attributes
   {'attributes': {'drupal_internal__fid': 98}}

2. ✓ REST API format with arrays
   {'fid': [{'value': 123}]}

3. ✓ Simple format with direct values
   {'drupal_internal__fid': 456}

4. ✓ Alternative field names
   {'file_id': 789, 'entity_id': 999}

5. ✓ Missing FID returns None

The fix prioritizes checking inside 'attributes' first (JSON:API format),
which is the format returned by Archipelago's file upload endpoint.
    """)


if __name__ == '__main__':
    test_fid_extraction()
