#!/usr/bin/env python3
"""
Direct LM Studio API Test - With proper JSON parsing
"""

import json
import base64
import requests
import re
from pathlib import Path

def clean_json_response(response_text):
    """Clean LM Studio response (remove markdown code blocks)"""
    # Remove markdown code blocks
    if response_text.startswith('```'):
        # Remove opening ```json or ```
        response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
        # Remove closing ```
        response_text = re.sub(r'\s*```$', '', response_text)
    return response_text.strip()

def extract_metadata_from_pdf(pdf_path, metadata_type='invoice'):
    """Extract metadata from real PDF file"""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"✗ File not found: {pdf_path}")
        return None

    print(f"\n{'='*70}")
    print(f"PDF Metadata Extraction Test")
    print(f"{'='*70}\n")
    
    print(f"File: {pdf_file.name}")
    print(f"Size: {pdf_file.stat().st_size / 1024:.1f} KB")
    print(f"Type: {metadata_type}\n")

    # Import PDF processing
    try:
        import fitz
        from PIL import Image
        from io import BytesIO
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Install with: pip install pymupdf pillow")
        return None

    # Convert PDF to images
    print("Converting PDF to images...")
    try:
        pdf_doc = fitz.open(pdf_path)
        page_images = []

        for page_num in range(min(len(pdf_doc), 3)):  # First 3 pages
            page = pdf_doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")
            page_images.append((page_num + 1, img_data))

        print(f"✓ Extracted {len(page_images)} page image(s)\n")

    except Exception as e:
        print(f"✗ PDF processing failed: {e}")
        return None

    # LM Studio settings
    lmstudio_host = 'http://localhost:1234'
    model = 'google/gemma-3-27b'  # Use available model

    # Prompts by type
    prompts = {
        'invoice': """Extract invoice metadata. Return ONLY valid JSON:
{
  "document_type": "invoice",
  "invoice_number": "...",
  "invoice_date": "...",
  "due_date": "...",
  "vendor_name": "...",
  "customer_name": "...",
  "total_amount": "...",
  "currency": "..."
}""",

        'generic': """Extract document metadata. Return ONLY valid JSON:
{
  "document_type": "identify type",
  "title": "...",
  "date": "...",
  "pages": "...",
  "parties": [],
  "key_amounts": []
}"""
    }

    prompt = prompts.get(metadata_type, prompts['generic'])

    # Process pages
    results = []
    print("Extracting metadata from pages...\n")

    for page_num, img_data in page_images:
        print(f"  Page {page_num}...", end=" ", flush=True)

        # Encode image
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        # Create API request
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                f"{lmstudio_host}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=600
            )

            if response.status_code == 200:
                result = response.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    
                    # Clean JSON
                    cleaned = clean_json_response(content)
                    
                    try:
                        metadata = json.loads(cleaned)
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
                            "raw": content[:300]
                        })
                        print("⚠ (parse error)")
                else:
                    print("✗ (no content)")
            else:
                print(f"✗ (HTTP {response.status_code})")

        except Exception as e:
            print(f"✗ ({str(e)[:30]})")

    return results


def main():
    # Check LM Studio
    print("Checking LM Studio...")
    try:
        response = requests.get('http://localhost:1234/v1/models', timeout=5)
        if response.status_code == 200:
            print("✓ LM Studio is running\n")
        else:
            print(f"✗ LM Studio returned {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Cannot connect to LM Studio: {e}")
        print("\nStart LM Studio with:")
        print("  docker-compose up -d lmstudio")
        return

    # Get PDF file
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        # Use first available PDF
        from pathlib import Path
        pdfs = list(Path('/mnt/sda1/mango1_home/gvpocr/backend/uploads').glob('**/*.pdf'))
        if pdfs:
            pdf_file = pdfs[0]
            print(f"Using PDF: {pdf_file.name}\n")
        else:
            print("✗ No PDF files found")
            return

    # Extract metadata
    results = extract_metadata_from_pdf(str(pdf_file))

    if results:
        print(f"\n{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        for result in results:
            print(f"\nPage {result['page']}:")
            if result['status'] == 'success':
                print(json.dumps(result['metadata'], indent=2))
            else:
                print(f"Status: {result['status']}")
                if 'raw' in result:
                    print(f"Response: {result['raw']}")

        # Save results
        output = {
            "pdf_file": str(pdf_file),
            "pages_processed": len(results),
            "results": results
        }

        output_file = Path(pdf_file).stem + '_metadata.json'
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n{'='*70}")
        print(f"Saved to: {output_file}")
        print(f"{'='*70}\n")
    else:
        print("✗ No metadata extracted")


if __name__ == '__main__':
    import sys
    main()
