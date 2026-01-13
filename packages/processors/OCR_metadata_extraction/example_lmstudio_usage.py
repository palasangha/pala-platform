#!/usr/bin/env python3
"""
LM Studio OCR Provider - Usage Examples

This script demonstrates how to use the LM Studio provider for:
1. Basic text extraction from images
2. Metadata extraction from scanned documents
3. Batch processing multiple files
4. PDF processing
5. Custom prompts for specific tasks
"""

import os
import sys
import json
from pathlib import Path

# Add backend to path (adjust if needed)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.ocr_service import OCRService


def example_1_basic_ocr():
    """Example 1: Extract text from a single image"""
    print("\n" + "="*60)
    print("Example 1: Basic Text Extraction from Image")
    print("="*60)

    ocr_service = OCRService()

    # Check if provider is available
    provider = ocr_service.get_provider('lmstudio')
    if not provider.is_available():
        print("❌ LM Studio provider is not available.")
        print("   Make sure:")
        print("   1. LM Studio is running")
        print("   2. LMSTUDIO_ENABLED=true in .env")
        print("   3. A vision model is loaded")
        return

    print("✓ LM Studio provider is available")

    # Process image
    try:
        # Replace with your actual image path
        image_path = 'sample_letter.jpg'

        if not os.path.exists(image_path):
            print(f"ℹ Image not found: {image_path}")
            print("  Create a test image or provide a valid path")
            return

        result = ocr_service.process_image(
            image_path=image_path,
            provider='lmstudio',
            languages=['en']
        )

        print("\nExtracted Text:")
        print("-" * 40)
        print(result['text'])
        print("-" * 40)

        print(f"\nConfidence: {result['confidence']}")
        print(f"Blocks: {len(result['blocks'])}")

    except Exception as e:
        print(f"❌ Error: {e}")


def example_2_metadata_extraction():
    """Example 2: Extract metadata from a scanned letter"""
    print("\n" + "="*60)
    print("Example 2: Metadata Extraction (Letter)")
    print("="*60)

    ocr_service = OCRService()

    # Custom prompt for metadata extraction
    metadata_prompt = """Analyze this scanned letter and extract the following metadata in JSON format:
    {
        "sender_name": "Full name of sender",
        "sender_address": "Complete mailing address",
        "recipient_name": "Full name of recipient",
        "recipient_address": "Complete mailing address",
        "date": "Date the letter was written",
        "subject": "Main topic or subject of the letter",
        "key_points": ["Important point 1", "Important point 2", "..."],
        "letter_type": "Type of letter (business, personal, official, etc)"
    }

    Extract ONLY the JSON output without any additional text or explanation."""

    try:
        image_path = 'sample_letter.jpg'

        if not os.path.exists(image_path):
            print(f"ℹ Image not found: {image_path}")
            return

        result = ocr_service.process_image(
            image_path=image_path,
            provider='lmstudio',
            custom_prompt=metadata_prompt
        )

        print("\nExtracted Metadata:")
        print("-" * 40)

        # Try to parse as JSON
        try:
            metadata = json.loads(result['text'])
            print(json.dumps(metadata, indent=2))
        except json.JSONDecodeError:
            # If not valid JSON, print as text
            print(result['text'])

        print("-" * 40)

    except Exception as e:
        print(f"❌ Error: {e}")


def example_3_batch_processing():
    """Example 3: Batch process multiple images"""
    print("\n" + "="*60)
    print("Example 3: Batch Processing Multiple Files")
    print("="*60)

    ocr_service = OCRService()

    # List of files to process
    files_to_process = [
        'letter1.jpg',
        'letter2.jpg',
        'letter3.jpg'
    ]

    results = []

    for file_path in files_to_process:
        if not os.path.exists(file_path):
            print(f"⊘ Skipping {file_path} (not found)")
            continue

        try:
            print(f"\nProcessing: {file_path}...", end=' ', flush=True)

            result = ocr_service.process_image(
                image_path=file_path,
                provider='lmstudio',
                languages=['en']
            )

            results.append({
                'file': file_path,
                'text_length': len(result['text']),
                'confidence': result['confidence'],
                'text': result['text'][:100] + '...' if len(result['text']) > 100 else result['text']
            })

            print("✓ Done")

        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "-"*60)
    print("Batch Processing Results:")
    print("-"*60)
    for r in results:
        print(f"\nFile: {r['file']}")
        print(f"  Length: {r['text_length']} chars")
        print(f"  Confidence: {r['confidence']}")
        print(f"  Preview: {r['text']}")


