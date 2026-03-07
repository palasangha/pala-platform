#!/usr/bin/env python3
"""
Standalone test for metadata enhancements
Does not require MongoDB or full enrichment service
"""

import json
import sys
import re
import uuid
from pathlib import Path
from datetime import datetime

# Direct import of enhancer and AMI parser
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'agents' / 'context-agent'))

# Import AMI parser
from tools.ami_metadata_parser import AMIMetadataParser


# Simplified enhancer for testing (copy of key methods)
class SimpleMetadataEnhancer:
    def __init__(self, ami_parser=None):
        self.ami_parser = ami_parser

    def enhance_metadata(self, enriched_data, ocr_data, filename, document_id=None, collection_id=None):
        enhanced = enriched_data.copy()

        # 1. Generate ID
        if not document_id:
            document_id = str(uuid.uuid4())
        enhanced['metadata']['id'] = document_id

        # 2. Collection ID
        if not collection_id:
            collection_id = self._extract_collection_id(filename)
        enhanced['metadata']['collection_id'] = collection_id

        # 3. Full text
        ocr_text = ocr_data.get('ocr_text', '')
        if ocr_text and not enhanced['content'].get('full_text'):
            enhanced['content']['full_text'] = ocr_text

        # 4. Dates
        enhanced = self._enhance_dates(enhanced, filename, ocr_text)

        # 5. Correspondence
        enhanced = self._fix_correspondence(enhanced)

        # 6. AMI metadata
        if self.ami_parser:
            enhanced = self._add_ami_metadata(enhanced, filename)

        # 7. Temporal markers
        enhanced = self._add_temporal_markers(enhanced)

        # 8. Classification
        enhanced = self._add_classification(enhanced)

        # 9. Facets
        enhanced = self._generate_facets(enhanced)

        # 10. Searchability
        enhanced = self._add_searchability_metadata(enhanced, filename)

        # 11. Completeness
        enhanced = self._calculate_completeness(enhanced)

        return enhanced

    def _extract_collection_id(self, filename):
        path = Path(filename)
        ami_match = re.match(r'^([A-Z]+)', path.stem)
        if ami_match:
            return ami_match.group(1)
        if path.parent and path.parent.name not in ['.', '', '/']:
            return path.parent.name
        return "default_collection"

    def _enhance_dates(self, data, filename, ocr_text):
        filename_date = self._extract_date_from_filename(filename)
        content_date = self._extract_date_from_content(ocr_text[:500] if ocr_text else '')
        best_date = filename_date or content_date

        if best_date:
            if 'date' not in data['document']:
                data['document']['date'] = {}

            data['document']['date']['creation_date'] = best_date
            data['document']['date']['sent_date'] = best_date
            data['document']['date']['date_precision'] = 'exact' if filename_date else 'inferred'
            data['document']['date']['date_source'] = 'filename' if filename_date else 'content'

        return data

    def _extract_date_from_filename(self, filename):
        date_pattern = r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})'
        match = re.search(date_pattern, filename, re.IGNORECASE)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).lower()
            year = match.group(3)

            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }

            month_num = month_map.get(month, '01')
            return f"{year}-{month_num}-{day}"
        return None

    def _extract_date_from_content(self, content):
        date_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})'
        match = re.search(date_pattern, content, re.IGNORECASE)
        if match:
            day = match.group(1).zfill(2)
            month_map = {
                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                'september': '09', 'october': '10', 'november': '11', 'december': '12'
            }
            month_num = month_map.get(match.group(2).lower(), '01')
            return f"{match.group(3)}-{month_num}-{day}"
        return None

    def _fix_correspondence(self, data):
        signature = data['content'].get('signature', '')
        salutation = data['content'].get('salutation', '')

        recipient_name = re.sub(r'^Dear\s+', '', salutation, flags=re.IGNORECASE)
        recipient_name = re.sub(r'[,;:]$', '', recipient_name).strip()

        if 'correspondence' in data['document']:
            corresp = data['document']['correspondence']
            if 'correspondence' in corresp:
                corresp = corresp['correspondence']
                data['document']['correspondence'] = corresp

            if signature and 'sender' in corresp and not corresp['sender'].get('name'):
                corresp['sender']['name'] = signature

            if recipient_name and 'recipient' in corresp:
                corresp['recipient']['name'] = recipient_name

        return data

    def _add_ami_metadata(self, data, filename):
        if not self.ami_parser:
            return data
        try:
            ami_result = self.ami_parser.parse(filename)
            if ami_result.get('parsed'):
                data['metadata']['ami_metadata'] = {
                    'master_identifier': ami_result.get('master_identifier'),
                    'collection': ami_result.get('collection'),
                    'series': ami_result.get('series'),
                    'page_number': ami_result.get('page_number'),
                    'sequence_id': ami_result.get('sequence'),
                    'year': ami_result.get('year')
                }
        except:
            pass
        return data

    def _add_temporal_markers(self, data):
        date_str = data['document'].get('date', {}).get('creation_date')
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                if 'date' not in data['document']:
                    data['document']['date'] = {}
                data['document']['date']['temporal_markers'] = {
                    'year': dt.year,
                    'month': dt.month,
                    'day': dt.day,
                    'decade': f"{(dt.year // 10) * 10}s",
                    'quarter': f"Q{(dt.month - 1) // 3 + 1}",
                    'day_of_week': dt.strftime('%A')
                }
            except:
                pass
        return data

    def _add_classification(self, data):
        keywords = data.get('analysis', {}).get('keywords', [])
        topics = [kw.get('keyword', '') for kw in keywords[:5] if kw.get('keyword')]
        subjects = data.get('analysis', {}).get('subjects', [])
        subject_names = [s.get('subject', '') for s in subjects if s.get('subject')]

        data['metadata']['classification'] = {
            'primary_subject': subject_names[0] if subject_names else '',
            'secondary_subjects': subject_names[1:4] if len(subject_names) > 1 else [],
            'topics': topics,
            'genre': 'personal_correspondence'
        }
        return data

    def _generate_facets(self, data):
        facets = {}
        temporal = data['document'].get('date', {}).get('temporal_markers', {})
        if temporal.get('decade'):
            facets['decade'] = temporal['decade']
        if data['metadata'].get('document_type'):
            facets['document_type'] = data['metadata']['document_type']

        languages = data['document'].get('languages', [])
        if languages:
            facets['language'] = languages[0] if isinstance(languages, list) else languages

        if data['metadata'].get('collection_id'):
            facets['collection'] = data['metadata']['collection_id']

        facets['person_count'] = len(data.get('analysis', {}).get('people', []))

        if 'searchability' not in data:
            data['searchability'] = {}
        data['searchability']['facets'] = facets
        return data

    def _add_searchability_metadata(self, data, filename):
        if 'searchability' not in data:
            data['searchability'] = {}

        tags = set()
        for kw in data.get('analysis', {}).get('keywords', [])[:10]:
            if kw.get('keyword'):
                tags.add(kw['keyword'])

        temporal = data['document'].get('date', {}).get('temporal_markers', {})
        if temporal.get('year'):
            tags.add(str(temporal['year']))
        if temporal.get('decade'):
            tags.add(temporal['decade'])

        data['searchability']['tags'] = sorted(list(tags))
        data['searchability']['verification_status'] = 'auto'
        return data

    def _calculate_completeness(self, data):
        required_fields = [
            ('metadata', 'id'),
            ('metadata', 'collection_id'),
            ('content', 'full_text'),
            ('content', 'summary'),
            ('document', 'date', 'creation_date'),
            ('document', 'correspondence', 'sender', 'name'),
            ('document', 'correspondence', 'recipient', 'name'),
        ]

        present = 0
        for field_path in required_fields:
            current = data
            exists = True
            for key in field_path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    exists = False
                    break
            if exists and current:
                present += 1

        score = present / len(required_fields) if required_fields else 0.0

        if 'searchability' not in data:
            data['searchability'] = {}
        data['searchability']['completeness_score'] = round(score, 2)
        data['searchability']['quality_score'] = round(score * 0.95, 2)
        return data


