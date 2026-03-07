#!/usr/bin/env python3
"""
Test Metadata Enhancements - Week 1 Critical Fixes

Tests all 9 enhancements:
1. UUID generation
2. Collection ID extraction
3. Full text population
4. Date extraction
5. Correspondence fixing
6. AMI metadata
7. Temporal markers
8. Facets generation
9. Completeness scoring
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'enrichment_service'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'agents' / 'context-agent'))

from enrichment_service.utils.metadata_enhancer import MetadataEnhancer
from tools.ami_metadata_parser import AMIMetadataParser


def create_sample_enriched_data():
    """Create sample enriched data from agent orchestrator (before enhancement)"""
    return {
        "metadata": {
            "document_type": "letter",
            "access_level": "private",
            "storage_location": {
                "archive_name": "Vipassana Research Institute",
                "collection_name": "",
                "box_number": "",
                "folder_number": "",
                "digital_repository": ""
            },
            "digitization_info": {
                "date": "Unknown",
                "operator": "Unknown",
                "equipment": "Unknown",
                "resolution": "Unknown DPI",
                "file_format": "PDF"
            }
        },
        "document": {
            "date": {},
            "languages": ["en"],
            "physical_attributes": {},
            "correspondence": {
                "sender": {
                    "name": "",
                    "title": "",
                    "affiliation": ""
                },
                "recipient": {
                    "name": "Last",  # Incorrect from parsing
                    "title": "",
                    "affiliation": ""
                },
                "cc": []
            }
        },
        "content": {
            "full_text": "",  # MISSING - should be populated
            "summary": "Letter describing third Vipassana meditation retreat in Mumbai...",
            "salutation": "Dear Babu bhaiya,",
            "body": [
                "a month has passed and yet I have not been able to write...",
                "It was arranged at the strong insistence of the students..."
            ],
            "closing": "",  # Should be "Your younger brother,"
            "signature": "Satyanarayan",
            "attachments": [],
            "annotations": []
        },
        "analysis": {
            "keywords": [
                {"keyword": "Vipassanā", "relevance": 0.8, "frequency": 6},
                {"keyword": "Dhamma", "relevance": 0.7, "frequency": 3}
            ],
            "subjects": [
                {"subject": "personal_matters", "confidence": 0.8},
                {"subject": "correspondence", "confidence": 0.9}
            ],
            "people": [
                {"name": "Babu bhaiya", "role": "recipient", "confidence": 0.7},
                {"name": "Vijay Adukia", "role": "mentioned", "confidence": 0.7}
            ],
            "organizations": [
                {"name": "Vipassana Research Institute", "type": "religious_organization"}
            ],
            "locations": [
                {"name": "Mumbai", "type": "city"},
                {"name": "New Delhi", "type": "city"}
            ],
            "events": [
                {"name": "Third Vipassana Meditation Retreat", "date": "1969-08-14"}
            ],
            "historical_context": "Early Vipassana movement in India...",
            "significance": "Documents the growth of Vipassana meditation...",
            "relationships": []
        }
    }


def create_sample_ocr_data():
    """Create sample OCR data"""
    return {
        "filename": "From Refusals to Last-Minute Rescue 29 sep 1969 New Delhi.pdf",
        "file_path": "/documents/From Refusals to Last-Minute Rescue 29 sep 1969 New Delhi.pdf",
        "ocr_text": """--- Page 1 ---
From Refusals to Last - Minute Rescue
29th September 1969, New Delhi.

Dear Babu bhaiya,
Respectful salutations!

Over a month has passed and yet I have not been able to write to you about the third
meditation retreat held in Mumbai from August 14 to 24...

[Full OCR text would continue here...]

