import json
import pytest


def test_get_available_models(client):
    """Test listing available models."""
    response = client.get('/api/models')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'models' in data
    assert isinstance(data['models'], list)
    # Should have at least the default providers
    assert len(data['models']) > 0
    # Each model should have required fields
    for model in data['models']:
        assert 'id' in model
        assert 'name' in model
        assert 'provider' in model


def test_discover_ollama_models(client):
    """Test Ollama model discovery endpoint."""
    response = client.get('/api/models/ollama/discover')
    assert response.status_code == 200
    data = json.loads(response.data)
    # Response uses 'ollama_models' key
    assert 'ollama_models' in data
    assert isinstance(data['ollama_models'], list)


def test_test_model_endpoint(client):
    """Test model connectivity test endpoint."""
    response = client.post(
        '/api/models/test',
        data=json.dumps({'model_id': 'claude-sonnet-4-20250514'}),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'model_id' in data
    assert 'status' in data


def test_test_model_missing_id(client):
    """Test model test endpoint with missing model_id."""
    response = client.post(
        '/api/models/test',
        data=json.dumps({}),
        content_type='application/json'
    )
    # Should handle gracefully
    assert response.status_code in [200, 400]
