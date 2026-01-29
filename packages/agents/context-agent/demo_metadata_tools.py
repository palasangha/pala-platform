#!/usr/bin/env python3
"""
Practical demonstration of metadata tools

Shows real-world usage of:
1. Metadata Writer (JSON files)
2. EXIF Handler (embedded metadata)
3. Integration with AMI parser
4. Complete enrichment workflow
"""

import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.metadata_writer import MetadataWriter
from tools.exif_metadata_handler import ExifMetadataHandler
from tools.ami_metadata_parser import AMIMetadataParser


def create_sample_document_image(path: str, text: str):
    """Create a sample document image with text"""
    img = Image.new('RGB', (1200, 800), color='#F5F5DC')  # Beige background
    draw = ImageDraw.Draw(img)

    # Add document-like text
    draw.text((50, 50), text, fill='black')
    draw.text((50, 100), "This is a historical document", fill='black')
    draw.text((50, 150), "demonstrating metadata embedding.", fill='black')

    img.save(path, 'JPEG', quality=95)
    print(f"  Created sample image: {path}")


def demo_1_basic_json_metadata():
    """Demo 1: Basic JSON metadata writing"""
    print("\n" + "="*70)
    print("DEMO 1: Basic JSON Metadata")
    print("="*70)

    writer = MetadataWriter()

    # Create sample document
    doc_path = '/tmp/demo/letter_to_student.jpg'
    Path(doc_path).parent.mkdir(parents=True, exist_ok=True)
    create_sample_document_image(doc_path, "Letter to Student")

    # Metadata to save
    metadata = {
        'document_type': 'Letter',
        'title': 'Guidance on Meditation Practice',
        'sender': 'S.N. Goenka',
        'recipient': 'Student Practitioner',
        'date': '1990-05-15',
        'language': 'English',
        'subjects': ['Vipassana', 'Meditation', 'Dhamma'],
        'summary': 'A letter providing guidance on deepening meditation practice.',
        'page_count': 2,
        'quality': 'Good'
    }

    print("\n1. Writing JSON metadata...")
    result = writer.write_metadata(doc_path, metadata)

    if result['success']:
        print(f"  ✓ Metadata file created: {result['output_path']}")
        print(f"  ✓ File size: {result['bytes_written']} bytes")
        print(f"  ✓ Fields saved: {len(result['metadata_keys'])}")

    # Read it back
    print("\n2. Reading metadata back...")
    read_result = writer.read_metadata(result['output_path'])

    if read_result['success']:
        print(f"  ✓ Document type: {read_result['metadata']['document_type']}")
        print(f"  ✓ From: {read_result['metadata']['sender']}")
        print(f"  ✓ To: {read_result['metadata']['recipient']}")
        print(f"  ✓ Date: {read_result['metadata']['date']}")

    return result['output_path']


def demo_2_exif_embedding():
    """Demo 2: EXIF metadata embedding"""
    print("\n" + "="*70)
    print("DEMO 2: EXIF Metadata Embedding")
    print("="*70)

    handler = ExifMetadataHandler()

    # Create sample document
    doc_path = '/tmp/demo/historical_photograph.jpg'
    create_sample_document_image(doc_path, "Historical Photograph")

    # Metadata to embed
    metadata = {
        'title': 'Vipassana Center Opening Ceremony',
        'author': 'Unknown Photographer',
        'date': '1976-10-29T14:30:00',
        'summary': 'Photograph documenting the opening of the Vipassana Meditation Center.',
        'copyright': 'Vipassana Research Institute',
        'location': 'Igatpuri, Maharashtra, India'
    }

    print("\n1. Embedding EXIF metadata...")
    output_path = '/tmp/demo/historical_photograph_with_exif.jpg'
    result = handler.write_exif(doc_path, metadata, output_path)

    if result['success']:
        print(f"  ✓ EXIF embedded: {result['output_path']}")
        print(f"  ✓ Metadata keys: {', '.join(result['metadata_keys'])}")

    # Read EXIF back
    print("\n2. Reading EXIF metadata...")
    exif_result = handler.read_exif(output_path)

    if exif_result['success']:
        exif = exif_result['exif']
        print(f"  ✓ ImageDescription: {exif.get('ImageDescription', 'N/A')}")
        print(f"  ✓ Artist: {exif.get('Artist', 'N/A')}")
        print(f"  ✓ DateTime: {exif.get('DateTime', 'N/A')}")
        print(f"  ✓ Software: {exif.get('Software', 'N/A')}")
        print(f"  ✓ Copyright: {exif.get('Copyright', 'N/A')}")


