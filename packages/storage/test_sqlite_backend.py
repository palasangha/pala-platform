#!/usr/bin/env python3
"""
SQLite Backend Tests

Tests the SQLite storage backend specifically.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Add packages directory to path
packages_dir = Path(__file__).parent.parent
sys.path.insert(0, str(packages_dir))

from storage.backends.sqlite import SQLiteStorageBackend


async def test_sqlite_basic():
    """Test basic SQLite backend operations"""
    print("\n=== Testing SQLite Backend (Basic) ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteStorageBackend('test-sqlite', {
            'db_path': f"{tmpdir}/test.db",
            'enable_wal': True
        })
        
        # Test write
        print("1. Writing content...")
        location = await backend.write(
            content_id='doc-123',
            content=b'Test document content',
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
        assert content == b'Test document content'
        
        # Test delete
        print("5. Deleting content...")
        deleted = await backend.delete('doc-123', location)
        print(f"   ✓ Deleted: {deleted}")
        
        # Verify deletion
        exists_after = await backend.exists('doc-123', location)
        print(f"   ✓ Exists after delete: {exists_after}")
        assert not exists_after
        
        print("\n✅ SQLite basic tests passed!\n")


async def test_sqlite_multiple_items():
    """Test SQLite with multiple items"""
    print("\n=== Testing SQLite Backend (Multiple Items) ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteStorageBackend('test-sqlite', {
            'db_path': f"{tmpdir}/multi.db"
        })
        
        print("1. Writing multiple items...")
        items = []
        for i in range(5):
            location = await backend.write(
                content_id=f'item-{i}',
                content=f'Content {i}'.encode(),
                metadata={'content_type': 'document', 'index': i}
            )
            items.append(location)
        print(f"   ✓ Wrote {len(items)} items")
        
        print("2. Listing content...")
        all_items = await backend.list_content()
        print(f"   ✓ Found {len(all_items)} items")
        
        print("3. Getting statistics...")
        stats = await backend.get_stats()
        print(f"   ✓ Total count: {stats['total_count']}")
        print(f"   ✓ Total size: {stats['total_size']} bytes")
        print(f"   ✓ By type: {stats['by_type']}")
        
        assert stats['total_count'] == 5
        
        print("\n✅ SQLite multiple items test passed!\n")


async def test_sqlite_large_content():
    """Test SQLite with large content"""
    print("\n=== Testing SQLite Backend (Large Content) ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteStorageBackend('test-sqlite', {
            'db_path': f"{tmpdir}/large.db"
        })
        
        # Create 1MB content
        large_content = b'x' * (1024 * 1024)
        
        print("1. Writing large content (1MB)...")
        location = await backend.write(
            content_id='large-001',
            content=large_content,
            metadata={'content_type': 'document'}
        )
        print(f"   ✓ Written to: {location}")
        
        print("2. Verifying size...")
        size = await backend.get_size('large-001', location)
        print(f"   ✓ Size: {size} bytes ({size / 1024 / 1024:.2f}MB)")
        assert size == len(large_content)
        
        print("3. Reading large content back...")
        read_content = await backend.read('large-001', location)
        print(f"   ✓ Read: {len(read_content)} bytes")
        assert read_content == large_content
        
        print("4. Database info...")
        db_info = backend.get_db_info()
        print(f"   ✓ DB file size: {db_info['file_size']} bytes")
        print(f"   ✓ Page count: {db_info['page_count']}")
        print(f"   ✓ Journal mode: {db_info['journal_mode']}")
        
        print("\n✅ SQLite large content test passed!\n")


async def test_sqlite_metadata():
    """Test SQLite with complex metadata"""
    print("\n=== Testing SQLite Backend (Metadata) ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteStorageBackend('test-sqlite', {
            'db_path': f"{tmpdir}/metadata.db"
        })
        
        print("1. Storing with complex metadata...")
        metadata = {
            'content_type': 'document',
            'source': 'scan.jpg',
            'workflow': 'document-processing',
            'extracted_data': {
                'text': 'Some text',
                'date': '1892-03-15',
                'author': 'John Smith'
            }
        }
        
        location = await backend.write(
            content_id='doc-meta',
            content=b'Document with metadata',
            metadata=metadata
        )
        print(f"   ✓ Stored with metadata")
        
        print("2. Listing with prefix filter...")
        all_items = await backend.list_content(prefix='doc-')
        print(f"   ✓ Prefix search found: {len(all_items)} items")
        
        print("3. Getting stats by type...")
        stats = await backend.get_stats()
        print(f"   ✓ By type: {stats['by_type']}")
        
        print("\n✅ SQLite metadata test passed!\n")


async def test_sqlite_compaction():
    """Test SQLite compaction"""
    print("\n=== Testing SQLite Backend (Compaction) ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/compact.db"
        backend = SQLiteStorageBackend('test-sqlite', {
            'db_path': db_path
        })
        
        print("1. Adding content...")
        for i in range(10):
            await backend.write(
                content_id=f'item-{i}',
                content=b'x' * 1000,
                metadata={'content_type': 'document'}
            )
        print(f"   ✓ Added 10 items")
        
        # Get size before deletion
        info_before = backend.get_db_info()
        print(f"   ✓ DB size before: {info_before['file_size']} bytes")
        
        print("2. Deleting content...")
        for i in range(10):
            await backend.delete(f'item-{i}', f'item-{i}')
        print(f"   ✓ Deleted all items")
        
        info_after_delete = backend.get_db_info()
        print(f"   ✓ DB size after delete: {info_after_delete['file_size']} bytes")
        
        print("3. Compacting database...")
        result = await backend.compact()
        print(f"   ✓ Space freed: {result['space_freed']} bytes")
        
        info_after_compact = backend.get_db_info()
        print(f"   ✓ DB size after compact: {info_after_compact['file_size']} bytes")
        
        print("\n✅ SQLite compaction test passed!\n")


async def test_sqlite_concurrent_writes():
    """Test SQLite with multiple concurrent writes"""
    print("\n=== Testing SQLite Backend (Concurrent Writes) ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteStorageBackend('test-sqlite', {
            'db_path': f"{tmpdir}/concurrent.db",
            'enable_wal': True  # WAL mode for better concurrency
        })
        
        print("1. Concurrent writes...")
        
        async def write_item(i):
            await backend.write(
                content_id=f'concurrent-{i}',
                content=f'Content {i}'.encode(),
                metadata={'content_type': 'document', 'index': i}
            )
        
        # Write 20 items concurrently
        await asyncio.gather(*[write_item(i) for i in range(20)])
        print(f"   ✓ Wrote 20 items concurrently")
        
        print("2. Verifying all items...")
        items = await backend.list_content()
        print(f"   ✓ Total items: {len(items)}")
        assert len(items) == 20
        
        print("3. Getting stats...")
        stats = await backend.get_stats()
        print(f"   ✓ Total count: {stats['total_count']}")
        print(f"   ✓ Journal mode: {stats['db_path']}")
        
        print("\n✅ SQLite concurrent writes test passed!\n")


async def test_sqlite_health_check():
    """Test SQLite health check"""
    print("\n=== Testing SQLite Backend (Health Check) ===\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SQLiteStorageBackend('test-sqlite', {
            'db_path': f"{tmpdir}/health.db"
        })
        
        print("1. Health check (before content)...")
        healthy = await backend.health_check()
        print(f"   ✓ Healthy: {healthy}")
        assert healthy
        
        print("2. Adding content...")
        await backend.write(
            content_id='health-test',
            content=b'Test',
            metadata={'content_type': 'document'}
        )
        print(f"   ✓ Content added")
        
        print("3. Health check (after content)...")
        healthy = await backend.health_check()
        print(f"   ✓ Healthy: {healthy}")
        assert healthy
        
        print("\n✅ SQLite health check test passed!\n")


async def main():
    """Run all SQLite tests"""
    print("\n" + "="*60)
    print("  Pala Platform - SQLite Backend Tests")
    print("="*60)
    
    try:
        await test_sqlite_basic()
        await test_sqlite_multiple_items()
        await test_sqlite_large_content()
        await test_sqlite_metadata()
        await test_sqlite_concurrent_writes()
        await test_sqlite_health_check()
        await test_sqlite_compaction()
        
        print("\n" + "="*60)
        print("  ✅ All SQLite backend tests passed!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
