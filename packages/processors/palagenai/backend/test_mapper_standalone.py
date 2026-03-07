#!/usr/bin/env python3
"""
Standalone test script for data mapper (no Flask dependencies)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class DataMapper:
    """Maps data from input OCR format to Archipelago template format"""

    @staticmethod
    def map_ocr_to_archipelago(
        ocr_data: Dict[str, Any],
        collection_id: Optional[str] = None,
        file_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Map OCR data format to Archipelago template format"""

        # Extract basic information from OCR data
        name = ocr_data.get('name', '')
        text = ocr_data.get('text', '')
        label = ocr_data.get('label', name)
        description = ocr_data.get('description', '')

        # Extract file information
        file_info = ocr_data.get('file_info', {})
        filename = file_info.get('filename', name)
        file_path = file_info.get('file_path', '')

        # Extract OCR metadata
        ocr_metadata = ocr_data.get('ocr_metadata', {})
        language_code = ocr_metadata.get('language', 'en')

        # Map language codes to full names
        language_map = {
            'en': 'English',
            'hi': 'Hindi',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ar': 'Arabic',
            'ru': 'Russian',
            'pt': 'Portuguese',
            'it': 'Italian'
        }
        language = [language_map.get(language_code, language_code)]

        # Extract generator info
        generator_info = ocr_data.get('as:generator', {})
        if not generator_info:
            generator_info = {
                'type': 'Update',
                'actor': {
                    'url': 'http://localhost:8001/form/descriptive-metadata',
                    'name': 'descriptive_metadata',
                    'type': 'Service'
                },
                'endTime': datetime.utcnow().isoformat() + 'Z',
                'summary': 'Generator',
                '@context': 'https://www.w3.org/ns/activitystreams'
            }

        # Build the as:document structure if we have file information
        as_document = {}
        if file_id and filename:
            doc_uuid = str(uuid.uuid4())

            # Determine mime type from filename
            mime_type = 'application/octet-stream'
            if filename.lower().endswith('.pdf'):
                mime_type = 'application/pdf'
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif filename.lower().endswith('.png'):
                mime_type = 'image/png'
            elif filename.lower().endswith('.tif'):
                mime_type = 'image/tiff'

            as_document = {
                f"urn:uuid:{doc_uuid}": {
                    'url': f"s3://files/{filename}",
                    'name': filename,
                    'tags': [],
                    'type': 'Document',
                    'dr:fid': file_id,
                    'dr:for': 'documents',
                    'dr:uuid': doc_uuid,
                    'checksum': '',
                    'sequence': 1,
                    'dr:filesize': 0,
                    'dr:mimetype': mime_type,
                    'crypHashFunc': 'md5'
                }
            }

        # Build description if not provided
        if not description:
            ocr_desc_parts = []
            provider = ocr_metadata.get('provider', '')
            if provider:
                ocr_desc_parts.append(f"Processed using {provider.replace('_', ' ').title()} OCR")

            confidence = ocr_metadata.get('confidence')
            if confidence:
                ocr_desc_parts.append(f"Confidence: {confidence*100:.1f}%")

            word_count = ocr_metadata.get('word_count')
            if word_count:
                ocr_desc_parts.append(f"{word_count} words")

            char_count = ocr_metadata.get('character_count')
            if char_count:
                ocr_desc_parts.append(f"{char_count} characters")

            if ocr_desc_parts:
                description = '. '.join(ocr_desc_parts) + '.'

        # Build the Archipelago template structure
        archipelago_data = {
            'note': text[:5000] if text else '',  # Limit note to 5000 chars
            'type': ocr_data.get('@type', 'DigitalDocument'),
            'viaf': '',
            'label': label,
            'model': [],
            'owner': '',
            'audios': [],
            'images': [],
            'models': [],
            'rights': '',
            'videos': [],
            'creator': '',
            'ap:tasks': {
                'ap:sortfiles': 'index'
            },
            'duration': '',
            'ispartof': [],
            'language': language,
            'documents': [file_id] if file_id else [],
            'edm_agent': '',
            'publisher': '',
            'ismemberof': [collection_id] if collection_id else [],
            'as:document': as_document,
            'creator_lod': [],
            'description': description,
            'interviewee': '',
            'interviewer': '',
            'pubmed_mesh': None,
            'sequence_id': '',
            'subject_loc': [],
            'website_url': '',
            'as:generator': generator_info,
            'date_created': ocr_data.get('dateCreated', datetime.utcnow().isoformat()),
            'issue_number': None,
            'date_published': '',
            'subjects_local': None,
            'term_aat_getty': '',
            'ap:entitymapping': {
                'entity:file': [
                    'model',
                    'audios',
                    'images',
                    'videos',
                    'documents',
                    'upload_associated_warcs'
                ],
                'entity:node': [
                    'ispartof',
                    'ismemberof'
                ]
            },
            'europeana_agents': '',
            'europeana_places': [],
            'local_identifier': '',
            'subject_wikidata': [],
            'date_created_edtf': '',
            'date_created_free': None,
            'date_embargo_lift': None,
            'physical_location': None,
            'related_item_note': None,
            'rights_statements': '',
            'europeana_concepts': [],
            'geographic_location': {},
            'note_publishinginfo': None,
            'subject_lcgft_terms': '',
            'upload_associated_warcs': [],
            'physical_description_extent': '',
            'subject_lcnaf_personal_names': '',
            'subject_lcnaf_corporate_names': '',
            'subjects_local_personal_names': '',
            'related_item_host_location_url': None,
            'subject_lcnaf_geographic_names': [],
            'related_item_host_display_label': None,
            'related_item_host_local_identifier': None,
            'related_item_host_title_info_title': '',
            'related_item_host_type_of_resource': None,
            'physical_description_note_condition': None
        }

        # Add keywords if present
        keywords = ocr_data.get('keywords', [])
        if keywords:
            archipelago_data['subjects_local'] = ', '.join(keywords)

        return archipelago_data


