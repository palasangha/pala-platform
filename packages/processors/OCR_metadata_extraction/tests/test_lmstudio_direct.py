#!/usr/bin/env python3
"""
Direct LM Studio API Test - Extract Metadata from PDF
No Flask/app dependencies needed
"""

import json
import base64
import requests
import sys
from pathlib import Path
from datetime import datetime

def test_lmstudio():
    """Test LM Studio connectivity and extract metadata"""
    
    # Check LM Studio is running
    print("Testing LM Studio connection...")
    try:
        response = requests.get('http://localhost:1234/v1/models', timeout=5)
        if response.status_code == 200:
            print("✓ LM Studio is available")
            models = response.json()
            print(f"  Available models: {json.dumps(models, indent=2)[:200]}...\n")
        else:
            print(f"✗ LM Studio returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to LM Studio: {e}")
        print("\nMake sure LM Studio is running:")
        print("  docker-compose up -d lmstudio")
        return False

    # Test with a simple image if available
    print("Testing metadata extraction...")
    
    # Create a simple test image (white rectangle with text)
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("⚠ PIL not available, using test prompt only")
        test_simple_request()
        return True

    # Create test image
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "INVOICE #INV-001\nDate: 2024-01-15\nTotal: $1500.00", fill='black')
    
    # Save temporarily
    img_path = '/tmp/test_invoice.png'
    img.save(img_path)
    print(f"✓ Created test image: {img_path}")

    # Convert to base64
    with open(img_path, 'rb') as f:
        img_base64 = base64.b64encode(f.read()).decode('utf-8')

    # Create request
    prompt = """Extract all visible text and metadata from this image.
Return ONLY valid JSON with no markdown or explanations.
{
  "document_type": "identify if invoice, form, letter, etc",
  "text_content": "all visible text",
  "extracted_data": {
    "invoice_number": "if present",
    "date": "if present",
    "amount": "if present"
  }
}"""

    payload = {
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
        "max_tokens": 2048,
        "temperature": 0.1
    }

    headers = {"Content-Type": "application/json"}

    print("Sending request to LM Studio...")
    try:
        response = requests.post(
            'http://localhost:1234/v1/chat/completions',
            json=payload,
            headers=headers,
            timeout=600
        )

        if response.status_code != 200:
            print(f"✗ API returned status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False

        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content'].strip()
            print(f"✓ Got response from LM Studio\n")
            print("Response Content:")
            print("=" * 70)
            print(content)
            print("=" * 70)

            # Try to parse as JSON
            try:
                metadata = json.loads(content)
                print("\n✓ Response is valid JSON")
                print("\nParsed Metadata:")
                print(json.dumps(metadata, indent=2))
                return True
            except json.JSONDecodeError as e:
                print(f"\n⚠ Response is not valid JSON: {e}")
                print("Raw response (first 500 chars):")
                print(content[:500])
                return False
        else:
            print("✗ No content in response")
            return False

    except requests.exceptions.Timeout:
        print("✗ Request timed out (600s)")
        return False
    except Exception as e:
        print(f"✗ Request failed: {e}")
        return False


def test_simple_request():
    """Test with simple text prompt"""
    print("\nSending simple test request...")
    
    payload = {
        "model": "local-model",
        "messages": [
            {
                "role": "user",
                "content": "Return valid JSON: {\"test\": \"working\"}"
            }
        ],
        "max_tokens": 100,
        "temperature": 0.1
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            'http://localhost:1234/v1/chat/completions',
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print("✓ Text request successful")
            print(json.dumps(result, indent=2)[:300])
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == '__main__':
    success = test_lmstudio()
    sys.exit(0 if success else 1)
