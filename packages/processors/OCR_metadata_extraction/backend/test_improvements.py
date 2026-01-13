#!/usr/bin/env python3
"""
Test script for MiniCPM-V Hindi OCR and PDF metadata extraction
"""
import sys
import os

# Add app to path
sys.path.insert(0, '/app')

from app.services.pdf_service import PDFService
from app.services.ocr_providers.ollama_provider import OllamaProvider

def test_pdf_metadata():
    """Test PDF metadata extraction"""
    print("=" * 60)
    print("TEST 1: PDF Metadata Extraction")
    print("=" * 60)

    # Use first available PDF
    test_pdf = "/app/uploads/691803122872c23ac9e9f628/a77f9ef2-4962-4c5c-ba33-f1ccab3af806.pdf"

    try:
        metadata = PDFService.extract_pdf_metadata(test_pdf)

        print(f"\n📄 PDF File: {os.path.basename(test_pdf)}")
        print(f"\n📊 Metadata:")
        print(f"  • Title: {metadata.get('title', 'N/A')}")
        print(f"  • Author: {metadata.get('author', 'N/A')}")
        print(f"  • Subject: {metadata.get('subject', 'N/A')}")
        print(f"  • Creator: {metadata.get('creator', 'N/A')}")
        print(f"  • Producer: {metadata.get('producer', 'N/A')}")
        print(f"  • Keywords: {metadata.get('keywords', 'N/A')}")
        print(f"  • Page Count: {metadata.get('page_count', 0)}")
        print(f"  • File Size: {metadata.get('file_size_mb', 0)} MB")
        print(f"  • Encrypted: {metadata.get('encrypted', False)}")
        print(f"  • Creation Date: {metadata.get('creation_date', 'N/A')}")
        print(f"  • Modification Date: {metadata.get('modification_date', 'N/A')}")

        print("\n✅ PDF Metadata Extraction: SUCCESS")
        return True
    except Exception as e:
        print(f"\n❌ PDF Metadata Extraction: FAILED")
        print(f"Error: {str(e)}")
        return False

def test_ollama_provider():
    """Test Ollama provider with MiniCPM-V"""
    print("\n" + "=" * 60)
    print("TEST 2: Ollama Provider (MiniCPM-V Model)")
    print("=" * 60)

    try:
        provider = OllamaProvider()

        print(f"\n🤖 Model Information:")
        print(f"  • Host: {provider.host}")
        print(f"  • Model: {provider.model}")
        print(f"  • Available: {provider.is_available()}")

        if provider.is_available():
            print("\n✅ Ollama Provider Initialized: SUCCESS")
            print(f"✅ Using model: {provider.model}")

            # Check if it's the new model
            if 'minicpm' in provider.model.lower():
                print("✅ MiniCPM-V model is being used (optimal for Hindi)")
            else:
                print(f"⚠️  Warning: Using {provider.model} instead of minicpm-v")

            return True
        else:
            print("\n❌ Ollama Provider: NOT AVAILABLE")
            return False

    except Exception as e:
        print(f"\n❌ Ollama Provider: FAILED")
        print(f"Error: {str(e)}")
        return False

def test_hindi_ocr():
    """Test Hindi OCR with an image"""
    print("\n" + "=" * 60)
    print("TEST 3: Hindi OCR Test (with sample image)")
    print("=" * 60)

    # Use first available image
    test_image = "/app/uploads/691491f02e56f9b01aba2dd5/6e7f5f24-178a-4eb3-9800-95398263aff3.jpg"

    if not os.path.exists(test_image):
        print(f"⚠️  Test image not found: {test_image}")
        return False

    try:
        provider = OllamaProvider()

        if not provider.is_available():
            print("❌ Ollama provider not available")
            return False

        print(f"\n🖼️  Processing image: {os.path.basename(test_image)}")
        print("📝 Requesting OCR with Hindi language support...")
        print("⏳ This may take 10-30 seconds depending on image size...\n")

        # Process with Hindi language
        result = provider.process_image(test_image, languages=['hi', 'en'])

        extracted_text = result.get('text', '')

        print("📄 Extracted Text:")
        print("-" * 60)
        print(extracted_text if extracted_text else "(No text extracted)")
        print("-" * 60)

        if extracted_text:
            print(f"\n✅ OCR Extraction: SUCCESS")
            print(f"✅ Extracted {len(extracted_text)} characters")

            # Check if text contains Devanagari characters
            has_devanagari = any('\u0900' <= char <= '\u097F' for char in extracted_text)
            if has_devanagari:
                print("✅ Devanagari script detected in output")

            return True
        else:
            print("\n⚠️  OCR completed but no text was extracted")
            print("   (This might be normal if the image contains no text)")
            return False

    except Exception as e:
        print(f"\n❌ Hindi OCR: FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 TESTING IMPROVEMENTS")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("PDF Metadata", test_pdf_metadata()))
    results.append(("Ollama Provider", test_ollama_provider()))
    results.append(("Hindi OCR", test_hindi_ocr()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)

    sys.exit(0 if passed == total else 1)