def main():
    # Read the input OCR data
    input_file = Path(__file__).parent / 'input_ocr_data.json'
    template_file = Path(__file__).parent / 'archipelago-template.json'
    output_file = Path(__file__).parent / 'mapped_output.json'

    print("=" * 80)
    print("Data Mapper Test - OCR Format to Archipelago Format")
    print("=" * 80)

    # Load input OCR data
    print(f"\n1. Loading input OCR data from: {input_file}")
    with open(input_file, 'r') as f:
        ocr_data = json.load(f)

    print(f"   ✓ Loaded OCR data for: {ocr_data.get('name', 'Unknown')}")

    # Load template for reference
    print(f"\n2. Loading Archipelago template from: {template_file}")
    with open(template_file, 'r') as f:
        template_data = json.load(f)

    print(f"   ✓ Loaded template (type: {template_data.get('type', 'Unknown')})")

    # Map the data
    print("\n3. Mapping OCR data to Archipelago format...")
    try:
        mapped_data = DataMapper.map_ocr_to_archipelago(
            ocr_data=ocr_data,
            collection_id=110,  # Example collection ID
            file_id=49  # Example file ID
        )
        print("   ✓ Successfully mapped data")
    except Exception as e:
        print(f"   ✗ Error mapping data: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    # Save mapped output
    print(f"\n4. Saving mapped data to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(mapped_data, f, indent=4, ensure_ascii=False)
    print("   ✓ Saved mapped data")

    # Compare structures
    print("\n5. Comparing data structures:")
    print(f"   Input OCR format fields: {len(ocr_data.keys())}")
    print(f"   Template format fields: {len(template_data.keys())}")
    print(f"   Mapped output fields: {len(mapped_data.keys())}")

    # Show key field mappings
    print("\n6. Key field mappings:")
    print(f"   OCR 'name' → Archipelago 'label':")
    print(f"      {mapped_data.get('label', 'N/A')[:70]}...")
    print(f"   OCR 'text' → Archipelago 'note': {len(mapped_data.get('note', ''))} chars")
    print(f"   OCR 'description' → Archipelago 'description':")
    print(f"      {mapped_data.get('description', 'N/A')[:70]}...")
    print(f"   OCR 'dateCreated' → Archipelago 'date_created':")
    print(f"      {mapped_data.get('date_created', 'N/A')}")
    ocr_lang = ocr_data.get('ocr_metadata', {}).get('language')
    print(f"   OCR language '{ocr_lang}' → Archipelago language: {mapped_data.get('language', [])}")

    # Show metadata preservation
    print("\n7. Metadata preservation check:")
    ocr_meta = ocr_data.get('ocr_metadata', {})
    print(f"   ✓ OCR provider: {ocr_meta.get('provider', 'N/A')}")
    print(f"   ✓ Confidence: {ocr_meta.get('confidence', 'N/A')}")
    print(f"   ✓ Word count: {ocr_meta.get('word_count', 'N/A')}")
    print(f"   ✓ Character count: {ocr_meta.get('character_count', 'N/A')}")

    # Show collection linking
    print("\n8. Collection and file references:")
    print(f"   Collection ID (ismemberof): {mapped_data.get('ismemberof', [])}")
    print(f"   Document reference (documents): {mapped_data.get('documents', [])}")
    print(f"   File attachment structure: {'as:document' in mapped_data and bool(mapped_data['as:document'])}")

    print("\n" + "=" * 80)
    print("✓ Mapping completed successfully!")
    print("=" * 80)
    print(f"\nMapped output saved to: {output_file}")
    print("\nTo use this in your application:")
    print("  from app.services.archipelago_service import ArchipelagoService")
    print("  service = ArchipelagoService()")
    print("  result = service.create_digital_object_from_ocr_data(ocr_data)")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
