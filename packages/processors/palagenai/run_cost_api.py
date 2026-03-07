#!/usr/bin/env python3
"""
Cost API - HTTP API for cost tracking and budget monitoring

Provides REST endpoints for:
- Per-document cost breakdown
- Per-enrichment-job costs
- Daily and monthly budget status
- Cost estimates for collections
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enrichment_service.utils.cost_tracker import CostTracker
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
        service_name='cost-api',
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

    # Initialize cost tracker
    cost_tracker = CostTracker(db)

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        try:
            mongo_client.admin.command('ping')
            return jsonify({
                'status': 'healthy',
                'service': 'cost-api',
                'db': 'connected'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 503

    # Task cost estimation
    @app.route('/api/costs/task/<task_name>', methods=['GET'])
    def estimate_task_cost(task_name: str):
        """Estimate cost for a specific task"""
        try:
            cost = cost_tracker.estimate_task_cost(task_name)

            return jsonify({
                'status': 'success',
                'task': task_name,
                'estimate': cost
            }), 200

        except Exception as e:
            logger.error(f"Error estimating task cost: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Document cost estimation
    @app.route('/api/costs/document-estimate', methods=['POST'])
    def estimate_document_cost():
        """Estimate cost for enriching a document"""
        try:
            doc_length = request.json.get('doc_length_chars', 2000) if request.json else 2000
            enable_context_agent = request.json.get('enable_context_agent', True) if request.json else True

            cost = cost_tracker.estimate_document_cost(
                doc_length_chars=doc_length,
                enable_context_agent=enable_context_agent
            )

            return jsonify({
                'status': 'success',
                'estimate': cost
            }), 200

        except Exception as e:
            logger.error(f"Error estimating document cost: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Collection cost estimation
    @app.route('/api/costs/collection-estimate', methods=['POST'])
    def estimate_collection_cost():
        """Estimate cost for enriching a collection"""
        try:
            num_documents = request.json.get('num_documents', 100) if request.json else 100
            avg_doc_length = request.json.get('avg_doc_length', 2000) if request.json else 2000
            enable_context_agent = request.json.get('enable_context_agent', True) if request.json else True

            cost = cost_tracker.estimate_collection_cost(
                num_documents=num_documents,
                avg_doc_length=avg_doc_length,
                enable_context_agent=enable_context_agent
            )

            return jsonify({
                'status': 'success',
                'estimate': cost
            }), 200

        except Exception as e:
            logger.error(f"Error estimating collection cost: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Document costs (actual)
    @app.route('/api/costs/document/<document_id>', methods=['GET'])
    def get_document_costs(document_id: str):
        """Get actual costs for enriching a document"""
        try:
            costs = cost_tracker.get_document_costs(document_id)

            return jsonify({
                'status': 'success',
                'document_id': document_id,
                'costs': costs
            }), 200

        except Exception as e:
            logger.error(f"Error getting document costs: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Job costs (actual)
    @app.route('/api/costs/job/<job_id>', methods=['GET'])
    def get_job_costs(job_id: str):
        """Get actual costs for an enrichment job"""
        try:
            costs = cost_tracker.get_job_costs(job_id)

            return jsonify({
                'status': 'success',
                'job_id': job_id,
                'costs': costs
            }), 200

        except Exception as e:
            logger.error(f"Error getting job costs: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Daily costs
    @app.route('/api/costs/daily', methods=['GET'])
    def get_daily_costs():
        """Get costs for a specific day"""
        try:
            date_str = request.args.get('date', None, type=str)

            if date_str:
                date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            else:
                date = None

            costs = cost_tracker.get_daily_costs(date)

            return jsonify({
                'status': 'success',
                'costs': costs
            }), 200

        except Exception as e:
            logger.error(f"Error getting daily costs: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Budget check
    @app.route('/api/costs/budget/<time_period>', methods=['GET'])
    def check_budget(time_period: str):
        """Check budget status for daily or monthly period"""
        try:
            if time_period not in ['daily', 'monthly']:
                return jsonify({
                    'status': 'error',
                    'error': 'time_period must be "daily" or "monthly"'
                }), 400

            budget = cost_tracker.check_budget(time_period=time_period)

            return jsonify({
                'status': 'success',
                'budget': budget
            }), 200

        except Exception as e:
            logger.error(f"Error checking budget: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Cost summary
    @app.route('/api/costs/summary', methods=['GET'])
    def get_summary():
        """Get comprehensive cost summary"""
        try:
            daily_budget = cost_tracker.check_budget(time_period='daily')
            monthly_budget = cost_tracker.check_budget(time_period='monthly')

            return jsonify({
                'status': 'success',
                'summary': {
                    'daily': daily_budget,
                    'monthly': monthly_budget,
                    'pricing_info': {
                        'claude_opus_4_5': cost_tracker.PRICING['claude-opus-4-5'],
                        'claude_sonnet_4': cost_tracker.PRICING['claude-sonnet-4'],
                        'claude_haiku_4': cost_tracker.PRICING['claude-haiku-4'],
                        'ollama': 'Free (local)'
                    }
                }
            }), 200

        except Exception as e:
            logger.error(f"Error getting summary: {e}", exc_info=True)
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
        description='Cost API - HTTP API for cost tracking and budget monitoring'
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
        default=5002,
        help='Port to listen on (default: 5002)'
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
            logger.info(f"Starting Cost API (production) on {args.host}:{args.port}")
            serve(app, host=args.host, port=args.port, threads=args.threads)
        except ImportError:
            logger.warning("waitress not available, using Flask development server")
            app.run(host=args.host, port=args.port, debug=False)
    else:
        logger.info(f"Starting Cost API (development) on {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
