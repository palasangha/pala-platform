"""
Health Routes - System health and status checks
"""

from flask import Blueprint, jsonify, current_app
from app.services.tipitaka_service import TipitakaService
from app import mongo
import os

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'samma-ai-backend'
    })


@health_bp.route('/status', methods=['GET'])
def detailed_status():
    """Detailed system status with database connectivity checks."""
    status = {
        'service': 'samma-ai-backend',
        'version': '1.0.0',
        'checks': {}
    }

    # Check MongoDB
    try:
        mongo.db.command('ping')
        status['checks']['mongodb'] = {'status': 'connected'}
    except Exception as e:
        status['checks']['mongodb'] = {'status': 'error', 'message': str(e)}

    # Check Tipitaka database
    try:
        tipitaka = TipitakaService()
        count = tipitaka.get_paragraph_count()
        status['checks']['tipitaka_db'] = {
            'status': 'connected',
            'paragraphs': count
        }
    except Exception as e:
        status['checks']['tipitaka_db'] = {'status': 'error', 'message': str(e)}

    # Check Claude API key
    api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
    status['checks']['claude_api'] = {
        'status': 'configured' if api_key else 'not_configured'
    }

    # Check translation service (Ollama + Deepseek)
    try:
        translation_service = current_app.extensions.get('translation_service')
        if translation_service:
            if translation_service._is_ollama_available():
                status['checks']['translation_service'] = {
                    'status': 'healthy',
                    'model': current_app.config.get('OLLAMA_TRANSLATION_MODEL'),
                    'endpoint': current_app.config.get('OLLAMA_TRANSLATION_ENDPOINT')
                }
            else:
                status['checks']['translation_service'] = {
                    'status': 'degraded',  # Optional service
                    'message': 'Ollama not reachable'
                }
        else:
            status['checks']['translation_service'] = {
                'status': 'disabled'
            }
    except Exception as e:
        status['checks']['translation_service'] = {
            'status': 'error',
            'message': str(e)
        }

    # Overall status
    all_healthy = all(
        check.get('status') in ['connected', 'configured', 'healthy', 'disabled', 'degraded']
        for check in status['checks'].values()
    )
    status['status'] = 'healthy' if all_healthy else 'degraded'

    return jsonify(status)