--- Page 7 ---
Your younger brother,
Satyanarayan
""",
        "page_count": 7,
        "extraction_mode": "text_only"
    }


def test_enhancements():
    """Test all metadata enhancements"""
    print("="*80)
    print("TESTING METADATA ENHANCEMENTS - WEEK 1 CRITICAL FIXES")
    print("="*80)

    # Initialize
    ami_parser = AMIMetadataParser()
    enhancer = MetadataEnhancer(ami_parser=ami_parser)

    # Sample data
    enriched_data = create_sample_enriched_data()
    ocr_data = create_sample_ocr_data()
    filename = ocr_data['filename']

    print(f"\n📄 Testing with filename: {filename}")
    print(f"📝 OCR text length: {len(ocr_data['ocr_text'])} characters")

    # Apply enhancements
    print("\n🚀 Applying metadata enhancements...\n")
    enhanced = enhancer.enhance_metadata(
        enriched_data=enriched_data,
        ocr_data=ocr_data,
        filename=filename,
        document_id=None,  # Will be generated
        collection_id=None  # Will be extracted
    )

    # Test results
    print("="*80)
    print("TESTING RESULTS")
    print("="*80)

    results = {
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }

    # Test 1: UUID Generation
    print("\n1. UUID GENERATION")
    print("-" * 80)
    has_id = bool(enhanced['metadata'].get('id'))
    is_uuid = len(enhanced['metadata'].get('id', '')) == 36
    if has_id and is_uuid:
        print(f"✓ PASS: Generated document ID: {enhanced['metadata']['id']}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: No valid UUID generated")
        results["failed"] += 1

    # Test 2: Collection ID
    print("\n2. COLLECTION ID EXTRACTION")
    print("-" * 80)
    collection_id = enhanced['metadata'].get('collection_id')
    if collection_id:
        print(f"✓ PASS: Collection ID: {collection_id}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: No collection ID")
        results["failed"] += 1

    # Test 3: Full Text Population
    print("\n3. FULL TEXT POPULATION")
    print("-" * 80)
    full_text = enhanced['content'].get('full_text', '')
    if full_text and len(full_text) > 100:
        print(f"✓ PASS: Full text populated ({len(full_text)} chars)")
        print(f"   Preview: {full_text[:100]}...")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: Full text not populated or too short")
        results["failed"] += 1

    # Test 4: Date Extraction
    print("\n4. DATE EXTRACTION")
    print("-" * 80)
    creation_date = enhanced['document'].get('date', {}).get('creation_date')
    if creation_date:
        print(f"✓ PASS: Creation date: {creation_date}")
        print(f"   Display: {enhanced['document']['date'].get('date_display')}")
        print(f"   Source: {enhanced['document']['date'].get('date_source')}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: Date not extracted")
        results["failed"] += 1

    # Test 5: Correspondence Fixing
    print("\n5. CORRESPONDENCE SENDER/RECIPIENT")
    print("-" * 80)
    sender = enhanced['document']['correspondence'].get('sender', {}).get('name')
    recipient = enhanced['document']['correspondence'].get('recipient', {}).get('name')

    if sender and sender != "":
        print(f"✓ PASS: Sender name: {sender}")
        results["passed"] += 1
    else:
        print(f"⚠ WARNING: Sender name not set")
        results["warnings"] += 1

    if recipient and recipient != "Last":
        print(f"✓ PASS: Recipient name: {recipient}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: Recipient name not fixed (still '{recipient}')")
        results["failed"] += 1

    # Test 6: AMI Metadata (will fail for non-AMI filename)
    print("\n6. AMI METADATA")
    print("-" * 80)
    ami_metadata = enhanced['metadata'].get('ami_metadata')
    if ami_metadata and ami_metadata.get('master_identifier'):
        print(f"✓ PASS: AMI metadata extracted")
        print(f"   Master ID: {ami_metadata.get('master_identifier')}")
        results["passed"] += 1
    else:
        print(f"⚠ INFO: No AMI metadata (filename not AMI format)")
        results["warnings"] += 1

    # Test 7: Temporal Markers
    print("\n7. TEMPORAL MARKERS")
    print("-" * 80)
    temporal = enhanced['document'].get('date', {}).get('temporal_markers', {})
    if temporal and temporal.get('year'):
        print(f"✓ PASS: Temporal markers added")
        print(f"   Year: {temporal.get('year')}")
        print(f"   Decade: {temporal.get('decade')}")
        print(f"   Quarter: {temporal.get('quarter')}")
        print(f"   Day of week: {temporal.get('day_of_week')}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: Temporal markers not added")
        results["failed"] += 1

    # Test 8: Facets
    print("\n8. SEARCH FACETS")
    print("-" * 80)
    facets = enhanced.get('searchability', {}).get('facets', {})
    if facets:
        print(f"✓ PASS: {len(facets)} facets generated")
        for key, value in facets.items():
            print(f"   {key}: {value}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: No facets generated")
        results["failed"] += 1

    # Test 9: Completeness Scoring
    print("\n9. COMPLETENESS SCORING")
    print("-" * 80)
    completeness = enhanced.get('searchability', {}).get('completeness_score')
    quality = enhanced.get('searchability', {}).get('quality_score')
    if completeness is not None:
        print(f"✓ PASS: Completeness score calculated")
        print(f"   Completeness: {completeness:.2%}")
        print(f"   Quality: {quality:.2%}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: No completeness score")
        results["failed"] += 1

    # Test 10: Classification
    print("\n10. CLASSIFICATION METADATA")
    print("-" * 80)
    classification = enhanced['metadata'].get('classification', {})
    if classification:
        print(f"✓ PASS: Classification added")
        print(f"   Primary subject: {classification.get('primary_subject')}")
        print(f"   Topics: {', '.join(classification.get('topics', [])[:3])}")
        print(f"   Genre: {classification.get('genre')}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: No classification")
        results["failed"] += 1

    # Test 11: Search Tags
    print("\n11. SEARCH TAGS")
    print("-" * 80)
    tags = enhanced.get('searchability', {}).get('tags', [])
    if tags:
        print(f"✓ PASS: {len(tags)} search tags generated")
        print(f"   Tags: {', '.join(tags[:10])}")
        results["passed"] += 1
    else:
        print(f"✗ FAIL: No tags generated")
        results["failed"] += 1

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    total_tests = results["passed"] + results["failed"]
    print(f"✓ PASSED: {results['passed']}/{total_tests}")
    print(f"✗ FAILED: {results['failed']}/{total_tests}")
    print(f"⚠ WARNINGS: {results['warnings']}")

    if results["failed"] == 0:
        print(f"\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  SOME TESTS FAILED")

    # Save enhanced output
    output_file = Path(__file__).parent / "test_enhanced_output.json"
    with open(output_file, 'w') as f:
        json.dump(enhanced, f, indent=2)
    print(f"\n💾 Enhanced output saved to: {output_file}")

    return results["failed"] == 0


def test_ami_filename():
    """Test with AMI-formatted filename"""
    print("\n" + "="*80)
    print("BONUS TEST: AMI FILENAME PARSING")
    print("="*80)

    ami_parser = AMIMetadataParser()
    enhancer = MetadataEnhancer(ami_parser=ami_parser)

    # AMI filename
    ami_filename = "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG"
    enriched_data = create_sample_enriched_data()
    ocr_data = create_sample_ocr_data()
    ocr_data['filename'] = ami_filename

    enhanced = enhancer.enhance_metadata(
        enriched_data=enriched_data,
        ocr_data=ocr_data,
        filename=ami_filename
    )

    ami_metadata = enhanced['metadata'].get('ami_metadata', {})
    if ami_metadata:
        print(f"\n✓ AMI metadata successfully extracted:")
        print(f"   Master ID: {ami_metadata.get('master_identifier')}")
        print(f"   Collection: {ami_metadata.get('collection')}")
        print(f"   Series: {ami_metadata.get('series')}")
        print(f"   Page: {ami_metadata.get('page_number')}")
        print(f"   Year: {ami_metadata.get('year')}")
        print(f"   Document Type: {ami_metadata.get('document_type_code')}")
        print(f"   Medium: {ami_metadata.get('medium_code')}")
        return True
    else:
        print(f"\n✗ AMI parsing failed")
        return False


if __name__ == '__main__':
    try:
        success = test_enhancements()
        test_ami_filename()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
