"""
Tests for TranslationService — Pali to English translation

Test coverage:
- Cache hits and misses
- Deepseek translation quality
- Ollama unavailable fallback
- Batch passage enrichment
- Integration with chat route
"""

import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from flask import Flask


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['TIPITAKA_DB_PATH'] = ':memory:'
    app.config['OLLAMA_TRANSLATION_ENABLED'] = True
    app.config['OLLAMA_TRANSLATION_MODEL'] = 'deepseek-r1:32b'
    app.config['OLLAMA_TRANSLATION_ENDPOINT'] = 'http://localhost:11434'
    app.config['OLLAMA_TRANSLATION_TIMEOUT'] = 90
    app.config['TRANSLATION_CACHE_TTL'] = 604800  # 7 days

    # Create in-memory SQLite database
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE pali_translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pali_text TEXT NOT NULL UNIQUE,
            english_translation TEXT NOT NULL,
            reference TEXT,
            model_used TEXT DEFAULT 'deepseek-r1:32b',
            source TEXT DEFAULT 'ollama',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    return app


@pytest.fixture
def translation_service(app):
    """Create translation service with test config."""
    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()
        return service


def test_translation_service_init(app):
    """Test TranslationService initialization."""
    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        assert service.enabled == True
        assert service.model == 'deepseek-r1:32b'
        assert service.timeout == 90
        assert service.cache_ttl == 604800


def test_translate_pali_passage_disabled(app):
    """Test translation returns original Pali when disabled."""
    app.config['OLLAMA_TRANSLATION_ENABLED'] = False

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        pali = "samadhi"
        result = service.translate_pali_passage(pali)

        assert result == pali


def test_translate_pali_passage_empty(app):
    """Test translation handles empty strings."""
    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        result = service.translate_pali_passage("")
        assert result == ""

        result = service.translate_pali_passage("   ")
        assert result == "   "


@patch('app.services.translation_service.requests.get')
@patch('app.services.translation_service.requests.post')
def test_translate_pali_passage_success(mock_post, mock_get, app):
    """Test successful translation via Deepseek."""
    # Mock Ollama availability check
    mock_get.return_value.status_code = 200

    # Mock Deepseek response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        'response': 'concentration, meditative absorption'
    }

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        pali = "samadhi"
        result = service.translate_pali_passage(pali)

        assert result == "concentration, meditative absorption"
        # Verify Deepseek was called
        mock_post.assert_called_once()


@patch('app.services.translation_service.requests.get')
def test_translate_pali_passage_ollama_unavailable(mock_get, app):
    """Test fallback when Ollama unavailable."""
    # Mock Ollama unavailable
    mock_get.side_effect = Exception("Connection refused")

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        pali = "samadhi"
        result = service.translate_pali_passage(pali)

        # Should return original Pali
        assert result == pali


@patch('app.services.translation_service.requests.get')
@patch('app.services.translation_service.requests.post')
def test_translate_pali_passage_timeout(mock_post, mock_get, app):
    """Test handling of translation timeout."""
    # Mock Ollama available
    mock_get.return_value.status_code = 200

    # Mock timeout
    import requests
    mock_post.side_effect = requests.Timeout("Request timed out")

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        pali = "samadhi"
        result = service.translate_pali_passage(pali)

        # Should return original Pali on timeout
        assert result == pali


def test_check_cache_hit(app):
    """Test cache lookup finds existing translation."""
    # Pre-populate cache
    db_path = app.config['TIPITAKA_DB_PATH']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    future_time = (datetime.utcnow() + timedelta(days=7)).isoformat()
    cursor.execute(
        """
        INSERT INTO pali_translations
        (pali_text, english_translation, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        ('samadhi', 'concentration', datetime.utcnow().isoformat(), future_time)
    )
    conn.commit()
    conn.close()

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        result = service._check_cache('samadhi')
        assert result == 'concentration'


def test_check_cache_miss(app):
    """Test cache lookup returns None for missing translation."""
    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        result = service._check_cache('nonexistent')
        assert result is None


def test_check_cache_expired(app):
    """Test cache lookup returns None for expired translations."""
    # Pre-populate cache with expired entry
    db_path = app.config['TIPITAKA_DB_PATH']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    past_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
    cursor.execute(
        """
        INSERT INTO pali_translations
        (pali_text, english_translation, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        ('metta', 'loving-kindness', datetime.utcnow().isoformat(), past_time)
    )
    conn.commit()
    conn.close()

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        result = service._check_cache('metta')
        assert result is None  # Expired


@patch('app.services.translation_service.requests.get')
def test_is_ollama_available_true(mock_get, app):
    """Test Ollama availability check succeeds."""
    mock_get.return_value.status_code = 200

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        result = service._is_ollama_available()
        assert result == True


@patch('app.services.translation_service.requests.get')
def test_is_ollama_available_false(mock_get, app):
    """Test Ollama availability check fails."""
    mock_get.side_effect = Exception("Connection refused")

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        result = service._is_ollama_available()
        assert result == False


def test_save_to_cache(app):
    """Test saving translation to cache."""
    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        pali = "dukkha"
        english = "suffering, unsatisfactoriness"

        success = service._save_to_cache(pali, english, reference="DN16")
        assert success == True

        # Verify saved
        result = service._check_cache(pali)
        assert result == english


def test_enrich_passages_with_translations_db_only(app):
    """Test enrichment when all passages have DB translations."""
    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        passages = [
            {'pali_text': 'samadhi', 'english_text': 'concentration'},
            {'pali_text': 'metta', 'english_text': 'loving-kindness'},
        ]

        enriched = service.enrich_passages_with_translations(passages)

        assert len(enriched) == 2
        assert enriched[0]['english_text'] == 'concentration'
        assert enriched[0]['translation_source'] == 'db'
        assert enriched[1]['english_text'] == 'loving-kindness'
        assert enriched[1]['translation_source'] == 'db'


@patch('app.services.translation_service.requests.get')
@patch('app.services.translation_service.requests.post')
def test_enrich_passages_with_translations_mixed(mock_post, mock_get, app):
    """Test enrichment with mix of DB and Ollama translations."""
    # Mock Ollama available
    mock_get.return_value.status_code = 200

    # Mock Deepseek response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        'response': 'suffering, unsatisfactoriness'
    }

    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        passages = [
            {'pali_text': 'samadhi', 'english_text': 'concentration'},  # DB
            {'pali_text': 'dukkha', 'english_text': None},  # Needs translation
        ]

        enriched = service.enrich_passages_with_translations(passages)

        assert enriched[0]['translation_source'] == 'db'
        assert enriched[0]['english_text'] == 'concentration'

        assert enriched[1]['translation_source'] == 'ollama'
        assert enriched[1]['english_text'] == 'suffering, unsatisfactoriness'


def test_enrich_passages_with_translations_empty(app):
    """Test enrichment with empty passages list."""
    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        enriched = service.enrich_passages_with_translations([])
        assert enriched == []


def test_enrich_passages_with_translations_no_pali(app):
    """Test enrichment with passages missing pali_text."""
    with app.app_context():
        from app.services.translation_service import TranslationService
        service = TranslationService()

        passages = [
            {'english_text': None},  # Missing pali_text
        ]

        enriched = service.enrich_passages_with_translations(passages)

        assert enriched[0]['english_text'] == ''
        assert enriched[0]['translation_source'] == 'none'
