"""
Models Routes - API endpoints for model listing, discovery, and testing.
"""

from flask import Blueprint, request, jsonify
from app.services.model_router_service import ModelRouterService

models_bp = Blueprint('models', __name__)
model_router = ModelRouterService()


@models_bp.route('/models', methods=['GET'])
def list_models():
    """List all available AI models across providers."""
    try:
        models = model_router.list_available_models()
        return jsonify({'models': models})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@models_bp.route('/models/ollama/discover', methods=['GET'])
def discover_ollama():
    """Discover locally available Ollama models."""
    try:
        models = model_router.discover_ollama_models()
        return jsonify({'ollama_models': models, 'count': len(models)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@models_bp.route('/models/test', methods=['POST'])
def test_model():
    """Test connectivity to a model endpoint."""
    data = request.get_json()
    if not data or 'model_id' not in data:
        return jsonify({'error': 'model_id is required'}), 400

    try:
        result = model_router.test_model(data['model_id'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
