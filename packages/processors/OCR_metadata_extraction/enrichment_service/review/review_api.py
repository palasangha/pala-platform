"""
Review API - REST endpoints for review queue management

Provides API for review interface to fetch pending tasks, approve/reject documents
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, jsonify, request, Blueprint
from pymongo import MongoClient
from functools import wraps

from enrichment_service.review.review_queue import ReviewQueue

logger = logging.getLogger(__name__)


def create_review_api(app: Flask, db=None) -> Blueprint:
    """
    Create review API blueprint

    Args:
        app: Flask application instance
        db: MongoDB database instance

    Returns:
        Blueprint with review endpoints
    """
    review_bp = Blueprint('review', __name__, url_prefix='/api/review')

    # Initialize review queue
    review_queue = ReviewQueue(db)

    # Middleware for authentication (placeholder)
    def require_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Unauthorized'}), 401
            # In production, validate JWT token here
            return f(*args, **kwargs)
        return decorated

    # ===================== Queue Management =====================

    @review_bp.route('/queue', methods=['GET'])
    @require_auth
    def get_queue():
        """
        Get pending review tasks

        Query parameters:
        - limit: Max results (default: 50, max: 100)
        - skip: Results to skip for pagination (default: 0)

        Returns:
            {
                "tasks": [
                    {
                        "_id": "review_abc123",
                        "document_id": "doc_456",
                        "reason": "completeness_below_threshold",
                        "missing_fields": ["analysis.keywords", ...],
                        "low_confidence_fields": [...],
                        "created_at": "2025-01-17T12:00:00Z",
                        "status": "pending"
                    },
                    ...
                ],
                "total": 42,
                "limit": 50,
                "skip": 0
            }
        """
        try:
            limit = min(int(request.args.get('limit', 50)), 100)
            skip = int(request.args.get('skip', 0))

            tasks = review_queue.get_pending_tasks(limit=limit, skip=skip)
            total = db.review_queue.count_documents({'status': 'pending'})

            return jsonify({
                'tasks': [_serialize_task(t) for t in tasks],
                'total': total,
                'limit': limit,
                'skip': skip
            }), 200

        except Exception as e:
            logger.error(f"Error getting queue: {e}")
            return jsonify({'error': str(e)}), 500

    @review_bp.route('/stats', methods=['GET'])
    @require_auth
    def get_stats():
        """
        Get review queue statistics

        Returns:
            {
                "pending": 12,
                "in_progress": 3,
                "approved": 45,
                "rejected": 2,
                "total": 62
            }
        """
        try:
            stats = review_queue.get_stats()
            return jsonify(stats), 200

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return jsonify({'error': str(e)}), 500

    # ===================== Task Details =====================

    @review_bp.route('/<review_id>', methods=['GET'])
    @require_auth
    def get_task(review_id: str):
        """
        Get specific review task with full context

        Returns task with side-by-side OCR and enriched data for comparison

        Returns:
            {
                "_id": "review_abc123",
                "document_id": "doc_456",
                "enrichment_job_id": "enrich_job_123",
                "reason": "completeness_below_threshold",
                "missing_fields": [...],
                "low_confidence_fields": [...],
                "ocr_data": {
                    "text": "Full OCR text...",
                    "confidence": 0.92,
                    ...
                },
                "enriched_data": {
                    "metadata": {...},
                    "document": {...},
                    "content": {...},
                    "analysis": {...}
                },
                "quality_metrics": {
                    "completeness_score": 0.87,
                    ...
                },
                "status": "pending",
                "created_at": "2025-01-17T12:00:00Z"
            }
        """
        try:
            task = review_queue.get_task(review_id)

            if not task:
                return jsonify({'error': 'Task not found'}), 404

            return jsonify(_serialize_task(task, include_details=True)), 200

        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return jsonify({'error': str(e)}), 500

    @review_bp.route('/<review_id>/history', methods=['GET'])
    @require_auth
    def get_document_history(review_id: str):
        """
        Get review history for a document

        Returns:
            {
                "document_id": "doc_456",
                "history": [
                    {
                        "_id": "review_abc123",
                        "status": "rejected",
                        "completed_at": "2025-01-17T13:00:00Z",
                        "reason": "User rejected",
                        ...
                    },
                    ...
                ]
            }
        """
        try:
            task = review_queue.get_task(review_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404

            document_id = task['document_id']
            history = review_queue.get_document_review_history(document_id)

            return jsonify({
                'document_id': document_id,
                'history': [_serialize_task(t) for t in history]
            }), 200

        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return jsonify({'error': str(e)}), 500

    # ===================== Task Actions =====================

    @review_bp.route('/<review_id>/assign', methods=['POST'])
    @require_auth
    def assign_task(review_id: str):
        """
        Assign task to current reviewer

        Request body:
            {
                "reviewer_id": "user_123"
            }

        Returns:
            {
                "success": true,
                "message": "Task assigned",
                "task": {...}
            }
        """
        try:
            data = request.get_json() or {}
            reviewer_id = data.get('reviewer_id') or request.headers.get('X-User-ID')

            if not reviewer_id:
                return jsonify({'error': 'reviewer_id required'}), 400

            success = review_queue.assign_task(review_id, reviewer_id)

            if success:
                task = review_queue.get_task(review_id)
                return jsonify({
                    'success': True,
                    'message': 'Task assigned',
                    'task': _serialize_task(task)
                }), 200
            else:
                return jsonify({'error': 'Failed to assign task'}), 500

        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            return jsonify({'error': str(e)}), 500

    @review_bp.route('/<review_id>/approve', methods=['POST'])
    @require_auth
    def approve_task(review_id: str):
        """
        Approve reviewed document

        Request body:
            {
                "reviewer_id": "user_123",
                "reviewer_notes": "Looks good",
                "corrections": {
                    "analysis.keywords": ["meditation", "retreat"]
                }
            }

        Returns:
            {
                "success": true,
                "message": "Document approved",
                "document_id": "doc_456"
            }
        """
        try:
            data = request.get_json() or {}
            reviewer_id = data.get('reviewer_id') or request.headers.get('X-User-ID')
            reviewer_notes = data.get('reviewer_notes', '')
            corrections = data.get('corrections')

            if not reviewer_id:
                return jsonify({'error': 'reviewer_id required'}), 400

            task = review_queue.get_task(review_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404

            # Merge corrections with enriched data if provided
            if corrections:
                enriched_data = task.get('enriched_data', {})
                _deep_merge(enriched_data, corrections)
                corrections = enriched_data

            success = review_queue.approve_task(
                review_id,
                reviewer_id,
                reviewer_notes=reviewer_notes,
                corrections=corrections
            )

            if success:
                return jsonify({
                    'success': True,
                    'message': 'Document approved',
                    'document_id': task['document_id']
                }), 200
            else:
                return jsonify({'error': 'Failed to approve task'}), 500

        except Exception as e:
            logger.error(f"Error approving task: {e}")
            return jsonify({'error': str(e)}), 500

    @review_bp.route('/<review_id>/reject', methods=['POST'])
    @require_auth
    def reject_task(review_id: str):
        """
        Reject reviewed document

        Request body:
            {
                "reviewer_id": "user_123",
                "reason": "Incomplete entity extraction",
                "reviewer_notes": "Missing key persons"
            }

        Returns:
            {
                "success": true,
                "message": "Document rejected",
                "document_id": "doc_456"
            }
        """
        try:
            data = request.get_json() or {}
            reviewer_id = data.get('reviewer_id') or request.headers.get('X-User-ID')
            reason = data.get('reason', 'User rejected')
            reviewer_notes = data.get('reviewer_notes', '')

            if not reviewer_id:
                return jsonify({'error': 'reviewer_id required'}), 400

            task = review_queue.get_task(review_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404

            success = review_queue.reject_task(
                review_id,
                reviewer_id,
                reason=reason,
                reviewer_notes=reviewer_notes
            )

            if success:
                return jsonify({
                    'success': True,
                    'message': 'Document rejected',
                    'document_id': task['document_id']
                }), 200
            else:
                return jsonify({'error': 'Failed to reject task'}), 500

        except Exception as e:
            logger.error(f"Error rejecting task: {e}")
            return jsonify({'error': str(e)}), 500

    # ===================== Utilities =====================

    def _serialize_task(task: Dict[str, Any], include_details: bool = False) -> Dict[str, Any]:
        """Serialize review task for JSON response"""
        if not task:
            return {}

        serialized = {
            '_id': task.get('_id'),
            'document_id': task.get('document_id'),
            'enrichment_job_id': task.get('enrichment_job_id'),
            'reason': task.get('reason'),
            'status': task.get('status'),
            'created_at': task.get('created_at').isoformat() if task.get('created_at') else None,
            'updated_at': task.get('updated_at').isoformat() if task.get('updated_at') else None,
            'missing_fields': task.get('missing_fields', []),
            'low_confidence_fields': task.get('low_confidence_fields', []),
            'assigned_to': task.get('assigned_to'),
            'reviewer_notes': task.get('reviewer_notes', '')
        }

        if include_details:
            serialized.update({
                'ocr_data': task.get('ocr_data', {}),
                'enriched_data': task.get('enriched_data', {}),
                'quality_metrics': task.get('quality_metrics', {}),
                'corrections': task.get('corrections', {})
            })

        return serialized

    def _deep_merge(target: Dict, source: Dict) -> None:
        """Deep merge source dict into target dict"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                _deep_merge(target[key], value)
            else:
                target[key] = value

    return review_bp


# Standalone Flask app for development/testing
def create_review_app(db=None):
    """Create standalone Flask app with review API"""
    app = Flask(__name__)
    review_bp = create_review_api(app, db)
    app.register_blueprint(review_bp)

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'healthy'}), 200

    return app


if __name__ == '__main__':
    # Test server
    import os
    from pymongo import MongoClient

    logging.basicConfig(level=logging.INFO)

    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/gvpocr')
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client['gvpocr']

    app = create_review_app(db)
    app.run(host='0.0.0.0', port=5001, debug=True)