def example_4_pdf_processing():
    """Example 4: Process a multi-page PDF"""
    print("\n" + "="*60)
    print("Example 4: PDF Processing (Multi-page)")
    print("="*60)

    ocr_service = OCRService()

    try:
        pdf_path = 'sample_document.pdf'

        if not os.path.exists(pdf_path):
            print(f"ℹ PDF not found: {pdf_path}")
            print("  Provide a valid PDF path to test")
            return

        print(f"Processing PDF: {pdf_path}...", end=' ', flush=True)

        result = ocr_service.process_image(
            image_path=pdf_path,
            provider='lmstudio',
            languages=['en']
        )

        print("✓ Done\n")

        print(f"Pages Processed: {result.get('pages_processed', 'unknown')}")
        print(f"Total Blocks: {len(result['blocks'])}")
        print(f"Confidence: {result['confidence']}")

        print("\nBlock Details:")
        print("-" * 40)
        for i, block in enumerate(result['blocks'], 1):
            page = block.get('page', '?')
            text_preview = block['text'][:80] + '...' if len(block['text']) > 80 else block['text']
            print(f"Block {i} (Page {page}): {text_preview}")

        print("-" * 40)

    except Exception as e:
        print(f"❌ Error: {e}")


def example_5_custom_extraction():
    """Example 5: Extract specific information with custom prompt"""
    print("\n" + "="*60)
    print("Example 5: Custom Information Extraction")
    print("="*60)

    ocr_service = OCRService()

    # Custom prompt for invoice extraction
    custom_prompt = """Extract invoice information:

    Please extract and return ONLY these fields as JSON:
    {
        "invoice_number": "...",
        "invoice_date": "...",
        "due_date": "...",
        "vendor_name": "...",
        "vendor_address": "...",
        "customer_name": "...",
        "customer_address": "...",
        "total_amount": "...",
        "currency": "...",
        "payment_terms": "...",
        "line_items": [
            {"description": "...", "quantity": "...", "unit_price": "...", "total": "..."}
        ]
    }

    Return ONLY valid JSON, no additional text."""

    try:
        image_path = 'invoice.jpg'

        if not os.path.exists(image_path):
            print(f"ℹ Image not found: {image_path}")
            print("  For this example, use an invoice image")
            return

        print(f"Processing invoice: {image_path}...", end=' ', flush=True)

        result = ocr_service.process_image(
            image_path=image_path,
            provider='lmstudio',
            custom_prompt=custom_prompt
        )

        print("✓ Done\n")

        # Parse and display JSON
        try:
            invoice_data = json.loads(result['text'])
            print("Extracted Invoice Data:")
            print("-" * 40)
            print(json.dumps(invoice_data, indent=2))
        except json.JSONDecodeError:
            print("Response (not valid JSON):")
            print("-" * 40)
            print(result['text'])

    except Exception as e:
        print(f"❌ Error: {e}")


def example_6_multilingual():
    """Example 6: Process multilingual document"""
    print("\n" + "="*60)
    print("Example 6: Multilingual Text Extraction")
    print("="*60)

    ocr_service = OCRService()

    try:
        image_path = 'multilingual_doc.jpg'

        if not os.path.exists(image_path):
            print(f"ℹ Image not found: {image_path}")
            print("  For this example, use a multilingual document")
            return

        # Process with language hints
        result = ocr_service.process_image(
            image_path=image_path,
            provider='lmstudio',
            languages=['en', 'hi', 'es'],  # English, Hindi, Spanish
            handwriting=False
        )

        print("\nExtracted Text (Multilingual):")
        print("-" * 40)
        print(result['text'])
        print("-" * 40)

    except Exception as e:
        print(f"❌ Error: {e}")


def check_provider_availability():
    """Check which providers are available"""
    print("\n" + "="*60)
    print("Available OCR Providers")
    print("="*60)

    ocr_service = OCRService()
    providers = ocr_service.get_available_providers()

    for provider in providers:
        status = "✓" if provider['available'] else "✗"
        print(f"{status} {provider['display_name']} ({provider['name']})")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("LM Studio OCR Provider - Usage Examples")
    print("="*60)

    # Check available providers first
    check_provider_availability()

    # Run examples
    examples = [
        ("1. Basic Text Extraction", example_1_basic_ocr),
        ("2. Metadata Extraction", example_2_metadata_extraction),
        ("3. Batch Processing", example_3_batch_processing),
        ("4. PDF Processing", example_4_pdf_processing),
        ("5. Custom Extraction", example_5_custom_extraction),
        ("6. Multilingual", example_6_multilingual),
    ]

    print("\n" + "="*60)
    print("Running Examples:")
    print("="*60)

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Example failed: {e}")

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)
    print("\nFor detailed documentation, see:")
    print("  - LMSTUDIO_SETUP.md (full guide)")
    print("  - LMSTUDIO_QUICK_START.md (quick reference)")


if __name__ == '__main__':
    main()
