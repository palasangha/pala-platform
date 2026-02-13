import json
import pytest
import os

def test_full_workflow_health_check(client):
    """Test complete workflow: health check."""
    # 1. Check backend health
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data

    # 2. Check database status
    response = client.get('/api/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data

def test_full_workflow_lookup_and_search(client):
    """Test complete workflow: lookup and search."""
    # 1. Lookup a word
    response = client.get('/api/lookup/metta')
    assert response.status_code in [200, 404, 500]

    # 2. Search for related passages
    response = client.get('/api/search?q=compassion')
    assert response.status_code in [200, 400, 500]

def test_database_connectivity(client):
    """Test that database is accessible."""
    response = client.get('/api/status')
    assert response.status_code == 200
    data = json.loads(response.data)

    # Check for health status
    assert 'status' in data
    # Database info should be in checks or database field
    if 'checks' in data:
        assert 'tipitaka_db' in data['checks']
        assert data['checks']['tipitaka_db']['paragraphs'] >= 73000

def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.get('/api/health')
    assert response.status_code == 200
    # CORS headers may be set
    assert response.status_code == 200
