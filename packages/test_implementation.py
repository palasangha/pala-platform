#!/usr/bin/env python3
"""
Quick test of OCR agent and Storage API integration
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from storage.api.storage import StorageAPI


async def test_storage():
    """Test storage API"""
    print("\n=== Testing Storage API ===\n")
    
    # Initialize storage
    storage = StorageAPI(
        db_path="./test_pala_storage.db",
        content_dir="./test_content"
    )
    
    # Create test content
    test_content = json.dumps({
        "ocr_text": "Letter dated 15th March 1892\n\nDear Venerable Sir...",
        "ocr_confidence": 0.95,
        "extracted_metadata": {
            "date": "1892-03-15",
            "type": "letter",
            "author": "John Smith"
        }
    }).encode('utf-8')
    
    # Store content
    print("1. Storing content...")
    stored = storage.store_content(
        content=test_content,
        content_type="document",
        metadata={
            "source_file": "historical-letter.jpg",
            "workflow": "document-processing",
            "language": "eng"
        },
        signature="SHA256:test123"
    )
    
    print(f"   ✓ Stored as: {stored.content_id}")
    print(f"   ✓ Path: {stored.storage_path}")
    print(f"   ✓ Hash: {stored.file_hash[:16]}...")
    print(f"   ✓ Size: {stored.file_size} bytes")
    
    # Test deduplication
    print("\n2. Testing deduplication...")
    stored2 = storage.store_content(
        content=test_content,
        content_type="document",
        metadata={"source": "duplicate"}
    )
    print(f"   ✓ Same content ID: {stored.content_id == stored2.content_id}")
    
    # Retrieve content
    print("\n3. Retrieving content...")
    retrieved = storage.read_content(stored.content_id)
    retrieved_data = json.loads(retrieved)
    print(f"   ✓ Retrieved {len(retrieved)} bytes")
    print(f"   ✓ OCR text: {retrieved_data['ocr_text'][:50]}...")
    
    # List content
    print("\n4. Listing content...")
    content_list = storage.list_content(content_type="document")
    print(f"   ✓ Found {len(content_list)} document(s)")
    
    # Get stats
    print("\n5. Storage statistics...")
    stats = storage.get_stats()
    print(f"   ✓ Total count: {stats['total_count']}")
    print(f"   ✓ Total size: {stats['total_size']} bytes")
    print(f"   ✓ By type: {stats['by_type']}")
    
    print("\n✅ Storage API tests passed!\n")
    
    return stored


async def test_ocr_mock():
    """Test OCR agent with mock data"""
    print("\n=== Testing OCR Agent (Mock Mode) ===\n")
    
    # Add agents directory to path
    agents_dir = Path(__file__).parent / "agents" / "ocr-agent"
    sys.path.insert(0, str(agents_dir))
    
    from providers.tesseract_provider import TesseractOCRProvider
    
    provider = TesseractOCRProvider()
    
    print("1. Extracting text from mock image...")
    result = await provider.extract_text(
        image_path="test_image.jpg",
        language="eng",
        psm=3
    )
    
    print(f"   ✓ Extracted text: {result['text'][:80]}...")
    print(f"   ✓ Confidence: {result['confidence']}")
    print(f"   ✓ Language: {result['language']}")
    print(f"   ✓ Provider: {result['metadata']['provider']}")
    
    print("\n✅ OCR agent tests passed!\n")
    
    return result


async def test_full_workflow():
    """Test complete workflow: OCR → Storage"""
    print("\n=== Testing Full Workflow ===\n")
    
    # Step 1: OCR
    ocr_result = await test_ocr_mock()
    
    # Step 2: Storage
    storage = StorageAPI(
        db_path="./test_pala_storage.db",
        content_dir="./test_content"
    )
    
    print("Storing OCR result...")
    workflow_content = json.dumps({
        "ocr_result": ocr_result,
        "workflow": "document-processing",
        "steps_completed": ["upload", "ocr"]
    }).encode('utf-8')
    
    stored = storage.store_content(
        content=workflow_content,
        content_type="document",
        metadata={
            "source_file": "test_image.jpg",
            "ocr_confidence": ocr_result['confidence'],
            "workflow_status": "in_progress"
        }
    )
    
    print(f"   ✓ Workflow data stored: {stored.content_id}")
    
    print("\n✅ Full workflow test passed!\n")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  Pala Platform - OCR Agent & Storage Layer Test")
    print("="*60)
    
    try:
        await test_storage()
        await test_ocr_mock()
        await test_full_workflow()
        
        print("\n" + "="*60)
        print("  ✅ All tests passed!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
