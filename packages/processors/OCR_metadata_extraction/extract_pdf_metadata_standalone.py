#!/usr/bin/env python3
"""
Standalone PDF Metadata Extraction Script
Direct LM Studio API access - no Flask dependency
"""

import json
import sys
import os
import base64
import requests
from pathlib import Path
from datetime import datetime

# Pre-built metadata extraction prompts
METADATA_PROMPTS = {
    'invoice': """You are an expert invoice analyst. Extract ALL invoice metadata from this image.
Return ONLY valid JSON (no markdown, no explanations):
{
  "document_type": "invoice",
  "invoice_number": "...",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "vendor_name": "...",
  "vendor_address": "...",
  "customer_name": "...",
  "customer_address": "...",
  "items": [{"description": "...", "qty": "...", "price": "...", "total": "..."}],
  "subtotal": "...",
  "tax_amount": "...",
  "total_amount": "...",
  "currency": "USD"
}""",

    'contract': """You are an expert contract analyst. Extract ALL contract metadata from this image.
Return ONLY valid JSON (no markdown, no explanations):
{
  "document_type": "contract",
  "contract_title": "...",
  "contract_date": "YYYY-MM-DD",
  "parties": ["party1", "party2"],
  "total_value": "...",
  "currency": "USD",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "key_obligations": "...",
  "governing_law": "..."
}""",

    'form': """You are an expert form analyzer. Extract ALL form data from this image.
Return ONLY valid JSON (no markdown, no explanations):
{
  "document_type": "form",
  "form_name": "...",
  "fields": [
    {"field_name": "...", "field_value": "...", "field_type": "..."}
  ],
  "completed_by": "...",
  "date_completed": "YYYY-MM-DD",
  "signatures_present": true
}""",

    'generic': """You are a universal document analyzer. Extract ALL metadata from this document.
Return ONLY valid JSON (no markdown, no explanations):
{
  "document_type": "identify type",
  "title": "...",
  "date": "YYYY-MM-DD",
  "pages": "...",
  "parties": ["..."],
  "key_amounts": [{"value": "...", "description": "..."}],
  "action_items": [{"action": "...", "deadline": "YYYY-MM-DD"}]
}"""
}


def extract_metadata_direct(pdf_path, metadata_type='generic', lmstudio_host='http://localhost:1234'):
    """
    Extract metadata directly from LM Studio API (no Flask needed)
    """

    # Validate file
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return {"status": "error", "error": f"File not found: {pdf_path}"}

    if not pdf_file.suffix.lower() == '.pdf':
        return {"status": "error", "error": f"Not a PDF file: {pdf_path}"}

    print(f"\n{'='*70}")
    print("PDF METADATA EXTRACTION (Direct LM Studio API)")
    print(f"{'='*70}\n")

    print(f"File: {pdf_file.absolute()}")
    print(f"Size: {pdf_file.stat().st_size / 1024:.1f} KB")
    print(f"Type: {metadata_type}")

    # Check if LM Studio is available
    print("\nChecking LM Studio availability...", end=" ")
    try:
        response = requests.get(f"{lmstudio_host}/v1/models", timeout=5)
        if response.status_code != 200:
            return {"status": "error", "error": f"LM Studio returned {response.status_code}"}
        print("✓")
    except Exception as e:
        return {
            "status": "error",
            "error": f"Cannot connect to LM Studio at {lmstudio_host}: {str(e)}"
        }

    # Convert PDF to images
    print("Converting PDF to images...")
    try:
        from PIL import Image
        import fitz  # PyMuPDF

        pdf_doc = fitz.open(pdf_path)
        page_images = []

        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("ppm")
            img = Image.open(pd.BytesIO(img_data) if hasattr(pd, 'BytesIO') else None)

            # Alternative: use simple zoom render
            pix = page.get_pixmap(zoom=2)
            png_data = pix.tobytes("png")
            page_images.append((page_num + 1, png_data))

        print(f"✓ Converted {len(page_images)} page(s)")

    except ImportError:
        print("⚠ PyMuPDF not available, trying alternative method...")
        return {
            "status": "error",
            "error": "PDF processing requires PyMuPDF. Install with: pip install PyMuPDF"
        }
    except Exception as e:
        return {"status": "error", "error": f"PDF conversion failed: {str(e)}"}

    # Select prompt
    prompt = METADATA_PROMPTS.get(metadata_type, METADATA_PROMPTS['generic'])

    # Process first page (or all pages for batch)
    print(f"Extracting metadata from {len(page_images)} page(s)...")
    results = []

    for page_num, img_data in page_images[:1]:  # Just first page for demo
        print(f"  Page {page_num}...", end=" ")

        # Encode to base64
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        # Create API request
        api_payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1
        }

        headers = {"Content-Type": "application/json"}

        try:
            # Send to LM Studio
            api_response = requests.post(
                f"{lmstudio_host}/v1/chat/completions",
                json=api_payload,
                headers=headers,
                timeout=600
            )

            if api_response.status_code != 200:
                print(f"✗ (HTTP {api_response.status_code})")
                continue

            result = api_response.json()

            # Extract content
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()

                try:
                    metadata = json.loads(content)
                    results.append({
                        "page": page_num,
                        "status": "success",
                        "metadata": metadata
                    })
                    print("✓")
                except json.JSONDecodeError:
                    results.append({
                        "page": page_num,
                        "status": "partial",
                        "raw_content": content[:500]
                    })
                    print("⚠ (not valid JSON)")
            else:
                print("✗ (no content)")

        except requests.exceptions.Timeout:
            print("✗ (timeout)")
        except Exception as e:
            print(f"✗ ({str(e)[:30]})")

    # Return results
    if results:
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "pdf_file": str(pdf_file.absolute()),
            "metadata_type": metadata_type,
            "pages_processed": len(results),
            "results": results
        }
    else:
        return {
            "status": "error",
            "error": "No metadata extracted"
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_pdf_metadata_standalone.py <pdf_file> [metadata_type]")
        print("\nMetadata types: invoice, contract, form, generic")
        sys.exit(1)

    pdf_file = sys.argv[1]
    metadata_type = sys.argv[2] if len(sys.argv) > 2 else 'generic'

    result = extract_metadata_direct(pdf_file, metadata_type)

    print(f"\n{'='*70}")
    print("RESULT")
    print(f"{'='*70}\n")
    print(json.dumps(result, indent=2))

    # Save results
    output_file = Path(pdf_file).stem + '_metadata_direct.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to: {output_file}\n")


if __name__ == '__main__':
    main()