# Test data
def create_sample_data():
    enriched = {
        "metadata": {
            "document_type": "letter",
            "access_level": "private",
            "storage_location": {}
        },
        "document": {
            "date": {},
            "languages": ["en"],
            "physical_attributes": {},
            "correspondence": {
                "sender": {"name": "", "title": "", "affiliation": ""},
                "recipient": {"name": "Last", "title": "", "affiliation": ""},
                "cc": []
            }
        },
        "content": {
            "full_text": "",
            "summary": "Letter about third Vipassana meditation retreat...",
            "salutation": "Dear Babu bhaiya,",
            "body": ["First paragraph...", "Second paragraph..."],
            "closing": "",
            "signature": "Satyanarayan",
            "attachments": [],
            "annotations": []
        },
        "analysis": {
            "keywords": [
                {"keyword": "Vipassanā", "relevance": 0.8, "frequency": 6},
                {"keyword": "Dhamma", "relevance": 0.7, "frequency": 3}
            ],
            "subjects": [{"subject": "personal_matters", "confidence": 0.8}],
            "people": [{"name": "Babu bhaiya", "role": "recipient"}],
            "organizations": [],
            "locations": [{"name": "Mumbai", "type": "city"}],
            "events": [],
            "historical_context": "",
            "significance": "",
            "relationships": []
        }
    }

    ocr = {
        "filename": "From Refusals to Last-Minute Rescue 29 sep 1969 New Delhi.pdf",
        "ocr_text": "29th September 1969, New Delhi.\n\nDear Babu bhaiya,\nRespectful salutations!...\n\nYour younger brother,\nSatyanarayan"
    }

    return enriched, ocr