def demo_3_enriched_copy():
    """Demo 3: Create enriched copy (EXIF + JSON)"""
    print("\n" + "="*70)
    print("DEMO 3: Enriched Copy (EXIF + JSON) ⭐")
    print("="*70)

    handler = ExifMetadataHandler()

    # Create sample document
    doc_path = '/tmp/demo/original_manuscript.jpg'
    create_sample_document_image(doc_path, "Original Manuscript")

    # Complete metadata (from enrichment pipeline)
    enriched_metadata = {
        'document_type': 'Manuscript',
        'title': 'Commentary on Vipassana Technique',
        'author': 'S.N. Goenka',
        'date': '1985-03-20',
        'original_date': '1985-03-20T09:00:00',
        'language': 'Hindi',
        'subjects': ['Vipassana', 'Meditation', 'Buddhist Practice', 'Dhamma'],
        'summary': 'Detailed commentary explaining the theoretical foundation and practical application of Vipassana meditation technique.',
        'historical_context': 'Written during the period of establishing systematic teacher training programs in India.',
        'significance': 'Important teaching document used in early meditation courses.',
        'page_count': 15,
        'condition': 'Excellent',
        'digitization_date': '2025-01-15',
        'digitized_by': 'Heritage Platform',
        'quality_score': 98
    }

    print("\n1. Creating enriched copy...")
    result = handler.create_copy_with_metadata(
        doc_path,
        enriched_metadata,
        output_dir='/tmp/demo/enriched',
        suffix='_enriched'
    )

    if result['success']:
        print(f"  ✓ Original: {result['original_image']}")
        print(f"  ✓ Enriched image: {result['enriched_image']}")
        print(f"  ✓ Metadata JSON: {result['metadata_json']}")
        print(f"  ✓ EXIF embedded: {result['exif_embedded']}")
        print(f"\n  File sizes:")
        print(f"    - Original: {result['file_sizes']['original']:,} bytes")
        print(f"    - Enriched image: {result['file_sizes']['enriched_image']:,} bytes")
        print(f"    - Metadata JSON: {result['file_sizes']['metadata_json']:,} bytes")
        print(f"    - Total enriched: {result['file_sizes']['enriched_image'] + result['file_sizes']['metadata_json']:,} bytes")

    return result if result['success'] else None


def demo_4_ami_integration():
    """Demo 4: Full pipeline with AMI parser"""
    print("\n" + "="*70)
    print("DEMO 4: Complete Pipeline (AMI + Enrichment + EXIF)")
    print("="*70)

    ami_parser = AMIMetadataParser()
    handler = ExifMetadataHandler()

    # AMI filename
    ami_filename = "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG"

    print(f"\n1. Parsing AMI filename...")
    print(f"   {ami_filename}")

    parsed = ami_parser.parse(ami_filename)

    if parsed['parsed']:
        print(f"  ✓ Document Type: {parsed['document_type_full']}")
        print(f"  ✓ From: {parsed['sender']}")
        print(f"  ✓ To: {parsed['recipient']}")
        print(f"  ✓ Date: {parsed['year']}")
        print(f"  ✓ Medium: {parsed['medium_full']}")
        print(f"  ✓ Sequence: {parsed['sequence']}")

    # Create sample image with this filename
    doc_path = f'/tmp/demo/{ami_filename}'
    create_sample_document_image(doc_path, f"Letter from {parsed['sender']}")

    print(f"\n2. Simulating AI enrichment...")

    # Simulate enrichment results
    enrichment = {
        'summary': f"Letter from {parsed['sender']} to {parsed['recipient']} discussing matters of mutual interest and spiritual practice.",
        'historical_context': 'Part of correspondence between key figures in the Buddhist revival movement of the 1990s.',
        'significance': 'Documents important historical relationships and teachings.',
        'subjects': ['Letters', 'Buddhist Teachings', 'Historical Correspondence'],
        'language': 'English',
        'biographies': {
            parsed['sender']: f"{parsed['sender']} was an important figure in the Buddhist community.",
            parsed['recipient']: f"{parsed['recipient']} was a notable scholar and practitioner."
        }
    }

    print(f"  ✓ Generated summary")
    print(f"  ✓ Generated historical context")
    print(f"  ✓ Assessed significance")
    print(f"  ✓ Created biographies")

    # Combine AMI + Enrichment
    print(f"\n3. Combining AMI metadata + enrichment...")

    full_metadata = {
        **parsed,
        **enrichment,
        'archipelago_fields': ami_parser.get_archipelago_fields(parsed),
        'enrichment_date': '2026-01-29',
        'enriched_by': 'Heritage Platform AI Pipeline'
    }

    print(f"  ✓ Combined {len(parsed)} AMI fields + {len(enrichment)} enrichment fields")

    # Create enriched copy
    print(f"\n4. Creating enriched archive copy...")

    result = handler.create_copy_with_metadata(
        doc_path,
        full_metadata,
        output_dir='/tmp/demo/archive',
        suffix='_archive'
    )

    if result['success']:
        print(f"  ✓ Archive image: {Path(result['enriched_image']).name}")
        print(f"  ✓ Archive metadata: {Path(result['metadata_json']).name}")
        print(f"  ✓ EXIF embedded: {result['exif_embedded']}")
        print(f"  ✓ Ready for long-term preservation")


