"""Flask blueprint for LangChain Ollama endpoints."""

from flask import Blueprint, request, jsonify, Response
from app.services.langchain_service import get_langchain_service
import logging

logger = logging.getLogger(__name__)

langchain_bp = Blueprint('langchain', __name__, url_prefix='/api/langchain')


@langchain_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for Ollama server via LangChain."""
    try:
        service = get_langchain_service()
        is_healthy = service.health_check()
        
        if is_healthy:
            return jsonify({
                'status': 'healthy',
                'model': service.model,
                'host': service.ollama_host,
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'error': 'Cannot connect to Ollama server',
            }), 503
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
        }), 500


@langchain_bp.route('/invoke', methods=['POST'])
def invoke():
    """Invoke the LLM with a prompt."""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        temperature = data.get('temperature', 0.7)
        
        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400
        
        service = get_langchain_service()
        response = service.invoke(prompt)
        
        return jsonify({
            'prompt': prompt,
            'response': response,
            'model': service.model,
        }), 200
    except Exception as e:
        logger.error(f"Invoke error: {e}")
        return jsonify({'error': str(e)}), 500


@langchain_bp.route('/batch', methods=['POST'])
def batch_invoke():
    """Invoke the LLM with multiple prompts."""
    try:
        data = request.get_json()
        prompts = data.get('prompts', [])
        
        if not isinstance(prompts, list) or not prompts:
            return jsonify({'error': 'prompts must be a non-empty list'}), 400
        
        service = get_langchain_service()
        responses = service.batch_invoke(prompts)
        
        return jsonify({
            'prompts': prompts,
            'responses': responses,
            'model': service.model,
        }), 200
    except Exception as e:
        logger.error(f"Batch invoke error: {e}")
        return jsonify({'error': str(e)}), 500


@langchain_bp.route('/embed', methods=['POST'])
def embed():
    """Get embeddings for texts."""
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        
        if not isinstance(texts, list):
            texts = [texts] if isinstance(texts, str) else []
        
        if not texts:
            return jsonify({'error': 'texts is required (string or list)'}), 400
        
        service = get_langchain_service()
        
        if len(texts) == 1:
            embedding = service.get_embedding(texts[0])
            return jsonify({
                'text': texts[0],
                'embedding': embedding,
                'model': service.embedding_model,
            }), 200
        else:
            embeddings = service.get_embeddings(texts)
            return jsonify({
                'texts': texts,
                'embeddings': embeddings,
                'model': service.embedding_model,
            }), 200
    except Exception as e:
        logger.error(f"Embed error: {e}")
        return jsonify({'error': str(e)}), 500


@langchain_bp.route('/chat', methods=['POST'])
def chat():
    """Chat with the LLM (with conversation memory)."""
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'message is required'}), 400
        
        service = get_langchain_service()
        response = service.chat(message)
        
        return jsonify({
            'message': message,
            'response': response,
            'model': service.model,
        }), 200
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500


@langchain_bp.route('/stream', methods=['POST'])
def stream():
    """Stream completions from the LLM."""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400
        
        service = get_langchain_service()
        
        def generate():
            for chunk in service.stream_invoke(prompt):
                yield f"data: {chunk}\n\n"
        
        return Response(generate(), mimetype='text/event-stream'), 200
    except Exception as e:
        logger.error(f"Stream error: {e}")
        return jsonify({'error': str(e)}), 500


@langchain_bp.route('/config', methods=['GET'])
def get_config():
    """Get current LangChain configuration."""
    try:
        service = get_langchain_service()
        
        return jsonify({
            'ollama_host': service.ollama_host,
            'model': service.model,
            'embedding_model': service.embedding_model,
            'temperature': service.temperature,
            'top_k': service.top_k,
            'top_p': service.top_p,
        }), 200
    except Exception as e:
        logger.error(f"Config error: {e}")
        return jsonify({'error': str(e)}), 500