# Run test
print("="*80)
print("METADATA ENHANCEMENTS - STANDALONE TEST")
print("="*80)

try:
    ami_parser = AMIMetadataParser()
    enhancer = SimpleMetadataEnhancer(ami_parser=ami_parser)

    enriched_data, ocr_data = create_sample_data()
    filename = ocr_data['filename']

    print(f"\n📄 Testing with: {filename}\n")

    enhanced = enhancer.enhance_metadata(
        enriched_data=enriched_data,
        ocr_data=ocr_data,
        filename=filename
    )

    # Verify enhancements
    tests = {
        "UUID Generated": enhanced['metadata'].get('id') and len(enhanced['metadata']['id']) == 36,
        "Collection ID": bool(enhanced['metadata'].get('collection_id')),
        "Full Text": len(enhanced['content'].get('full_text', '')) > 0,
        "Date Extracted": bool(enhanced['document'].get('date', {}).get('creation_date')),
        "Sender Name": enhanced['document']['correspondence']['sender'].get('name') == "Satyanarayan",
        "Recipient Name": enhanced['document']['correspondence']['recipient'].get('name') == "Babu bhaiya",
        "Temporal Markers": bool(enhanced['document'].get('date', {}).get('temporal_markers')),
        "Facets": bool(enhanced.get('searchability', {}).get('facets')),
        "Tags": len(enhanced.get('searchability', {}).get('tags', [])) > 0,
        "Completeness": enhanced.get('searchability', {}).get('completeness_score', 0) > 0
    }

    print("RESULTS:")
    print("-" * 80)
    passed = 0
    for test_name, result in tests.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")
        if result:
            passed += 1

    print(f"\n{passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {len(tests) - passed} tests failed")

    # Show sample output
    print("\n" + "="*80)
    print("SAMPLE OUTPUT")
    print("="*80)
    print(f"\nDocument ID: {enhanced['metadata']['id']}")
    print(f"Collection ID: {enhanced['metadata']['collection_id']}")
    print(f"Creation Date: {enhanced['document']['date'].get('creation_date')}")
    print(f"Decade: {enhanced['document'].get('date', {}).get('temporal_markers', {}).get('decade')}")
    print(f"Sender: {enhanced['document']['correspondence']['sender']['name']}")
    print(f"Recipient: {enhanced['document']['correspondence']['recipient']['name']}")
    print(f"Completeness: {enhanced['searchability']['completeness_score']:.0%}")
    print(f"Facets: {list(enhanced['searchability']['facets'].keys())}")
    print(f"Tags: {enhanced['searchability']['tags'][:5]}")

    # Save output
    output_file = Path(__file__).parent / "test_enhanced_output.json"
    with open(output_file, 'w') as f:
        json.dump(enhanced, f, indent=2)
    print(f"\n💾 Output saved to: {output_file}")

    sys.exit(0 if passed == len(tests) else 1)

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
