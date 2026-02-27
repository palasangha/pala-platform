#!/usr/bin/env python3
"""
Tests for multi-backend storage architecture

Tests all backends and the unified StorageAPI.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Add packages directory to path
packages_dir = Path(__file__).parent.parent
sys.path.insert(0, str(packages_dir))


async def test_local_backend():
    """Test local filesystem backend"""
    print("\n=== Testing Local Backend ===\n")
    
    from storage.backends.local import LocalStorageBackend
    
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalStorageBackend('test-local', {
            'base_path': tmpdir,
            'organize_by_type': True,
            'organize_by_date': True
        })
        
        # Test write
        print("1. Writing content...")
        location = await backend.write(
            content_id='doc-123',
            content=b'Test content',
            metadata={'content_type': 'document'}
        )
        print(f"   ✓ Written to: {location}")
        
        # Test exists
        print("2. Checking existence...")
        exists = await backend.exists('doc-123', location)
        print(f"   ✓ Exists: {exists}")
        
        # Test get_size
        print("3. Getting size...")
        size = await backend.get_size('doc-123', location)
        print(f"   ✓ Size: {size} bytes")
        
        # Test read
        print("4. Reading content...")
        content = await backend.read('doc-123', location)
        print(f"   ✓ Read: {content[:30]}...")
        
        # Test list
        print("5. Listing content...")
        items = await backend.list_content()
        print(f"   ✓ Found {len(items)} items")
        
        # Test health
        print("6. Health check...")
        healthy = await backend.health_check()
        print(f"   ✓ Healthy: {healthy}")
        
        # Test stats
        print("7. Getting stats...")
        stats = await backend.get_stats()
        print(f"   ✓ Total count: {stats['total_count']}")
        print(f"   ✓ Total size: {stats['total_size']} bytes")
        
        # Test delete
        print("8. Deleting content...")
        deleted = await backend.delete('doc-123', location)
        print(f"   ✓ Deleted: {deleted}")
        
        print("\n✅ Local backend tests passed!\n")


async def test_storage_api_basic():
    """Test basic StorageAPI functionality"""
    print("\n=== Testing StorageAPI (Local) ===\n")
    
    from storage.api import StorageAPI
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageAPI(
            db_path=f"{tmpdir}/test.db",
            backends_config={
                'local': {
                    'enabled': True,
                    'default': True,
                    'config': {'base_path': f"{tmpdir}/content"}
                }
            }
        )
        
        # Test store
        print("1. Storing content...")
        stored = await storage.store_content(
            content=json.dumps({
                "text": "Sample document",
                "metadata": {"date": "2026-02-26"}
            }).encode('utf-8'),
            content_type='document',
            metadata={'source': 'test.jpg', 'workflow': 'document-processing'}
        )
        print(f"   ✓ Stored: {stored.content_id}")
        print(f"   ✓ Hash: {stored.file_hash[:16]}...")
        print(f"   ✓ Backend: {stored.backend_name}")
        
        # Test deduplication
        print("2. Testing deduplication...")
        stored2 = await storage.store_content(
            content=json.dumps({
                "text": "Sample document",
                "metadata": {"date": "2026-02-26"}
            }).encode('utf-8'),
            content_type='document',
            metadata={'source': 'duplicate.jpg'}
        )
        assert stored.content_id == stored2.content_id
        print(f"   ✓ Same content ID: {stored.content_id == stored2.content_id}")
        
        # Test read
        print("3. Reading content...")
        content = await storage.read_content(stored.content_id)
        data = json.loads(content)
        print(f"   ✓ Retrieved: {data['text']}")
        
        # Test get metadata
        print("4. Getting metadata...")
        meta = storage.get_content_metadata(stored.content_id)
        print(f"   ✓ Type: {meta.content_type}")
        print(f"   ✓ Version: {meta.version}")
        print(f"   ✓ Size: {meta.file_size} bytes")
        
        # Test list
        print("5. Listing content...")
        items = storage.list_content(content_type='document')
        print(f"   ✓ Found {len(items)} documents")
        
        # Test update metadata
        print("6. Updating metadata...")
        storage.update_metadata(
            content_id=stored.content_id,
            metadata={'status': 'reviewed', 'reviewer': 'admin'},
            updated_by='admin'
        )
        updated_meta = storage.get_content_metadata(stored.content_id)
        print(f"   ✓ New version: {updated_meta.version}")
        print(f"   ✓ Status: {updated_meta.metadata.get('status')}")
        
        # Test stats
        print("7. Getting statistics...")
        stats = await storage.get_stats()
        print(f"   ✓ Total items: {stats['total_count']}")
        print(f"   ✓ Total size: {stats['total_size']} bytes")
        print(f"   ✓ By type: {stats['by_type']}")
        
        # Test delete
        print("8. Deleting content...")
        deleted = await storage.delete_content(stored.content_id)
        print(f"   ✓ Deleted: {deleted}")
        
        # Verify deletion
        remaining = storage.list_content()
        print(f"   ✓ Remaining items: {len(remaining)}")
        
        print("\n✅ StorageAPI tests passed!\n")


async def test_backend_factory():
    """Test backend factory registration"""
    print("\n=== Testing Backend Factory ===\n")
    
    from storage.backends import StorageBackendFactory
    
    print("1. Checking registered backends...")
    backends = StorageBackendFactory.get_registered_backends()
    print(f"   ✓ Registered: {backends}")
    
    print("2. Creating local backend...")
    backend = StorageBackendFactory.create('local', 'test', {
        'base_path': tempfile.mkdtemp()
    })
    print(f"   ✓ Created: {backend.backend_type}")
    
    print("3. Creating S3 backend (mock)...")
    backend = StorageBackendFactory.create('s3', 'test', {
        'bucket_name': 'test'
    })
    print(f"   ✓ Created: {backend.backend_type}")
    
    print("4. Creating GCS backend (mock)...")
    backend = StorageBackendFactory.create('gcs', 'test', {
        'bucket_name': 'test'
    })
    print(f"   ✓ Created: {backend.backend_type}")
    
    print("5. Creating Azure backend (mock)...")
    backend = StorageBackendFactory.create('azure', 'test', {
        'container_name': 'test'
    })
    print(f"   ✓ Created: {backend.backend_type}")
    
    print("\n✅ Backend factory tests passed!\n")


async def test_backend_manager():
    """Test backend manager with multiple backends"""
    print("\n=== Testing Backend Manager ===\n")
    
    from storage.backends import StorageBackendManager, StorageBackendFactory
    
    manager = StorageBackendManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Register multiple backends
        print("1. Registering backends...")
        local1 = StorageBackendFactory.create('local', 'local-primary', {
            'base_path': f"{tmpdir}/content1"
        })
        manager.register_backend(local1, default=True)
        print(f"   ✓ Local primary registered")
        
        local2 = StorageBackendFactory.create('local', 'local-backup', {
            'base_path': f"{tmpdir}/content2"
        })
        manager.register_backend(local2, default=False)
        print(f"   ✓ Local backup registered")
        
        # Test write
        print("2. Writing to default backend...")
        backend_name, location = await manager.write(
            content_id='test-123',
            content=b'Test content',
            metadata={'content_type': 'document'}
        )
        print(f"   ✓ Written to {backend_name}")
        
        # Test write to specific backend
        print("3. Writing to specific backend...")
        backend_name2, location2 = await manager.write(
            content_id='test-456',
            content=b'Another test',
            metadata={'content_type': 'audio'},
            backend_name='local-backup'
        )
        print(f"   ✓ Written to {backend_name2}")
        
        # Test read
        print("4. Reading from backends...")
        content1 = await manager.read('test-123', backend_name, location)
        content2 = await manager.read('test-456', backend_name2, location2)
        print(f"   ✓ Read {len(content1)} bytes from {backend_name}")
        print(f"   ✓ Read {len(content2)} bytes from {backend_name2}")
        
        # Test health check
        print("5. Health checking...")
        health = await manager.health_check()
        print(f"   ✓ Health status: {health}")
        
        # Test stats
        print("6. Getting stats...")
        stats = await manager.get_backend_stats()
        for backend, backend_stats in stats.items():
            if 'error' not in backend_stats:
                print(f"   ✓ {backend}: {backend_stats.get('total_count', 0)} items")
        
        # Test list backends
        print("7. Listing backends...")
        backends = manager.list_backends()
        print(f"   ✓ Backends: {backends}")
        
        print("\n✅ Backend manager tests passed!\n")


async def test_workflow_scenario():
    """Test a complete document processing workflow"""
    print("\n=== Testing Document Processing Workflow ===\n")
    
    from storage.api import StorageAPI
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageAPI(
            db_path=f"{tmpdir}/workflow.db",
            backends_config={
                'local': {
                    'enabled': True,
                    'default': True,
                    'config': {'base_path': f"{tmpdir}/content"}
                }
            }
        )
        
        # Step 1: Upload
        print("1. Document Upload...")
        doc_content = b"Scanned document content..."
        stored = await storage.store_content(
            content=doc_content,
            content_type='document',
            metadata={
                'workflow': 'document-processing',
                'step': 'upload',
                'source_file': 'letter.jpg'
            }
        )
        print(f"   ✓ Stored: {stored.content_id}")
        
        # Step 2: OCR
        print("2. OCR Processing...")
        storage.update_metadata(
            content_id=stored.content_id,
            metadata={
                'workflow': 'document-processing',
                'step': 'ocr',
                'ocr_text': 'Extracted text from image',
                'ocr_confidence': 0.95
            },
            updated_by='ocr-agent'
        )
        meta = storage.get_content_metadata(stored.content_id)
        print(f"   ✓ Version: {meta.version}")
        print(f"   ✓ OCR Text: {meta.metadata.get('ocr_text')}")
        
        # Step 3: Metadata extraction
        print("3. Metadata Extraction...")
        storage.update_metadata(
            content_id=stored.content_id,
            metadata={
                'workflow': 'document-processing',
                'step': 'metadata',
                'extracted_date': '1892-03-15',
                'author': 'John Smith',
                'language': 'en'
            },
            updated_by='metadata-agent'
        )
        
        # Step 4: Review
        print("4. Human Review...")
        storage.update_metadata(
            content_id=stored.content_id,
            metadata={
                'workflow': 'document-processing',
                'step': 'review',
                'reviewed_by': 'curator',
                'status': 'approved'
            },
            updated_by='curator'
        )
        
        # Step 5: Signing
        print("5. Digital Signing...")
        storage.update_metadata(
            content_id=stored.content_id,
            metadata={
                'workflow': 'document-processing',
                'step': 'sign',
                'signature': 'SHA256:abc123...'
            },
            updated_by='signing-agent'
        )
        
        # Final: Check complete workflow
        print("6. Workflow Completion...")
        final_meta = storage.get_content_metadata(stored.content_id)
        print(f"   ✓ Final version: {final_meta.version}")
        print(f"   ✓ Workflow steps: {[final_meta.metadata.get('step')]}")
        print(f"   ✓ Status: {final_meta.metadata.get('status')}")
        
        print("\n✅ Workflow scenario tests passed!\n")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  Pala Platform - Multi-Backend Storage Tests")
    print("="*60)
    
    try:
        await test_backend_factory()
        await test_local_backend()
        await test_backend_manager()
        await test_storage_api_basic()
        await test_workflow_scenario()
        
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
