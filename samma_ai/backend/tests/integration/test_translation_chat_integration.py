"""
Integration tests for Translation Service with Chat Route

Tests the complete pipeline:
Chat Request → Tipitaka Search → Passage Enrichment → LLM Response
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@patch('app.services.translation_service.requests.get')
@patch('app.services.translation_service.requests.post')
@patch('app.services.tipitaka_service.TipitakaService.search_relevant_passages')
@patch('app.services.model_router_service.ModelRouterService.generate_dhamma_response')
def test_chat_with_translation_enrichment(
    mock_dhamma,
    mock_search,
    mock_post,
    mock_get,
    client
):
    """Test chat route enriches passages with translations."""
    # Mock Tipitaka search
    mock_search.return_value = [
        {
            'id': '1',
            'pali_text': 'samadhi',
            'english_text': None,  # Missing translation
            'xml_source_file': 'test.xml',
            'paragraph_number': 1,
        }
    ]

    # Mock Ollama availability
    mock_get.return_value.status_code = 200

    # Mock Deepseek translation
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        'response': 'concentration, meditative absorption'
    }

    # Mock LLM response
    mock_dhamma.return_value = {
        'canonical_teachings': ['teaching 1'],
        'raw_response': 'response'
    }

    response = client.post('/api/chat', json={
        'message': 'What is samadhi?',
        'model_id': 'copilot'
    })

    assert response.status_code == 200
    data = response.json

    # Verify translation was enriched
    assert len(data['passages']) > 0
    passage = data['passages'][0]
    assert passage['english_text'] == 'concentration, meditative absorption'
    assert passage['translation_source'] == 'ollama'


@patch('app.services.translation_service.requests.get')
@patch('app.services.tipitaka_service.TipitakaService.search_relevant_passages')
@patch('app.services.model_router_service.ModelRouterService.generate_dhamma_response')
def test_chat_with_db_translation(
    mock_dhamma,
    mock_search,
    mock_get,
    client
):
    """Test chat route uses DB translation if available."""
    # Mock Tipitaka search with DB translation
    mock_search.return_value = [
        {
            'id': '1',
            'pali_text': 'metta',
            'english_text': 'loving-kindness',  # Already in DB
            'xml_source_file': 'test.xml',
            'paragraph_number': 1,
        }
    ]

    # Mock LLM response
    mock_dhamma.return_value = {
        'canonical_teachings': ['teaching 1'],
        'raw_response': 'response'
    }

    response = client.post('/api/chat', json={
        'message': 'What is metta?',
        'model_id': 'copilot'
    })

    assert response.status_code == 200
    data = response.json

    passage = data['passages'][0]
    assert passage['english_text'] == 'loving-kindness'
    assert passage['translation_source'] == 'db'


@patch('app.services.translation_service.requests.get')
@patch('app.services.tipitaka_service.TipitakaService.search_relevant_passages')
@patch('app.services.model_router_service.ModelRouterService.generate_dhamma_response')
def test_chat_with_translation_disabled(
    mock_dhamma,
    mock_search,
    client,
    app
):
    """Test chat works when translation service disabled."""
    # Disable translation
    app.config['OLLAMA_TRANSLATION_ENABLED'] = False
    app.extensions['translation_service'] = None

    # Mock Tipitaka search
    mock_search.return_value = [
        {
            'id': '1',
            'pali_text': 'samadhi',
            'english_text': None,
            'xml_source_file': 'test.xml',
            'paragraph_number': 1,
        }
    ]

    # Mock LLM response
    mock_dhamma.return_value = {
        'canonical_teachings': ['teaching 1'],
        'raw_response': 'response'
    }

    response = client.post('/api/chat', json={
        'message': 'What is samadhi?',
        'model_id': 'copilot'
    })

    assert response.status_code == 200
    data = response.json
    # English text should not be translated
    assert data['passages'][0].get('english_text') is None


@patch('app.services.translation_service.requests.get')
@patch('app.services.tipitaka_service.TipitakaService.search_relevant_passages')
@patch('app.services.model_router_service.ModelRouterService.generate_dhamma_response')
def test_chat_with_translation_timeout_graceful(
    mock_dhamma,
    mock_search,
    mock_get,
    client
):
    """Test chat continues gracefully if translation times out."""
    # Mock Tipitaka search
    mock_search.return_value = [
        {
            'id': '1',
            'pali_text': 'samadhi',
            'english_text': None,
            'xml_source_file': 'test.xml',
            'paragraph_number': 1,
        }
    ]

    # Mock Ollama timeout
    import requests
    mock_get.side_effect = requests.Timeout()

    # Mock LLM response
    mock_dhamma.return_value = {
        'canonical_teachings': ['teaching 1'],
        'raw_response': 'response'
    }

    response = client.post('/api/chat', json={
        'message': 'What is samadhi?',
        'model_id': 'copilot'
    })

    # Chat should still succeed despite translation failure
    assert response.status_code == 200
    data = response.json
    # Pali should be returned if translation failed
    assert data['passages'][0]['pali_text'] == 'samadhi'
