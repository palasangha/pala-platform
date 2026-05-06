import tempfile

import pytest

from metadata_utils import deep_merge_dict, extract_metadata_health
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


def test_deep_merge_dict_preserves_existing_nested_values():
    existing = {'content': {'language': 'en', 'summary': 'Old'}, 'topics': ['one']}
    patch = {'content': {'summary': 'New'}, 'topics': ['two']}

    merged = deep_merge_dict(existing, patch)

    assert merged['content']['language'] == 'en'
    assert merged['content']['summary'] == 'New'
    assert merged['topics'] == ['two']


@pytest.mark.asyncio
async def test_update_document_metadata_merges_and_bumps_version():
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
