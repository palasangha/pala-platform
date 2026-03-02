"""
Storage Integration Routes - Connect OCR/Enrichment pipeline to Storage Layer

This module provides the bridge between the OCR/enrichment pipeline and the
storage layer, handling:
- Storing OCR results and enriched metadata
- Retrieving stored documents
- Managing document versions
- Digital signing workflow
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import asyncio
import hashlib
import importlib
import json

from app.models import mongo
from app.models.user import User
from app.models.bulk_job import BulkJob
from app.models.audit_log import AuditLog
from app.utils.decorators import token_required

# Import storage API
try:
    StorageAPI = importlib.import_module('api.storage_api').StorageAPI
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    print("Warning: Legacy Storage API not available. Storage integration endpoints are disabled.")

storage_bp = Blueprint('storage', __name__, url_prefix='/storage')

# Initialize storage API (configured for development)
if STORAGE_AVAILABLE:
    storage_api = StorageAPI(
        backends_config={
            'sqlite': {
                'enabled': True,
                'default': True,
                'config': {
                    'db_path': './pala_content.db'
                }
            }
        }
    )


# ============================================================================
# STORE ENRICHED DOCUMENT
# ============================================================================

@storage_bp.route('/store-document', methods=['POST'])
@token_required
def store_document(current_user_id):
    """
    Store OCR results and enriched metadata in storage layer
    
    Expected payload:
    {
        "job_id": "...",
        "file_index": 0,
        "ocr_text": "...",
        "enriched_metadata": {...},
        "original_file_path": "...",
        "content_type": "document"
    }
    """
    if not STORAGE_AVAILABLE:
        return jsonify({'error': 'Storage layer not available'}), 503
    
    try:
        data = request.get_json()
        
        job_id = data.get('job_id')
        file_index = data.get('file_index', 0)
        ocr_text = data.get('ocr_text', '')
        enriched_metadata = data.get('enriched_metadata', {})
        original_file_path = data.get('original_file_path', '')
        content_type = data.get('content_type', 'document')
        
        if not job_id:
            return jsonify({'error': 'job_id is required'}), 400
        
        # Get job from MongoDB
        job = BulkJob.get_by_job_id(mongo, job_id)
        if not job:
            return jsonify({'error': f'Job {job_id} not found'}), 404
        
        # Prepare content (OCR text + metadata as JSON)
        document_content = {
            'ocr_text': ocr_text,
            'enriched_metadata': enriched_metadata,
            'original_file': original_file_path,
            'processing_metadata': {
                'job_id': job_id,
                'file_index': file_index,
                'processed_at': datetime.utcnow().isoformat(),
                'processor_version': '1.0.0'
            }
        }
        
        content_bytes = json.dumps(document_content, indent=2).encode('utf-8')
        
        # Build metadata for storage layer
        storage_metadata = {
            'source_file': original_file_path,
            'job_id': job_id,
            'file_index': file_index,
            'content_type': content_type,
            'workflow_step': 'enrichment_complete',
            'processed_by': str(current_user_id),
            'enrichment_quality': enriched_metadata.get('quality_metrics', {}),
            'document_metadata': enriched_metadata.get('document', {}),
        }
        
        # Store in storage layer (async operation)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            storage_api.store_content(
                content=content_bytes,
                content_type=content_type,
                metadata=storage_metadata
            )
        )
        
        loop.close()
        
        # Update MongoDB with storage reference
        mongo.db.bulk_jobs.update_one(
            {'job_id': job_id},
            {
                '$set': {
                    f'files.{file_index}.storage_content_id': result.content_id,
                    f'files.{file_index}.storage_backend': result.backend_name,
                    f'files.{file_index}.stored_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        # Audit log
        AuditLog.create(
            mongo,
            current_user_id,
            'DOCUMENT_STORED',
            details={
                'job_id': job_id,
                'file_index': file_index,
                'content_id': result.content_id,
                'backend': result.backend_name,
                'size_bytes': result.file_size
            }
        )
        
        return jsonify({
            'success': True,
            'content_id': result.content_id,
            'backend': result.backend_name,
            'size': result.file_size,
            'hash': result.file_hash,
            'version': result.version
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to store document: {e}", exc_info=True)
        return jsonify({'error': f'Storage failed: {str(e)}'}), 500


# ============================================================================
# RETRIEVE STORED DOCUMENT
# ============================================================================

@storage_bp.route('/retrieve/<content_id>', methods=['GET'])
@token_required
def retrieve_document(current_user_id, content_id):
    """Retrieve stored document by content_id"""
    if not STORAGE_AVAILABLE:
        return jsonify({'error': 'Storage layer not available'}), 503
    
    try:
        # Get metadata first
        metadata = storage_api.get_content_metadata(content_id)
        if not metadata:
            return jsonify({'error': 'Document not found'}), 404
        
        # Check if user has access (basic check for now)
        # TODO: Implement proper RBAC checks
        
        # Retrieve content
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        content_bytes = loop.run_until_complete(
            storage_api.read_content(content_id)
        )
        
        loop.close()
        
        # Parse content
        document_content = json.loads(content_bytes.decode('utf-8'))
        
        # Audit log
        AuditLog.create(
            mongo,
            current_user_id,
            'DOCUMENT_RETRIEVED',
            details={'content_id': content_id}
        )
        
        return jsonify({
            'content_id': content_id,
            'document': document_content,
            'metadata': {
                'content_type': metadata.content_type,
                'file_size': metadata.file_size,
                'file_hash': metadata.file_hash,
                'version': metadata.version,
                'created_at': metadata.created_at.isoformat() if metadata.created_at else None,
                'updated_at': metadata.updated_at.isoformat() if metadata.updated_at else None,
                'backend_name': metadata.backend_name,
                **metadata.metadata
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to retrieve document: {e}", exc_info=True)
        return jsonify({'error': f'Retrieval failed: {str(e)}'}), 500


# ============================================================================
# LIST STORED DOCUMENTS
# ============================================================================

@storage_bp.route('/list', methods=['GET'])
@token_required
def list_documents(current_user_id):
    """List all stored documents with filtering"""
    if not STORAGE_AVAILABLE:
        return jsonify({'error': 'Storage layer not available'}), 503
    
    try:
        content_type = request.args.get('content_type', None)
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # List content from storage
        items = storage_api.list_content(content_type=content_type)
        
        # Apply pagination
        total = len(items)
        items = items[offset:offset + limit]
        
        # Format response
        documents = []
        for item in items:
            documents.append({
                'content_id': item.content_id,
                'content_type': item.content_type,
                'file_size': item.file_size,
                'file_hash': item.file_hash,
                'version': item.version,
                'backend_name': item.backend_name,
                'created_at': item.created_at.isoformat() if item.created_at else None,
                'metadata': item.metadata
            })
        
        return jsonify({
            'documents': documents,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        return jsonify({'error': f'List failed: {str(e)}'}), 500


# ============================================================================
# DIGITAL SIGNING (PLACEHOLDER)
# ============================================================================

@storage_bp.route('/sign-document', methods=['POST'])
@token_required
def sign_document(current_user_id):
    """
    Apply digital signature to document
    
    TODO: Implement actual cryptographic signing
    For now, this creates a signature record in metadata
    """
    if not STORAGE_AVAILABLE:
        return jsonify({'error': 'Storage layer not available'}), 503

    try:
        data = request.get_json()
        content_id = data.get('content_id')
        signature_method = data.get('method', 'SHA256-RSA')
        
        if not content_id:
            return jsonify({'error': 'content_id is required'}), 400
        
        # Get user info
        user = User.get_by_id(mongo, current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate signature placeholder
        # TODO: Replace with actual cryptographic signing
        signature_data = {
            'signer_id': str(current_user_id),
            'signer_name': user.get('email', 'unknown'),
            'signed_at': datetime.utcnow().isoformat(),
            'method': signature_method,
            'signature': hashlib.sha256(
                f"{content_id}{current_user_id}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
        }
        
        # Update storage metadata
        storage_api.update_metadata(content_id, {
            'digital_signature': signature_data,
            'workflow_step': 'signed',
            'status': 'approved_and_signed'
        })
        
        # Audit log
        AuditLog.create(
            mongo,
            current_user_id,
            'DOCUMENT_SIGNED',
            details={
                'content_id': content_id,
                'signature_method': signature_method
            }
        )
        
        return jsonify({
            'success': True,
            'content_id': content_id,
            'signature': signature_data
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to sign document: {e}", exc_info=True)
        return jsonify({'error': f'Signing failed: {str(e)}'}), 500


# ============================================================================
# STORAGE STATISTICS
# ============================================================================

@storage_bp.route('/stats', methods=['GET'])
@token_required
def get_storage_stats(current_user_id):
    """Get storage layer statistics"""
    if not STORAGE_AVAILABLE:
        return jsonify({'error': 'Storage layer not available'}), 503
    
    try:
        stats = storage_api.get_stats()
        
        return jsonify({
            'total_items': stats['total_items'],
            'total_size_bytes': stats['total_size'],
            'total_size_mb': round(stats['total_size'] / (1024 * 1024), 2),
            'by_backend': stats['by_backend'],
            'by_type': stats['by_type'],
            'backends_healthy': all(
                storage_api.get_backend_health(name)['is_healthy']
                for name in stats['by_backend'].keys()
            )
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        return jsonify({'error': f'Stats failed: {str(e)}'}), 500


import logging
logger = logging.getLogger(__name__)
