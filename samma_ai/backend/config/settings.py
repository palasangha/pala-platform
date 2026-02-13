"""
Samma AI Backend - Configuration Settings
"""

import os
from pathlib import Path


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database paths
    BASE_DIR = Path(__file__).parent.parent.parent
    TIPITAKA_DB_PATH = os.environ.get('TIPITAKA_DB_PATH', str(BASE_DIR / 'database' / 'tipitaka_ultimate.db'))

    # MongoDB
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/samma_ai')

    # Claude API
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

    # OpenAI API
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')

    # Copilot-compatible endpoint
    COPILOT_ENDPOINT = os.environ.get('COPILOT_ENDPOINT', '')
    COPILOT_API_KEY = os.environ.get('COPILOT_API_KEY', '')

    # Ollama API
    OLLAMA_ENABLED = os.environ.get('OLLAMA_ENABLED', 'True').lower() == 'true'
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2-vision:latest')

    # CORS
    CORS_ORIGINS = ['http://localhost:8080', 'http://localhost:3000', 'http://localhost:41081', 'http://localhost:12345', '*']


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    MONGO_URI = 'mongodb://localhost:27017/samma_ai_test'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
