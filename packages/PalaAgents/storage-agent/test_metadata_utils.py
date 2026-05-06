import asyncio
import tempfile
from types import SimpleNamespace

from metadata_utils import deep_merge_dict, extract_metadata_health
import main as storage_main
from sqlite_provider import SQLiteProvider


def test_extract_metadata_health_equal_weight_scoring():
    metadata = {
        'summary': 'A short summary',
        'document_date': '1969-09-29',
        'language': 'en',
        'people': ['Dr. Ashok Mehta'],
        'places': ['New Delhi'],
        'topics': ['Vietnam Negotiations'],
        'organizations': ['Ministry of External Affairs'],
    }

    health = extract_metadata_health(metadata, {'text': 'ignored'})

    assert health['score'] == 100.0
    assert health['missing_fields'] == []
    assert set(health['present_fields']) == {
        'summary',
        'document_date',
        'language',
        'people',
        'places',
        'topics',
        'organizations',
    }


def test_build_metadata_health_handles_nested_metadata_and_logs(caplog):
    nested_metadata = {
        'pala_metadata': {
            'content': {
                'summary': {'text': 'A complete nested summary'},
                'language': 'en',
                'topics': ['history'],
            },
            'parties': {
                'people': [{'name': 'Dr. Ashok Mehta'}],
                'organizations': [{'name': 'Ministry of External Affairs'}],
            },
            'places': {
                'locations': [{'name': 'New Delhi'}],
            },
            'document': {
                'date': {'value': '1969-09-29'},
            },
        }
    }

    fake_doc = SimpleNamespace(id='doc-1', metadata=nested_metadata, processed_data={})

    with caplog.at_level('INFO'):
        health = storage_main.build_metadata_health(fake_doc)

    assert health['score'] == 100.0
    assert health['missing_fields'] == []
    assert any('[METADATA-SCORE]' in record.message for record in caplog.records)


def test_deep_merge_dict_preserves_existing_nested_values():
    existing = {'content': {'language': 'en', 'summary': 'Old'}, 'topics': ['one']}
    patch = {'content': {'summary': 'New'}, 'topics': ['two']}

    merged = deep_merge_dict(existing, patch)

    assert merged['content']['language'] == 'en'
    assert merged['content']['summary'] == 'New'
    assert merged['topics'] == ['two']


def test_update_document_metadata_merges_and_bumps_version():
    async def run_test():
        with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
            provider = SQLiteProvider(db_path=tmp.name)
            doc, duplicate = await provider.store_document(
                type='ocr',
                original_file='doc.pdf',
                file_format='pdf',
                processed_data={'text': 'hello'},
                metadata={'language': 'en'},
                app_data={},
                created_by='pytest',
            )
            assert not duplicate
            assert doc.version == 1

            updated = await provider.update_document_metadata(
                document_id=doc.id,
                metadata={'summary': 'Added summary'},
                updated_by='pytest',
                replace=False,
            )

            assert updated is not None
            assert updated.version == 2
            assert updated.metadata['language'] == 'en'
            assert updated.metadata['summary'] == 'Added summary'

            health = extract_metadata_health(updated.metadata, updated.processed_data)
            assert health['score'] >= 28.0

    asyncio.run(run_test())


def test_update_document_metadata_refreshes_search_app_data(monkeypatch):
    async def run_test():
        with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
            provider = SQLiteProvider(db_path=tmp.name)
            doc, duplicate = await provider.store_document(
                type='ocr',
                original_file='refresh.pdf',
                file_format='pdf',
                processed_data={'text': 'hello world'},
                metadata={'language': 'en'},
                app_data={'embedding_generated': False},
                created_by='pytest',
            )
            assert not duplicate

            monkeypatch.setattr(storage_main, 'provider', provider)
            monkeypatch.setattr(
                storage_main,
                'embedding_model',
                SimpleNamespace(encode=lambda text, convert_to_tensor=False: [0.1, 0.2, 0.3]),
            )

            result = await storage_main.tool_update_document_metadata(
                {
                    'document_id': doc.id,
                    'metadata': {'summary': 'Refreshed summary'},
                    'updated_by': 'pytest',
                }
            )

            assert result['success'] is True
            assert result['search_index_refreshed'] is True

            refreshed = await provider.retrieve_document(doc.id)
            assert refreshed is not None
            assert refreshed.app_data['embedding_generated'] is True
            assert refreshed.app_data['embedding_vector'] == [0.1, 0.2, 0.3]
            assert 'Refreshed summary' in refreshed.app_data['searchable_text']

    asyncio.run(run_test())


def test_tool_list_documents_sorts_and_filters_by_metadata_score(monkeypatch):
    async def run_test():
        with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
            provider = SQLiteProvider(db_path=tmp.name)

            partial_doc, duplicate = await provider.store_document(
                type='ocr',
                original_file='partial.pdf',
                file_format='pdf',
                processed_data={'text': 'partial text'},
                metadata={'summary': 'Only summary provided'},
                app_data={},
                created_by='pytest',
            )
            assert not duplicate

            complete_doc, duplicate = await provider.store_document(
                type='ocr',
                original_file='complete.pdf',
                file_format='pdf',
                processed_data={'text': 'complete text'},
                metadata={
                    'pala_metadata': {
                        'content': {
                            'summary': {'text': 'A complete nested summary'},
                            'language': 'en',
                            'topics': ['history'],
                        },
                        'parties': {
                            'people': [{'name': 'Dr. Ashok Mehta'}],
                            'organizations': [{'name': 'Ministry of External Affairs'}],
                        },
                        'places': {
                            'locations': [{'name': 'New Delhi'}],
                        },
                        'document': {
                            'date': {'value': '1969-09-29'},
                        },
                    }
                },
                app_data={},
                created_by='pytest',
            )
            assert not duplicate

            monkeypatch.setattr(storage_main, 'provider', provider)

            sorted_result = await storage_main.tool_list_documents(
                {
                    'limit': 10,
                    'offset': 0,
                    'sort_by': 'metadata_score',
                }
            )

            assert sorted_result['documents'][0]['document_id'] == partial_doc.id
            assert sorted_result['documents'][-1]['document_id'] == complete_doc.id
            assert sorted_result['documents'][0]['metadata_score'] <= sorted_result['documents'][-1]['metadata_score']

            filtered_result = await storage_main.tool_list_documents(
                {
                    'limit': 10,
                    'offset': 0,
                    'score_lt': 100,
                }
            )

            assert all(doc['metadata_score'] < 100 for doc in filtered_result['documents'])
            assert all(doc['document_id'] != complete_doc.id for doc in filtered_result['documents'])

    asyncio.run(run_test())
