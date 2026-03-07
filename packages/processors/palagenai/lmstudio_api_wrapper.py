#!/usr/bin/env python3
"""
LMStudio API Wrapper - Lightweight REST API interface for LMStudio
Provides OpenAI-compatible API endpoints
"""

import os
import json
import logging
from flask import Flask, jsonify, request
from waitress import serve
import requests
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration from environment
LMSTUDIO_API_BASE = os.getenv('LMSTUDIO_API_BASE', 'http://127.0.0.1:1234')
API_PORT = int(os.getenv('LMSTUDIO_PORT', 1234))
API_HOST = os.getenv('LMSTUDIO_HOST', '0.0.0.0')

# Timeout for requests
REQUEST_TIMEOUT = int(os.getenv('LMSTUDIO_TIMEOUT', 600))

logger.info(f"Starting LMStudio API Wrapper")
logger.info(f"  Host: {API_HOST}:{API_PORT}")
logger.info(f"  Backend: {LMSTUDIO_API_BASE}")
logger.info(f"  Timeout: {REQUEST_TIMEOUT}s")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'lmstudio-api-wrapper',
        'version': '1.0'
    }), 200

@app.route('/v1/models', methods=['GET'])
def list_models():
    """List available models from LMStudio"""
    try:
        response = requests.get(
            f'{LMSTUDIO_API_BASE}/v1/models',
            timeout=5
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.ConnectionError:
        logger.warning(f"Failed to connect to LMStudio at {LMSTUDIO_API_BASE}")
        return jsonify({
            'error': 'LMStudio not available',
            'details': 'Cannot connect to LMStudio backend',
            'backend_url': LMSTUDIO_API_BASE
        }), 503
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({
            'error': 'Failed to list models',
            'details': str(e)
        }), 500

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """Chat completion endpoint - proxy to LMStudio"""
    try:
        data = request.get_json()
        
        # Log the request
        model = data.get('model', 'unknown')
        logger.info(f"Chat completion request for model: {model}")
        
        response = requests.post(
            f'{LMSTUDIO_API_BASE}/v1/chat/completions',
            json=data,
            timeout=REQUEST_TIMEOUT
        )
        
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout (timeout={REQUEST_TIMEOUT}s)")
        return jsonify({
            'error': 'Request timeout',
            'message': f'Request took longer than {REQUEST_TIMEOUT}s'
        }), 504
    except requests.exceptions.ConnectionError:
        logger.error(f"Failed to connect to LMStudio at {LMSTUDIO_API_BASE}")
        return jsonify({
            'error': 'Backend unavailable',
            'details': 'Cannot connect to LMStudio'
        }), 503
    except Exception as e:
        logger.error(f"Error in chat completions: {e}")
        return jsonify({
            'error': 'Failed to process request',
            'details': str(e)
        }), 500

@app.route('/v1/completions', methods=['POST'])
def completions():
    """Text completion endpoint - proxy to LMStudio"""
    try:
        data = request.get_json()
        logger.info(f"Completion request received")
        
        response = requests.post(
            f'{LMSTUDIO_API_BASE}/v1/completions',
            json=data,
            timeout=REQUEST_TIMEOUT
        )
        
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout',
            'message': f'Request took longer than {REQUEST_TIMEOUT}s'
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Backend unavailable',
            'details': 'Cannot connect to LMStudio'
        }), 503
    except Exception as e:
        logger.error(f"Error in completions: {e}")
        return jsonify({
            'error': 'Failed to process request',
            'details': str(e)
        }), 500

@app.route('/v1/embeddings', methods=['POST'])
def embeddings():
    """Embeddings endpoint - proxy to LMStudio"""
    try:
        data = request.get_json()
        logger.info(f"Embeddings request received")
        
        response = requests.post(
            f'{LMSTUDIO_API_BASE}/v1/embeddings',
            json=data,
            timeout=30
        )
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error in embeddings: {e}")
        return jsonify({
            'error': 'Failed to process request',
            'details': str(e)
        }), 500

@app.route('/status', methods=['GET'])
def status():
    """Get detailed status of LMStudio connection"""
    try:
        response = requests.get(
            f'{LMSTUDIO_API_BASE}/v1/models',
            timeout=5
        )
        
        return jsonify({
            'wrapper': {
                'status': 'ready',
                'host': API_HOST,
                'port': API_PORT,
                'timeout': REQUEST_TIMEOUT
            },
            'backend': {
                'connected': response.ok,
                'url': LMSTUDIO_API_BASE,
                'models': response.json() if response.ok else None
            }
        }), 200
    except Exception as e:
        logger.warning(f"Backend connection check failed: {e}")
        return jsonify({
            'wrapper': {
                'status': 'ready',
                'host': API_HOST,
                'port': API_PORT
            },
            'backend': {
                'connected': False,
                'url': LMSTUDIO_API_BASE,
                'error': str(e)
            }
        }), 200

@app.route('/', methods=['GET'])
def index():
    """API index page"""
    return jsonify({
        'name': 'LMStudio API Wrapper',
        'version': '1.0',
        'endpoints': {
            '/health': 'Health check',
            '/status': 'Detailed status',
            '/v1/models': 'List available models',
            '/v1/chat/completions': 'Chat completion',
            '/v1/completions': 'Text completion',
            '/v1/embeddings': 'Generate embeddings'
        },
        'backend': LMSTUDIO_API_BASE
    }), 200

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'path': request.path,
        'method': request.method,
        'message': 'See / for available endpoints'
    }), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {e}")
    return jsonify({
        'error': 'Internal server error',
        'details': str(e)
    }), 500

if __name__ == '__main__':
    try:
        logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
        logger.info(f"Press Ctrl+C to shutdown")
        serve(app, host=API_HOST, port=API_PORT, threads=4)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
