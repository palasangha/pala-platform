import pytest
import os
from app.services.claude_service import ClaudeService

@pytest.fixture
def claude_service(app):
    """Create a ClaudeService instance."""
    with app.app_context():
        return ClaudeService()

def test_service_initialization(claude_service):
    """Test ClaudeService initialization."""
    assert claude_service is not None

def test_api_key_configured():
    """Test that API key is configured."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    assert api_key is not None
    assert len(api_key) > 0

def test_model_configured():
    """Test that model is configured."""
    model = os.getenv('CLAUDE_MODEL')
    assert model is not None
    assert 'claude' in model.lower()
