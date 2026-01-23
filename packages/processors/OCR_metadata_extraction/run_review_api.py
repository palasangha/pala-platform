#!/usr/bin/env python3
"""
Review API - HTTP API for human review of enriched documents

Provides REST endpoints for:
- Listing documents in review queue
- Getting document details with completeness metrics
- Approving/rejecting documents
- Re-enrichment triggers
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enrichment_service.review.review_queue import ReviewQueue
from enrichment_service.utils.logging_config import setup_logging, get_logger
from enrichment_service.config import config

logger = get_logger(__name__)


def create_app() -> Flask:
    """Create Flask application"""
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False

    # Setup logging
    setup_logging(
        level='INFO',
        service_name='review-api',
        enable_json=True
    )

    # Initialize database
    try:
        mongo_client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        db = mongo_client[config.DB_NAME]
        logger.info("✓ MongoDB connection verified")
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {e}")
        sys.exit(1)

    # Initialize review queue
    review_queue = ReviewQueue(db)

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        try:
            mongo_client.admin.command('ping')
            return jsonify({
                'status': 'healthy',
                'service': 'review-api',
                'db': 'connected'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 503

    # Get review queue
    @app.route('/api/review-queue', methods=['GET'])
    def get_review_queue():
        """Get list of documents in review queue"""
        try:
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('page_size', 20, type=int)
            status = request.args.get('status', 'pending', type=str)

            skip = (page - 1) * page_size

            query = {}
            if status != 'all':
                query['status'] = status

            # Get total count
            total = db.review_queue.count_documents(query)

            # Get documents
            documents = list(
                db.review_queue
                .find(query)
                .skip(skip)
                .limit(page_size)
                .sort('created_at', -1)
            )

            # Convert ObjectIds to strings for JSON serialization
            for doc in documents:
                doc['_id'] = str(doc['_id'])
                doc['enrichment_job_id'] = str(doc.get('enrichment_job_id', ''))
                doc['document_id'] = str(doc.get('document_id', ''))
                doc['created_at'] = doc.get('created_at', '').isoformat() if hasattr(doc.get('created_at'), 'isoformat') else str(doc.get('created_at', ''))

            return jsonify({
                'status': 'success',
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size,
                'documents': documents
            }), 200

        except Exception as e:
            logger.error(f"Error getting review queue: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Get specific document in review
    @app.route('/api/review-queue/<document_id>', methods=['GET'])
    def get_document_review(document_id: str):
        """Get specific document and review details"""
        try:
            review_doc = db.review_queue.find_one({'document_id': document_id})

            if not review_doc:
                return jsonify({
                    'status': 'not_found',
                    'error': f'Document {document_id} not in review queue'
                }), 404

            # Get enriched document
            enriched_doc = db.enriched_documents.find_one({'document_id': document_id})

            # Convert for JSON
            review_doc['_id'] = str(review_doc.get('_id', ''))
            review_doc['enrichment_job_id'] = str(review_doc.get('enrichment_job_id', ''))

            return jsonify({
                'status': 'success',
                'review_record': review_doc,
                'enriched_document': enriched_doc if enriched_doc else {}
            }), 200

        except Exception as e:
            logger.error(f"Error getting document: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Approve document
    @app.route('/api/review-queue/<document_id>/approve', methods=['POST'])
    def approve_document(document_id: str):
        """Approve document from review queue"""
        try:
            reviewer = request.json.get('reviewer', 'api') if request.json else 'api'
            notes = request.json.get('notes', '') if request.json else ''

            result = review_queue.approve_document(
                document_id=document_id,
                reviewer=reviewer,
                notes=notes
            )

            if result:
                logger.info(f"✓ Document {document_id} approved by {reviewer}")
                return jsonify({
                    'status': 'success',
                    'message': f'Document {document_id} approved'
                }), 200
            else:
                return jsonify({
                    'status': 'not_found',
                    'error': f'Document {document_id} not in review queue'
                }), 404

        except Exception as e:
            logger.error(f"Error approving document: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Reject document
    @app.route('/api/review-queue/<document_id>/reject', methods=['POST'])
    def reject_document(document_id: str):
        """Reject document and trigger re-enrichment"""
        try:
            reviewer = request.json.get('reviewer', 'api') if request.json else 'api'
            reason = request.json.get('reason', 'Manual rejection') if request.json else 'Manual rejection'

            result = review_queue.reject_document(
                document_id=document_id,
                reviewer=reviewer,
                reason=reason
            )

            if result:
                logger.info(f"✓ Document {document_id} rejected by {reviewer}: {reason}")
                return jsonify({
                    'status': 'success',
                    'message': f'Document {document_id} rejected'
                }), 200
            else:
                return jsonify({
                    'status': 'not_found',
                    'error': f'Document {document_id} not in review queue'
                }), 404

        except Exception as e:
            logger.error(f"Error rejecting document: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Get statistics
    @app.route('/api/review-queue/stats', methods=['GET'])
    def get_queue_stats():
        """Get review queue statistics"""
        try:
            total_in_review = db.review_queue.count_documents({'status': 'pending'})
            total_approved = db.review_queue.count_documents({'status': 'approved'})
            total_rejected = db.review_queue.count_documents({'status': 'rejected'})

            return jsonify({
                'status': 'success',
                'stats': {
                    'pending': total_in_review,
                    'approved': total_approved,
                    'rejected': total_rejected,
                    'total': total_in_review + total_approved + total_rejected
                }
            }), 200

        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'error': 'Endpoint not found'
        }), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({
            'status': 'error',
            'error': 'Internal server error'
        }), 500

    return app


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Review API - HTTP API for human review of enriched documents'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5001,
        help='Port to listen on (default: 5001)'
    )
    parser.add_argument(
        '--production',
        action='store_true',
        default=False,
        help='Run in production mode (use Gunicorn)'
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=4,
        help='Number of threads for production mode (default: 4)'
    )
    parser.add_argument(
        '--enable-cors',
        action='store_true',
        default=False,
        help='Enable CORS for all origins'
    )
    parser.add_argument(
        '--cors-origins',
        type=str,
        default='http://localhost:3000',
        help='Allowed CORS origins (default: http://localhost:3000)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Create app
    app = create_app()

    # Enable CORS if requested
    if args.enable_cors:
        origins = args.cors_origins.split(',')
        CORS(app, resources={r'/api/*': {'origins': origins}})
        logger.info(f"CORS enabled for origins: {origins}")

    # Run
    if args.production:
        try:
            from waitress import serve
            logger.info(f"Starting Review API (production) on {args.host}:{args.port}")
            serve(app, host=args.host, port=args.port, threads=args.threads)
        except ImportError:
            logger.warning("waitress not available, using Flask development server")
            app.run(host=args.host, port=args.port, debug=False)
    else:
        logger.info(f"Starting Review API (development) on {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
