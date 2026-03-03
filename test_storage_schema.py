#!/usr/bin/env python3
"""
Test script to verify the new unified schema is working correctly
"""
import sys
import json
from pathlib import Path

# Add storage agent to path
sys.path.insert(0, str(Path(__file__).parent / 'packages/agents/storage-agent'))

from metadata_db import MetadataDB

def test_schema():
    """Test the unified schema"""
    print("🧪 Testing Unified Schema...\n")
    
    # Initialize DB
    db_path = Path(__file__).parent / 'packages/agents/storage-agent/data/test_metadata.db'
    db = MetadataDB(str(db_path))
    print(f"✅ Database initialized at {db_path}")
    
    # Test insert with new schema
    print("\n📝 Inserting document with unified schema...")
    result = db.insert(
        document_id="doc-test-001",
        type="ocr",
        file_hash="abc123def456",
        original_file="test.pdf",
        file_format="pdf",
        file_size=1024,
        processed_data={"text": "Test content", "confidence": 0.95},
        metadata={"language": "en"},
        app_data={"project": "test"},
        created_by="test-script",
    )
    print(f"✅ Document inserted: {result.document_id}")
    print(f"   Type: {result.type}")
    print(f"   Created by: {result.created_by}")
    print(f"   Created at: {result.created_at}")
    
    # Test retrieve
    print("\n🔍 Retrieving document...")
    retrieved = db.get_metadata("doc-test-001")
    if retrieved:
        print(f"✅ Document retrieved: {retrieved.document_id}")
        print(f"   Type: {retrieved.type}")
        print(f"   Original file: {retrieved.original_file}")
        print(f"   Processed data: {retrieved.processed_data}")
    else:
        print("❌ Document not found!")
        return False
    
    # Test list
    print("\n📋 Listing documents...")
    docs = db.list_all(limit=100, offset=0)
    print(f"✅ Found {len(docs)} documents")
    for doc in docs:
        print(f"   - {doc.document_id}: {doc.type} ({doc.created_by})")
    
    # Test filter by type
    print("\n🔎 Filtering by type='ocr'...")
    ocr_docs = db.list_all(type="ocr", limit=100, offset=0)
    print(f"✅ Found {len(ocr_docs)} OCR documents")
    
    # Test filter by created_by
    print("\n🔎 Filtering by created_by='test-script'...")
    test_docs = db.list_all(created_by="test-script", limit=100, offset=0)
    print(f"✅ Found {len(test_docs)} documents created by test-script")
    
    # Cleanup
    db_path.unlink(missing_ok=True)
    print("\n✅ Test completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = test_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
