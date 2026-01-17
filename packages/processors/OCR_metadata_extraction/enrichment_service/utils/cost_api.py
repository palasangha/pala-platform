"""
Cost API - REST endpoints for cost tracking, budgeting, and reporting

Provides monitoring dashboard with real-time cost information
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import Blueprint, jsonify, request
from functools import wraps

from enrichment_service.utils.cost_tracker import CostTracker
from enrichment_service.utils.budget_manager import BudgetManager
from enrichment_service.utils.cost_reporter import CostReporter

logger = logging.getLogger(__name__)


def create_cost_api(app, db=None) -> Blueprint:
    """
    Create cost API blueprint

    Args:
        app: Flask application instance
        db: MongoDB database instance

    Returns:
        Blueprint with cost endpoints
    """
    cost_bp = Blueprint('cost', __name__, url_prefix='/api/cost')

    # Initialize cost tracking components
    cost_tracker = CostTracker(db)
    budget_manager = BudgetManager(db)
    cost_reporter = CostReporter(db)

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

    # ===================== Budget Endpoints =====================

    @cost_bp.route('/budget/daily', methods=['GET'])
    @require_auth
    def get_daily_budget():
        """
        Get daily budget status

        Returns:
            {
                "budget_usd": 100.00,
                "spent_usd": 45.32,
                "remaining_usd": 54.68,
                "percentage_used": 45.3,
                "alert": null,
                "breakdown": {...}
            }
        """
        try:
            budget = budget_manager.check_budget('daily')
            return jsonify(budget), 200
        except Exception as e:
            logger.error(f"Error getting daily budget: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/budget/monthly', methods=['GET'])
    @require_auth
    def get_monthly_budget():
        """Get monthly budget status"""
        try:
            budget = budget_manager.check_budget('monthly')
            return jsonify(budget), 200
        except Exception as e:
            logger.error(f"Error getting monthly budget: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/budget/status', methods=['GET'])
    @require_auth
    def get_budget_status():
        """
        Get combined daily/monthly budget status

        Returns:
            {
                "daily": {...},
                "monthly": {...},
                "can_process": true,
                "recommendations": [...]
            }
        """
        try:
            daily = budget_manager.check_budget('daily')
            monthly = budget_manager.check_budget('monthly')
            can_process, reason = budget_manager.can_process_document()
            recommendations = budget_manager.get_recommendations()

            return jsonify({
                'daily': daily,
                'monthly': monthly,
                'can_process': can_process,
                'process_reason_if_not': reason,
                'recommendations': recommendations.get('actions', []),
                'status': recommendations.get('daily_status')
            }), 200
        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            return jsonify({'error': str(e)}), 500

    # ===================== Cost Estimation Endpoints =====================

    @cost_bp.route('/estimate/task', methods=['POST'])
    @require_auth
    def estimate_task_cost():
        """
        Estimate cost for single task

        Request body:
            {"task_name": "generate_summary"}

        Returns:
            {
                "task_name": "generate_summary",
                "estimated_usd": 0.045,
                "model": "claude-sonnet-4"
            }
        """
        try:
            data = request.get_json() or {}
            task_name = data.get('task_name')

            if not task_name:
                return jsonify({'error': 'task_name required'}), 400

            estimate = cost_tracker.estimate_task_cost(task_name)
            return jsonify(estimate), 200

        except Exception as e:
            logger.error(f"Error estimating task cost: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/estimate/document', methods=['POST'])
    @require_auth
    def estimate_document_cost():
        """
        Estimate cost for enriching one document

        Request body:
            {
                "doc_length_chars": 2000,
                "enable_context_agent": true
            }

        Returns:
            {
                "total_usd": 0.32,
                "phase1_ollama": 0.0,
                "phase2_sonnet": 0.045,
                "phase3_opus": 0.275
            }
        """
        try:
            data = request.get_json() or {}
            doc_length = data.get('doc_length_chars', 2000)
            enable_context = data.get('enable_context_agent', True)

            estimate = cost_tracker.estimate_document_cost(doc_length, enable_context)
            return jsonify(estimate), 200

        except Exception as e:
            logger.error(f"Error estimating document cost: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/estimate/collection', methods=['POST'])
    @require_auth
    def estimate_collection_cost():
        """
        Estimate cost for enriching collection

        Request body:
            {
                "num_documents": 100,
                "avg_doc_length": 2000,
                "enable_context_agent": true
            }

        Returns:
            {
                "num_documents": 100,
                "cost_per_document": 0.32,
                "total_cost_usd": 32.0
            }
        """
        try:
            data = request.get_json() or {}
            num_docs = data.get('num_documents', 100)
            avg_length = data.get('avg_doc_length', 2000)
            enable_context = data.get('enable_context_agent', True)

            estimate = cost_tracker.estimate_collection_cost(num_docs, avg_length, enable_context)
            return jsonify(estimate), 200

        except Exception as e:
            logger.error(f"Error estimating collection cost: {e}")
            return jsonify({'error': str(e)}), 500

    # ===================== Cost Analysis Endpoints =====================

    @cost_bp.route('/job/<enrichment_job_id>', methods=['GET'])
    @require_auth
    def get_job_costs(enrichment_job_id: str):
        """
        Get actual costs for enrichment job

        Returns:
            {
                "enrichment_job_id": "enrich_abc123",
                "total_cost_usd": 15.23,
                "num_documents": 50,
                "cost_per_document": 0.305,
                "breakdown_by_model": {...}
            }
        """
        try:
            costs = cost_tracker.get_job_costs(enrichment_job_id)
            if not costs:
                return jsonify({'error': 'Job not found'}), 404
            return jsonify(costs), 200
        except Exception as e:
            logger.error(f"Error getting job costs: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/document/<document_id>', methods=['GET'])
    @require_auth
    def get_document_costs(document_id: str):
        """
        Get costs for enriching single document

        Returns:
            {
                "document_id": "doc_456",
                "total_cost_usd": 0.32,
                "breakdown_by_task": {...},
                "api_calls": 12
            }
        """
        try:
            costs = cost_tracker.get_document_costs(document_id)
            if not costs or 'document_id' not in costs:
                return jsonify({'error': 'Document not found'}), 404
            return jsonify(costs), 200
        except Exception as e:
            logger.error(f"Error getting document costs: {e}")
            return jsonify({'error': str(e)}), 500

    # ===================== Report Endpoints =====================

    @cost_bp.route('/report/job/<enrichment_job_id>', methods=['GET'])
    @require_auth
    def report_job(enrichment_job_id: str):
        """Get detailed cost report for job"""
        try:
            summary = cost_reporter.get_enrichment_summary(enrichment_job_id)
            if 'error' in summary:
                return jsonify(summary), 404
            return jsonify(summary), 200
        except Exception as e:
            logger.error(f"Error generating job report: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/report/models', methods=['GET'])
    @require_auth
    def report_models():
        """
        Get model usage analysis

        Query params:
        - days: Number of days to analyze (default: 30)

        Returns:
            {
                "by_model": {...},
                "total_cost": 123.45
            }
        """
        try:
            days = int(request.args.get('days', 30))
            start_date = datetime.utcnow() - timedelta(days=days)
            analysis = cost_reporter.get_model_analysis(start_date)
            return jsonify(analysis), 200
        except Exception as e:
            logger.error(f"Error generating model report: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/report/trends', methods=['GET'])
    @require_auth
    def report_trends():
        """
        Get cost trends over time

        Query params:
        - days: Number of days to analyze (default: 30)

        Returns:
            {
                "daily_trends": [...],
                "statistics": {...}
            }
        """
        try:
            days = int(request.args.get('days', 30))
            trends = cost_reporter.get_cost_trends(days)
            return jsonify(trends), 200
        except Exception as e:
            logger.error(f"Error generating trends report: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/report/opportunities', methods=['GET'])
    @require_auth
    def report_opportunities():
        """
        Get cost optimization opportunities

        Returns:
            [
                {
                    "type": "model_usage",
                    "severity": "medium",
                    "title": "High Claude Opus usage",
                    "potential_savings": 50.0
                }
            ]
        """
        try:
            opportunities = cost_reporter.get_optimization_opportunities()
            return jsonify({'opportunities': opportunities}), 200
        except Exception as e:
            logger.error(f"Error generating opportunities report: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/report/full', methods=['GET'])
    @require_auth
    def report_full():
        """
        Get comprehensive cost report as text

        Query params:
        - enrichment_job_id: Optional specific job to report on

        Returns:
            {
                "report": "formatted report text"
            }
        """
        try:
            job_id = request.args.get('enrichment_job_id')
            report_text = cost_reporter.generate_report(job_id)
            return jsonify({'report': report_text}), 200
        except Exception as e:
            logger.error(f"Error generating full report: {e}")
            return jsonify({'error': str(e)}), 500

    # ===================== Configuration Endpoints =====================

    @cost_bp.route('/config', methods=['GET'])
    @require_auth
    def get_config():
        """
        Get current cost configuration

        Returns:
            {
                "max_cost_per_doc": 0.50,
                "daily_budget": 100.00,
                "monthly_budget": 2000.00
            }
        """
        try:
            config = budget_manager.config
            return jsonify({
                'max_cost_per_doc': config.get('MAX_COST_PER_DOC'),
                'daily_budget': config.get('DAILY_BUDGET_USD'),
                'monthly_budget': config.get('MONTHLY_BUDGET_USD'),
                'cost_alert_threshold': config.get('COST_ALERT_THRESHOLD')
            }), 200
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return jsonify({'error': str(e)}), 500

    @cost_bp.route('/recommendations', methods=['GET'])
    @require_auth
    def get_recommendations():
        """
        Get cost optimization recommendations

        Returns:
            {
                "daily_status": "WARNING",
                "monthly_status": "OK",
                "actions": [...]
            }
        """
        try:
            recommendations = budget_manager.get_recommendations()
            return jsonify(recommendations), 200
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return jsonify({'error': str(e)}), 500

    return cost_bp


# Standalone Flask app for development/testing
def create_cost_app(db=None):
    """Create standalone Flask app with cost API"""
    from flask import Flask
    app = Flask(__name__)
    cost_bp = create_cost_api(app, db)
    app.register_blueprint(cost_bp)

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

    app = create_cost_app(db)
    app.run(host='0.0.0.0', port=5002, debug=True)
