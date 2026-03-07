#!/usr/bin/env python3
"""
Test script to demonstrate data mapping from OCR format to Archipelago format
"""

import json
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.data_mapper import DataMapper


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
    print(f"   OCR 'name' → Archipelago 'label': {mapped_data.get('label', 'N/A')[:50]}...")
    print(f"   OCR 'text' → Archipelago 'note': {len(mapped_data.get('note', ''))} chars")
    print(f"   OCR 'description' → Archipelago 'description': {mapped_data.get('description', 'N/A')[:50]}...")
    print(f"   OCR 'dateCreated' → Archipelago 'date_created': {mapped_data.get('date_created', 'N/A')}")
    print(f"   OCR language '{ocr_data.get('ocr_metadata', {}).get('language')}' → Archipelago language: {mapped_data.get('language', [])}")

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
    print(f"   File attachment structure: {'as:document' in mapped_data}")

    print("\n" + "=" * 80)
    print("Mapping completed successfully!")
    print("=" * 80)
    print(f"\nYou can review the full mapped output in: {output_file}")
    print("\nTo use this in your application:")
    print("  from app.services.archipelago_service import ArchipelagoService")
    print("  service = ArchipelagoService()")
    print("  result = service.create_digital_object_from_ocr_data(ocr_data)")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
