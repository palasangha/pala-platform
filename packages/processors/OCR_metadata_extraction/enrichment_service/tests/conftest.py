"""
Pytest configuration and fixtures for enrichment service tests

Provides test database, mock clients, and sample data
"""

import pytest
import os
from typing import Dict, Any, Generator
from mongomock import MongoClient as MockMongoClient
from unittest.mock import Mock, AsyncMock, patch


# ===================== Fixtures =====================

@pytest.fixture
def mock_db():
    """Provide mock MongoDB database"""
    client = MockMongoClient()
    db = client['test_gvpocr']

    # Create collections
    db.enrichment_jobs.create_index([('_id', 1)])
    db.enriched_documents.create_index([('_id', 1)])
    db.review_queue.create_index([('_id', 1)])
    db.cost_records.create_index([('_id', 1)])

    return db


@pytest.fixture
def mock_config():
    """Provide test configuration"""
    return {
        'MONGO_URI': 'mongodb://localhost:27017/test_gvpocr',
        'DB_NAME': 'test_gvpocr',
        'MAX_COST_PER_DOC': 0.50,
        'DAILY_BUDGET_USD': 100.00,
        'MONTHLY_BUDGET_USD': 2000.00,
        'COST_ALERT_THRESHOLD': 80.00,
        'MCP_SERVER_URL': 'ws://localhost:3000',
        'COMPLETENESS_THRESHOLD': 0.95,
        'SCHEMA_PATH': '/app/enrichment_service/schema/historical_letters_schema.json'
    }


@pytest.fixture
def mock_mcp_client():
    """Provide mock MCP client"""
    client = AsyncMock()
    client.invoke_tool = AsyncMock()
    return client


# ===================== Sample Data Fixtures =====================

@pytest.fixture
def sample_ocr_data() -> Dict[str, Any]:
    """Sample OCR extracted data from a historical letter"""
    return {
        'text': '''S.N. Goenka
Vipassana International Academy
Dhammagiri, Igatpuri
Maharashtra 422403, India

15th March 1985

Dear Friend,

I am pleased to inform you that we will be conducting a 10-day Vipassana meditation course
at Dhamma Giri from April 1-12, 1985.

This ancient technique, as taught by Sayagyi U Ba Khin in the tradition of the Buddha,
has helped thousands find inner peace and liberation from suffering.

The course is open to all serious students without distinction of caste, creed, or religion.
Participants must have faith in the technique and commit fully to the discipline.

Please apply early as spaces are limited. For more details, contact the academy office.

With all good wishes for your spiritual progress,

S.N. Goenka
Founder, Vipassana International Academy''',
        'full_text': '''S.N. Goenka
Vipassana International Academy
Dhammagiri, Igatpuri
Maharashtra 422403, India

15th March 1985

Dear Friend,

I am pleased to inform you that we will be conducting a 10-day Vipassana meditation course
at Dhamma Giri from April 1-12, 1985.

This ancient technique, as taught by Sayagyi U Ba Khin in the tradition of the Buddha,
has helped thousands find inner peace and liberation from suffering.

The course is open to all serious students without distinction of caste, creed, or religion.
Participants must have faith in the technique and commit fully to the discipline.

Please apply early as spaces are limited. For more details, contact the academy office.

With all good wishes for your spiritual progress,

S.N. Goenka
Founder, Vipassana International Academy''',
        'confidence': 0.92,
        'detected_language': 'en',
        'provider': 'google_vision',
        'ocr_job_id': 'ocr_test_123',
        'file_path': '/uploads/test_letter.jpg',
        'file_metadata': {
            'filename': 'test_letter.jpg',
            'size': 1024000,
            'extension': '.jpg',
            'upload_date': '2025-01-17T12:00:00Z',
            'dpi': 300,
            'image_width': 2550,
            'image_height': 3300
        }
    }


