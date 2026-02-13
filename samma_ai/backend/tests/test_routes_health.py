import json
import pytest

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert data['status'] == 'healthy'
    assert 'service' in data

def test_status_endpoint(client):
    """Test status endpoint."""
    response = client.get('/api/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    # Check for health information
    assert 'service' in data or 'checks' in data