def demo_5_batch_processing():
    """Demo 5: Batch processing multiple documents"""
    print("\n" + "="*70)
    print("DEMO 5: Batch Processing")
    print("="*70)

    handler = ExifMetadataHandler()

    # Create multiple documents
    print("\n1. Preparing batch of 5 documents...")

    batch = []
    for i in range(1, 6):
        doc_path = f'/tmp/demo/batch/document_{i:03d}.jpg'
        Path(doc_path).parent.mkdir(parents=True, exist_ok=True)
        create_sample_document_image(doc_path, f"Document {i}")

        metadata = {
            'document_id': f'DOC{i:03d}',
            'document_type': ['Letter', 'Diary', 'Newsletter', 'Manuscript', 'Photograph'][i-1],
            'title': f'Historical Document {i}',
            'date': f'199{i}-01-15',
            'summary': f'This is the summary for document {i}.',
            'page_count': i
        }

        batch.append({
            'image_path': doc_path,
            'metadata': metadata,
            'suffix': '_processed'
        })

    print(f"  ✓ Created {len(batch)} sample documents")

    # Process batch
    print(f"\n2. Processing batch...")

    result = handler.batch_create_copies(batch, output_dir='/tmp/demo/batch/processed')

    print(f"\n  Results:")
    print(f"    ✓ Total: {result['total']}")
    print(f"    ✓ Successful: {result['successful']}")
    print(f"    ✗ Failed: {result['failed']}")

    if result['successful'] > 0:
        print(f"\n  Sample outputs:")
        for i, output in enumerate(result['outputs'][:3], 1):
            print(f"    {i}. {Path(output['enriched_image']).name}")
            print(f"       {Path(output['metadata_json']).name}")


def main():
    """Run all demonstrations"""
    print("\n" + "="*70)
    print("METADATA TOOLS - PRACTICAL DEMONSTRATIONS")
    print("="*70)
    print("\nShowing real-world usage of metadata tools for heritage documents")

    try:
        # Clean up old demo files
        import shutil
        if Path('/tmp/demo').exists():
            shutil.rmtree('/tmp/demo')

        # Run demos
        demo_1_basic_json_metadata()
        demo_2_exif_embedding()
        demo_3_enriched_copy()
        demo_4_ami_integration()
        demo_5_batch_processing()

        # Summary
        print("\n" + "="*70)
        print("DEMONSTRATION COMPLETE")
        print("="*70)
        print("\nAll demonstrations completed successfully! ✓")
        print("\nGenerated files available in /tmp/demo/:")
        print("  - /tmp/demo/*.jpg (original samples)")
        print("  - /tmp/demo/*_metadata.json (JSON metadata)")
        print("  - /tmp/demo/enriched/ (enriched copies)")
        print("  - /tmp/demo/archive/ (archive copies)")
        print("  - /tmp/demo/batch/processed/ (batch outputs)")

        print("\n" + "="*70)
        print("KEY TAKEAWAYS")
        print("="*70)
        print("\n1. JSON metadata: Flexible, complete, easy to process")
        print("2. EXIF embedding: Portable, embedded in image")
        print("3. Enriched copies: Best of both worlds (EXIF + JSON)")
        print("4. AMI integration: Seamless filename parsing + enrichment")
        print("5. Batch processing: Efficient for large collections")

        print("\n⭐ Recommended: Use 'create_enriched_copy' for everything!")
        print("   - Preserves original")
        print("   - Embeds EXIF in image")
        print("   - Creates complete JSON sidecar")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
