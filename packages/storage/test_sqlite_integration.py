#!/usr/bin/env python3
"""
Integration test: SQLite backend with StorageAPI

Verifies SQLite backend works seamlessly with the unified StorageAPI.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Add packages directory to path
packages_dir = Path(__file__).parent.parent
sys.path.insert(0, str(packages_dir))

from storage.api import StorageAPI


async def test_storage_api_with_sqlite():
    """Test StorageAPI with SQLite backend"""
    print("\n=== Testing StorageAPI with SQLite Backend ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageAPI(
            db_path=f"{tmpdir}/metadata.db",
            backends_config={
                'sqlite': {
                    'enabled': True,
                    'default': True,
                    'config': {'db_path': f"{tmpdir}/content.db"}
                }
            }
        )
        
        # Test store
        print("1. Storing document...")
        doc_data = json.dumps({
            "text": "Historical letter content",
            "metadata": {"date": "1892-03-15", "author": "John Smith"}
        }).encode('utf-8')
        
        stored = await storage.store_content(
            content=doc_data,
            content_type='document',
            metadata={
                'source': 'letter.jpg',
                'workflow': 'document-processing',
                'language': 'en'
            }
        )
        print(f"   ✓ Stored: {stored.content_id}")
        print(f"   ✓ Backend: {stored.backend_name}")
        print(f"   ✓ Size: {stored.file_size} bytes")
        
        # Test deduplication
        print("2. Testing deduplication...")
        stored2 = await storage.store_content(
            content=doc_data,
            content_type='document',
            metadata={'source': 'duplicate.jpg'}
        )
        assert stored.content_id == stored2.content_id
        print(f"   ✓ Duplicate detected: {stored.content_id == stored2.content_id}")
        
        # Test read
        print("3. Reading content...")
        content = await storage.read_content(stored.content_id)
        data = json.loads(content)
        print(f"   ✓ Retrieved text: {data['text'][:30]}...")
        
        # Test metadata retrieval
        print("4. Getting metadata...")
        meta = storage.get_content_metadata(stored.content_id)
        print(f"   ✓ Content type: {meta.content_type}")
        print(f"   ✓ Backend: {meta.backend_name}")
        print(f"   ✓ Version: {meta.version}")
        
        # Test versioning
        print("5. Updating metadata...")
        storage.update_metadata(
            content_id=stored.content_id,
            metadata={
                'status': 'ocr_complete',
                'ocr_confidence': 0.95,
                'extracted_text': data['text']
            },
            updated_by='ocr-agent'
        )
        
        updated = storage.get_content_metadata(stored.content_id)
        print(f"   ✓ New version: {updated.version}")
        print(f"   ✓ Status: {updated.metadata.get('status')}")
        
        # Test listing
        print("6. Listing content...")
        items = storage.list_content(content_type='document')
        print(f"   ✓ Found {len(items)} documents")
        
        # Test statistics
        print("7. Getting statistics...")
        stats = await storage.get_stats()
        print(f"   ✓ Total items: {stats['total_count']}")
        print(f"   ✓ Total size: {stats['total_size']} bytes")
        print(f"   ✓ Backend health: {stats['backends']['sqlite-primary']['healthy']}")
        
        # Test deletion
        print("8. Deleting content...")
        deleted = await storage.delete_content(stored.content_id)
        print(f"   ✓ Deleted: {deleted}")
        
        remaining = storage.list_content()
        print(f"   ✓ Remaining items: {len(remaining)}")
        
        print("\n✅ StorageAPI with SQLite backend test passed!\n")


async def test_storage_api_multi_backend_with_sqlite():
    """Test StorageAPI with SQLite as one of multiple backends"""
    print("\n=== Testing StorageAPI with Multiple Backends (SQLite + Local) ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageAPI(
            db_path=f"{tmpdir}/metadata.db",
            backends_config={
                'sqlite': {
                    'enabled': True,
                    'default': True,
                    'config': {'db_path': f"{tmpdir}/sqlite.db"}
                },
                'local': {
                    'enabled': True,
                    'default': False,
                    'config': {'base_path': f"{tmpdir}/filesystem"}
                }
            }
        )
        
        # Store in default (SQLite)
        print("1. Storing in SQLite (default)...")
        stored1 = await storage.store_content(
            content=b'Content for SQLite',
            content_type='document'
        )
        print(f"   ✓ Backend: {stored1.backend_name}")
        
        # Store in local
        print("2. Storing in Local backend...")
        stored2 = await storage.store_content(
            content=b'Content for Local',
            content_type='document',
            backend_name='local-primary'
        )
        print(f"   ✓ Backend: {stored2.backend_name}")
        
        # Get stats from both
        print("3. Getting statistics...")
        stats = await storage.get_stats()
        print(f"   ✓ Total items: {stats['total_count']}")
        print(f"   Backends:")
        for backend_name, backend_info in stats['backends'].items():
            print(f"     - {backend_name}: {backend_info['stats'].get('total_count', 0)} items")
        
        print("\n✅ Multi-backend test passed!\n")


async def test_workflow_with_sqlite():
    """Test complete document processing workflow with SQLite"""
    print("\n=== Testing Document Workflow with SQLite ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageAPI(
            db_path=f"{tmpdir}/metadata.db",
            backends_config={
                'sqlite': {
                    'enabled': True,
                    'default': True,
                    'config': {'db_path': f"{tmpdir}/content.db"}
                }
            }
        )
        
        # Step 1: Upload
        print("1. Upload...")
        stored = await storage.store_content(
            content=b"Scanned letter",
            content_type='document',
            metadata={
                'step': 'upload',
                'source': 'letter_1892.jpg'
            }
        )
        print(f"   ✓ ID: {stored.content_id}")
        
        # Step 2: OCR
        print("2. OCR Processing...")
        storage.update_metadata(
            stored.content_id,
            {'step': 'ocr', 'text': 'Letter content...', 'confidence': 0.92},
            updated_by='ocr-agent'
        )
        print(f"   ✓ Version: 2")
        
        # Step 3: Metadata
        print("3. Metadata Extraction...")
        storage.update_metadata(
            stored.content_id,
            {'step': 'metadata', 'date': '1892-03-15', 'author': 'John Smith'},
            updated_by='metadata-agent'
        )
        print(f"   ✓ Version: 3")
        
        # Step 4: Review
        print("4. Human Review...")
        storage.update_metadata(
            stored.content_id,
            {'step': 'review', 'status': 'approved'},
            updated_by='curator'
        )
        print(f"   ✓ Version: 4")
        
        # Step 5: Sign
        print("5. Digital Signing...")
        storage.update_metadata(
            stored.content_id,
            {'step': 'sign', 'signature': 'SHA256:abc123...'},
            updated_by='signing-agent'
        )
        print(f"   ✓ Version: 5")
        
        # Final check
        final = storage.get_content_metadata(stored.content_id)
        print(f"\n   Final State:")
        print(f"   ✓ Total versions: {final.version}")
        print(f"   ✓ Final step: {final.metadata.get('step')}")
        print(f"   ✓ Status: {final.metadata.get('status')}")
        
        print("\n✅ Document workflow test passed!\n")


async def main():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("  StorageAPI + SQLite Backend Integration Tests")
    print("="*60)
    
    try:
        await test_storage_api_with_sqlite()
        await test_storage_api_multi_backend_with_sqlite()
        await test_workflow_with_sqlite()
        
        print("\n" + "="*60)
        print("  ✅ All integration tests passed!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
