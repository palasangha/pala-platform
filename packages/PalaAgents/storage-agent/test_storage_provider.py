import asyncio
import os
import tempfile
import pytest
from storage_provider import Document
from sqlite_provider import SQLiteProvider

@pytest.mark.asyncio
async def test_store_and_retrieve_document_with_location_and_provider():
    # Use a temporary SQLite DB
    with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
        provider = SQLiteProvider(db_path=tmp.name)
        doc_type = 'test_type'
        original_file = '/tmp/testfile.txt'
        file_format = 'txt'
        processed_data = {'text': 'hello'}
        metadata = {'lang': 'en'}
        app_data = {'project': 'demo'}
        created_by = 'pytest'
        file_hash = 'abc123hash'

        # Store document
        doc, duplicate = await provider.store_document(
            type=doc_type,
            original_file=original_file,
            file_format=file_format,
            processed_data=processed_data,
            metadata=metadata,
            app_data=app_data,
            created_by=created_by,
            file_hash=file_hash
        )
        assert not duplicate
        assert doc.storage_location == original_file
        assert doc.provider_id == 'sqlite'

        # Retrieve document
        retrieved = await provider.retrieve_document(doc.id)
        assert retrieved is not None
        assert retrieved.storage_location == original_file
        assert retrieved.provider_id == 'sqlite'

        # List documents
        result = await provider.list_documents()
        assert result['count'] == 1
        doc_listed = result['documents'][0]
        assert doc_listed.storage_location == original_file
        assert doc_listed.provider_id == 'sqlite'

        # Store duplicate
        doc2, duplicate2 = await provider.store_document(
            type=doc_type,
            original_file=original_file,
            file_format=file_format,
            processed_data=processed_data,
            metadata=metadata,
            app_data=app_data,
            created_by=created_by,
            file_hash=file_hash
        )
        assert duplicate2
        assert doc2.storage_location == original_file
        assert doc2.provider_id == 'sqlite'