@pytest.fixture
def sample_enriched_data() -> Dict[str, Any]:
    """Sample enriched data from agents"""
    return {
        'metadata': {
            'id': 'doc_test_123',
            'collection_id': 'goenka_letters',
            'document_type': 'letter',
            'access_level': 'public',
            'storage_location': {
                'archive_name': 'Vipassana Research Institute',
                'collection_name': 'S.N. Goenka Correspondence',
                'box_number': 5,
                'folder_number': 3,
                'digital_repository': 'https://vri-archive.org'
            },
            'digitization_info': {
                'date': '2025-01-15',
                'operator': 'archive_team',
                'equipment': 'Epson Expression 12000XL',
                'resolution': '300 DPI',
                'file_format': 'JPEG'
            }
        },
        'document': {
            'date': {'year': 1985, 'month': 3, 'day': 15},
            'languages': ['English'],
            'physical_attributes': {
                'size': '8.5\" x 11\"',
                'material': 'Paper',
                'condition': 'Good',
                'pages': 1
            },
            'correspondence': {
                'sender': {
                    'name': 'S.N. Goenka',
                    'title': 'Founder, Vipassana International Academy',
                    'location': 'Igatpuri, Maharashtra, India'
                },
                'recipient': {
                    'name': 'Friend',
                    'title': 'Unknown',
                    'location': 'Unknown'
                },
                'date': '1985-03-15'
            }
        },
        'content': {
            'full_text': 'Full text of letter...',
            'summary': 'S.N. Goenka announces a 10-day Vipassana meditation course at Dhamma Giri (April 1-12, 1985), inviting sincere practitioners to learn the ancient meditation technique taught in the Buddha\'s tradition.',
            'salutation': 'Dear Friend,',
            'body': [
                'I am pleased to inform you that we will be conducting a 10-day Vipassana meditation course at Dhamma Giri from April 1-12, 1985.',
                'This ancient technique, as taught by Sayagyi U Ba Khin in the tradition of the Buddha, has helped thousands find inner peace and liberation from suffering.',
                'The course is open to all serious students without distinction of caste, creed, or religion.',
                'Please apply early as spaces are limited.'
            ],
            'closing': 'With all good wishes for your spiritual progress,',
            'signature': 'S.N. Goenka'
        },
        'analysis': {
            'keywords': ['Vipassana', 'meditation', 'course', 'Buddhism', 'spiritual', 'Dhamma Giri', 'liberation'],
            'subjects': ['spiritual_practice', 'event_invitation', 'educational_content'],
            'people': [
                {
                    'name': 'S.N. Goenka',
                    'role': 'sender',
                    'title': 'Founder',
                    'biography': 'S.N. Goenka was a renowned teacher of Vipassana meditation...'
                },
                {
                    'name': 'Sayagyi U Ba Khin',
                    'role': 'mentioned',
                    'title': 'Meditation Master',
                    'biography': 'Sayagyi U Ba Khin was a prominent Burmese meditation teacher...'
                }
            ],
            'organizations': [
                {
                    'name': 'Vipassana International Academy',
                    'type': 'spiritual_institution',
                    'location': 'Igatpuri, India'
                }
            ],
            'locations': [
                {
                    'name': 'Igatpuri',
                    'type': 'city',
                    'country': 'India',
                    'state': 'Maharashtra'
                },
                {
                    'name': 'Dhamma Giri',
                    'type': 'institution',
                    'location': 'Igatpuri'
                }
            ],
            'events': [
                {
                    'name': '10-day Vipassana Course',
                    'date': '1985-04-01 to 1985-04-12',
                    'location': 'Dhamma Giri',
                    'type': 'meditation_retreat'
                }
            ],
            'historical_context': 'This letter was written during the early years of the global Vipassana movement...',
            'significance': 'high'
        }
    }


@pytest.fixture
def sample_collection_metadata() -> Dict[str, Any]:
    """Sample collection metadata"""
    return {
        'collection_id': 'goenka_letters',
        'collection_name': 'S.N. Goenka Correspondence',
        'archive_name': 'Vipassana Research Institute',
        'total_documents': 100,
        'date_range': {'start': 1960, 'end': 2002},
        'primary_language': 'English'
    }


# ===================== Historical Letters for Testing =====================

@pytest.fixture
def historical_letter_sample_1() -> Dict[str, Any]:
    """First sample historical letter (invitation)"""
    return {
        'text': '''10 May 1978

Dear Shri Desai,

You are cordially invited to attend the opening ceremony of the new Vipassana
meditation center in New Delhi on June 15, 1978 at 3 PM.

As one of the distinguished supporters of this noble cause, your presence would
mean a great deal to us and to all the participants.

The center aims to serve those seeking genuine spiritual development through
the authentic Vipassana technique.

Looking forward to seeing you.

Yours in Dhamma,
S.N. Goenka''',
        'confidence': 0.95,
        'detected_language': 'en',
        'file_path': '/uploads/invitation_1978.jpg'
    }


@pytest.fixture
def historical_letter_sample_2() -> Dict[str, Any]:
    """Second sample historical letter (personal)"""
    return {
        'text': '''25 December 1990

My dear friend,

I hope this letter finds you in good health and spirits. It has been too long
since we last met.

The meditation practice continues to deepen and bring peace to many seekers.
Each course seems more meaningful than the last as we refine our teaching methods.

I would very much like to discuss the proposed European centers with you.
Your experience and wisdom would be invaluable.

Please visit us in Igatpuri whenever you can.

In good wishes,
S.N. Goenka''',
        'confidence': 0.88,
        'detected_language': 'en',
        'file_path': '/uploads/personal_1990.jpg'
    }


# ===================== Mock Data Helpers =====================

@pytest.fixture
def cost_tracker_fixture(mock_db, mock_config):
    """Provide initialized CostTracker"""
    from enrichment_service.utils.cost_tracker import CostTracker
    return CostTracker(mock_db, mock_config)


@pytest.fixture
def budget_manager_fixture(mock_db, mock_config):
    """Provide initialized BudgetManager"""
    from enrichment_service.utils.budget_manager import BudgetManager
    return BudgetManager(mock_db, mock_config)


@pytest.fixture
def review_queue_fixture(mock_db):
    """Provide initialized ReviewQueue"""
    from enrichment_service.review.review_queue import ReviewQueue
    return ReviewQueue(mock_db)


# ===================== Pytest Configuration =====================

def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
