"""
Flask Server for Storage API
Provides HTTP endpoints for the storage layer
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import asyncio
import logging
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.storage_api import StorageAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize storage API
storage_dir = Path(__file__).parent.parent / 'data'
storage_dir.mkdir(exist_ok=True)

db_path = storage_dir / 'pala_storage.db'
content_path = storage_dir / 'content'

storage_api = StorageAPI(
    db_path=str(db_path),
    backends_config={
        'local': {
            'enabled': True,
            'default': True,
            'config': {
                'base_path': str(content_path)
            }
        }
    }
)

logger.info(f"Storage initialized - DB: {db_path}, Content: {content_path}")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'pala-storage-api'})


@app.route('/storage/backends', methods=['GET'])
def list_backends():
    """List available storage backends"""
    try:
        backends = []
        
        # Get all registered backends from the manager
        for backend_name in storage_api.backend_manager.backends.keys():
            backend = storage_api.backend_manager.backends[backend_name]
            is_default = backend_name == storage_api.backend_manager.default_backend_name
            
            backends.append({
                'name': backend_name,
                'type': backend.__class__.__name__,
                'is_default': is_default,
                'enabled': True
            })
        
        return jsonify({
            'backends': backends,
            'default_backend': storage_api.backend_manager.default_backend_name
        })
        
    except Exception as e:
        logger.error(f"Error listing backends: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/storage/store-document', methods=['POST'])
def store_document():
    """
    Store document with OCR text and metadata
    
    Expected JSON:
    {
        "job_id": "job-123",
        "file_index": 0,
        "ocr_text": "extracted text...",
        "enriched_metadata": {...},
        "original_file_path": "document.jpg",
        "backend": "local-primary" (optional)
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('ocr_text') and not data.get('content'):
            return jsonify({'error': 'ocr_text or content is required'}), 400
        
        # Prepare content
        ocr_text = data.get('ocr_text') or data.get('content', '')
        backend_name = data.get('backend')
        
        metadata = {
            'job_id': data.get('job_id'),
            'file_index': data.get('file_index', 0),
            'original_file_path': data.get('original_file_path'),
            'enriched_metadata': data.get('enriched_metadata', {}),
            'document_metadata': data.get('document_metadata', {}),
            'content_type': data.get('content_type', 'document')
        }
        
        # Store in storage layer
        content_bytes = ocr_text.encode('utf-8')
        
        # Check for duplicate before storing
        import hashlib
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        existing = storage_api._find_by_hash(file_hash)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        stored = loop.run_until_complete(
            storage_api.store_content(
                content=content_bytes,
                content_type=data.get('content_type', 'document'),
                metadata=metadata,
                signature=data.get('signature'),
                tags=data.get('tags', {}),
                backend_name=backend_name
            )
        )
        
        loop.close()
        
        # Determine if deduplicated
        is_duplicate = existing is not None
        
        return jsonify({
            'content_id': stored.content_id,
            'provider': 'pala-storage-provider',
            'backend': stored.backend_name,
            'path': stored.backend_location,
            'version': stored.version,
            'size': stored.file_size,
            'file_hash': stored.file_hash,
            'created_at': stored.created_at,
            'deduplication': is_duplicate,
            'message': 'Content already exists (deduplicated)' if is_duplicate else 'Content stored successfully'
        })
        
    except Exception as e:
        logger.error(f"Error storing document: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/storage/retrieve/<content_id>', methods=['GET'])
def retrieve_document(content_id):
    """Retrieve document by content ID"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            storage_api.retrieve_content(content_id)
        )
        
        loop.close()
        
        if not result:
            return jsonify({'error': 'Content not found'}), 404
        
        content, metadata = result
        
        return jsonify({
            'ocr_text': content.decode('utf-8'),
            'enriched_metadata': metadata.metadata.get('enriched_metadata', {}),
            'storage_metadata': {
                'content_id': metadata.content_id,
                'backend': metadata.backend_name,
                'size': metadata.file_size,
                'hash': metadata.file_hash,
                'version': metadata.version,
                'created_at': metadata.created_at
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving document: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/storage/list', methods=['GET'])
def list_documents():
    """List all stored documents"""
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        content_type = request.args.get('content_type')
        backend = request.args.get('backend')
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            storage_api.list_content(
                content_type=content_type,
                backend_name=backend,
                limit=limit,
                offset=offset
            )
        )
        
        loop.close()
        
        items = [{
            'content_id': item.content_id,
            'backend': item.backend_name,
            'size': item.file_size,
            'hash': item.file_hash,
            'version': item.version,
            'created_at': item.created_at,
            'metadata': item.metadata
        } for item in results]
        
        return jsonify({'items': items, 'count': len(items)})
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/storage/stats', methods=['GET'])
def get_stats():
    """Get storage statistics"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        stats = loop.run_until_complete(storage_api.get_stats())
        
        loop.close()
        
        return jsonify({
            'total_items': stats.total_items,
            'total_size': stats.total_size,
            'by_backend': stats.by_backend,
            'by_content_type': stats.by_content_type
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/storage/sign-document', methods=['POST'])
def sign_document():
    """Digital signing endpoint (placeholder)"""
    try:
        data = request.json
        content_id = data.get('content_id')
        
        # For now, return a mock signature
        # In production, this would integrate with a signing service
        return jsonify({
            'signature': f'sig_{content_id}_{int(datetime.now().timestamp())}',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'algorithm': 'SHA-256'
        })
        
    except Exception as e:
        logger.error(f"Error signing document: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
