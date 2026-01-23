from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.models import mongo
from app.models.user import User
from app.models.image import Image
from app.models.audit_log import AuditLog
from app.models.role import Role
from app.utils.decorators import token_required, require_admin
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


# ============================================================================
# DASHBOARD OVERVIEW (ADMIN ONLY)
# ============================================================================

@dashboard_bp.route('/overview', methods=['GET'])
@token_required
@require_admin
def get_dashboard_overview(current_user_id):
    """Get dashboard overview with KPIs and statistics"""
    try:
        project_id = request.args.get('project_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        # Build query
        query = {}
        if project_id:
            query['project_id'] = ObjectId(project_id)

        if date_from or date_to:
            date_query = {}
            try:
                if date_from:
                    date_query['$gte'] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                if date_to:
                    date_query['$lte'] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                return jsonify({
                    'error': 'Invalid date format',
                    'expected_format': 'ISO 8601 (e.g., 2026-01-22 or 2026-01-22T10:00:00Z)',
                    'example': datetime.utcnow().isoformat()
                }), 400
            if date_query:
                query['created_at'] = date_query

        # Count documents by status
        status_counts = {}
        for status in Image.VALID_STATUSES:
            count = mongo.db.images.count_documents({**query, 'document_status': status})
            status_counts[status] = count

        # Total documents
        total_documents = mongo.db.images.count_documents(query)

        # Calculate progress
        classified = status_counts.get(Image.STATUS_CLASSIFIED, 0)
        ocr_processed = status_counts.get(Image.STATUS_OCR_PROCESSED, 0)
        reviewed = status_counts.get(Image.STATUS_REVIEWED_APPROVED, 0)
        exported = status_counts.get(Image.STATUS_EXPORTED, 0)

        # Identify bottleneck
        in_review = status_counts.get(Image.STATUS_IN_REVIEW, 0)
        pending_classification = status_counts.get(Image.STATUS_CLASSIFICATION_PENDING, 0)

        bottleneck_stage = None
        bottleneck_count = 0

        if in_review > bottleneck_count:
            bottleneck_stage = Image.STATUS_IN_REVIEW
            bottleneck_count = in_review

        if pending_classification > bottleneck_count:
            bottleneck_stage = Image.STATUS_CLASSIFICATION_PENDING
            bottleneck_count = pending_classification

        # Calculate progress percentage
        progress_percentage = 0
        if total_documents > 0:
            progress_percentage = round((reviewed + exported) / total_documents * 100, 2)

        return jsonify({
            'status': 'success',
            'overview': {
                'total_documents': total_documents,
                'classification_pending': status_counts.get(Image.STATUS_CLASSIFICATION_PENDING, 0),
                'classified': classified,
                'ocr_processing': status_counts.get(Image.STATUS_OCR_PROCESSING, 0),
                'ocr_processed': ocr_processed,
                'in_review': in_review,
                'approved': reviewed,
                'exported': exported,
                'progress_percentage': progress_percentage
            },
            'status_breakdown': status_counts,
            'bottleneck': {
                'stage': bottleneck_stage,
                'count': bottleneck_count,
                'recommendation': get_bottleneck_recommendation(bottleneck_stage)
            }
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, 'DASHBOARD_ERROR',
                       details={'error': str(e), 'error_type': type(e).__name__,
                               'endpoint': '/dashboard/overview'})
        return jsonify({'error': 'Failed to load dashboard', 'details': str(e)}), 500


# ============================================================================
# USER METRICS (ADMIN ONLY)
# ============================================================================

@dashboard_bp.route('/user-metrics', methods=['GET'])
@token_required
@require_admin
def get_user_metrics(current_user_id):
    """Get user performance metrics"""
    try:
        user_id_filter = request.args.get('user_id')
        role = request.args.get('role')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        # Build query for audit logs
        query = {
            'action_type': {
                '$in': [
                    AuditLog.ACTION_APPROVE_DOCUMENT,
                    AuditLog.ACTION_REJECT_DOCUMENT,
                    AuditLog.ACTION_CLAIM_DOCUMENT
                ]
            }
        }

        if user_id_filter:
            query['user_id'] = ObjectId(user_id_filter)

        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query['$gte'] = datetime.fromisoformat(date_from)
            if date_to:
                date_query['$lte'] = datetime.fromisoformat(date_to)
            if date_query:
                query['created_at'] = date_query

        # Get audit logs
        audit_logs = list(mongo.db.audit_logs.find(query))

        # Group by user and calculate metrics
        user_metrics = {}

        for log in audit_logs:
            user_id = str(log.get('user_id', 'system'))

            if user_id not in user_metrics:
                user_doc = User.find_by_id(mongo, user_id) if user_id != 'system' else None
                user_metrics[user_id] = {
                    'user_id': user_id,
                    'name': user_doc.get('name') if user_doc else 'System',
                    'roles': user_doc.get('roles', []) if user_doc else [],
                    'documents_processed': 0,
                    'approved': 0,
                    'rejected': 0,
                    'claimed': 0,
                    'approval_rate': 0.0,
                    'actions': []
                }

            metrics = user_metrics[user_id]
            action_type = log.get('action_type')

            if action_type == AuditLog.ACTION_APPROVE_DOCUMENT:
                metrics['approved'] += 1
                metrics['documents_processed'] += 1
            elif action_type == AuditLog.ACTION_REJECT_DOCUMENT:
                metrics['rejected'] += 1
                metrics['documents_processed'] += 1
            elif action_type == AuditLog.ACTION_CLAIM_DOCUMENT:
                metrics['claimed'] += 1

            metrics['actions'].append({
                'action': action_type,
                'timestamp': log.get('created_at').isoformat() if log.get('created_at') else None
            })

        # Calculate approval rates
        for user_id, metrics in user_metrics.items():
            if metrics['documents_processed'] > 0:
                metrics['approval_rate'] = round(
                    metrics['approved'] / metrics['documents_processed'], 2
                )

            # Remove action list for summary view
            metrics.pop('actions', None)

        # Filter by role if specified
        if role:
            user_metrics = {
                uid: m for uid, m in user_metrics.items()
                if role in m.get('roles', [])
            }

        # Convert to list and sort by documents_processed
        metrics_list = sorted(
            user_metrics.values(),
            key=lambda x: x['documents_processed'],
            reverse=True
        )

        return jsonify({
            'status': 'success',
            'metrics': metrics_list,
            'summary': {
                'total_users': len(metrics_list),
                'total_documents_processed': sum(m['documents_processed'] for m in metrics_list),
                'avg_approval_rate': round(
                    sum(m['approval_rate'] for m in metrics_list) / len(metrics_list) if metrics_list else 0,
                    2
                )
            }
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, 'DASHBOARD_ERROR',
                       details={'error': str(e), 'error_type': type(e).__name__,
                               'endpoint': '/dashboard/user-metrics'})
        return jsonify({'error': 'Failed to load user metrics', 'details': str(e)}), 500


# ============================================================================
# QUALITY METRICS (ADMIN ONLY)
# ============================================================================

@dashboard_bp.route('/quality-metrics', methods=['GET'])
@token_required
@require_admin
def get_quality_metrics(current_user_id):
    """Get OCR and enrichment quality metrics"""
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        # Build query
        query = {}
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query['$gte'] = datetime.fromisoformat(date_from)
            if date_to:
                date_query['$lte'] = datetime.fromisoformat(date_to)
            if date_query:
                query['created_at'] = date_query

        # OCR quality metrics
        total_ocr = mongo.db.images.count_documents({
            **query,
            'ocr_status': {'$in': ['completed', 'failed']}
        })

        failed_ocr = mongo.db.images.count_documents({
            **query,
            'ocr_status': 'failed'
        })

        ocr_success_rate = 0
        if total_ocr > 0:
            ocr_success_rate = round((total_ocr - failed_ocr) / total_ocr, 2)

        # Classification quality metrics
        total_classified = mongo.db.images.count_documents({
            **query,
            'classification': {'$ne': None}
        })

        public_count = mongo.db.images.count_documents({
            **query,
            'classification': Image.CLASSIFICATION_PUBLIC
        })

        private_count = mongo.db.images.count_documents({
            **query,
            'classification': Image.CLASSIFICATION_PRIVATE
        })

        # Review quality metrics
        total_reviewed = mongo.db.images.count_documents({
            **query,
            'review_status': 'approved'
        })

        total_rejected = mongo.db.images.count_documents({
            **query,
            'review_status': 'rejected'
        })

        manual_edits_count = mongo.db.images.count_documents({
            **query,
            'manual_edits': {'$exists': True, '$ne': []}
        })

        return jsonify({
            'status': 'success',
            'ocr_metrics': {
                'total_processed': total_ocr,
                'failed': failed_ocr,
                'success_rate': ocr_success_rate,
                'failure_rate': round(1 - ocr_success_rate, 2)
            },
            'classification_metrics': {
                'total_classified': total_classified,
                'public_count': public_count,
                'private_count': private_count,
                'public_percentage': round(public_count / total_classified * 100, 2) if total_classified > 0 else 0,
                'private_percentage': round(private_count / total_classified * 100, 2) if total_classified > 0 else 0
            },
            'review_metrics': {
                'total_approved': total_reviewed,
                'total_rejected': total_rejected,
                'documents_with_edits': manual_edits_count,
                'approval_rate': round(total_reviewed / (total_reviewed + total_rejected) * 100, 2) if (total_reviewed + total_rejected) > 0 else 0
            }
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, 'DASHBOARD_ERROR',
                       details={'error': str(e), 'error_type': type(e).__name__,
                               'endpoint': '/dashboard/quality-metrics'})
        return jsonify({'error': 'Failed to load quality metrics', 'details': str(e)}), 500


# ============================================================================
# SLA METRICS (ADMIN ONLY)
# ============================================================================

@dashboard_bp.route('/sla-metrics', methods=['GET'])
@token_required
@require_admin
def get_sla_metrics(current_user_id):
    """Get SLA compliance metrics"""
    try:
        # SLA targets (in hours)
        sla_targets = {
            'classification': 2,      # 2 hours to classify
            'ocr_processing': 6,      # 6 hours for OCR
            'review': 24,             # 24 hours for review
            'total_processing': 48    # 48 hours total
        }

        # Get recent documents
        recent_docs = list(mongo.db.images.find({
            'created_at': {'$gte': datetime.utcnow() - timedelta(days=7)}
        }))

        # Calculate SLA metrics
        classification_times = []
        ocr_times = []
        review_times = []

        for doc in recent_docs:
            # Classification time
            if doc.get('classified_at') and doc.get('created_at'):
                class_time = (doc['classified_at'] - doc['created_at']).total_seconds() / 3600
                classification_times.append(class_time)

            # OCR time
            if doc.get('ocr_processed_at') and doc.get('classified_at'):
                ocr_time = (doc['ocr_processed_at'] - doc['classified_at']).total_seconds() / 3600
                ocr_times.append(ocr_time)

            # Review time
            if doc.get('reviewed_at') and doc.get('ocr_processed_at'):
                review_time = (doc['reviewed_at'] - doc['ocr_processed_at']).total_seconds() / 3600
                review_times.append(review_time)

        # Calculate compliance
        def calculate_compliance(times, sla_hours):
            if not times:
                return 0, 0
            compliant = sum(1 for t in times if t <= sla_hours)
            return round(compliant / len(times) * 100, 2), len(times)

        class_compliance, class_samples = calculate_compliance(classification_times, sla_targets['classification'])
        ocr_compliance, ocr_samples = calculate_compliance(ocr_times, sla_targets['ocr_processing'])
        review_compliance, review_samples = calculate_compliance(review_times, sla_targets['review'])

        return jsonify({
            'status': 'success',
            'sla_metrics': {
                'classification': {
                    'sla_hours': sla_targets['classification'],
                    'compliance_percentage': class_compliance,
                    'samples': class_samples,
                    'avg_time_hours': round(sum(classification_times) / len(classification_times), 2) if classification_times else 0
                },
                'ocr_processing': {
                    'sla_hours': sla_targets['ocr_processing'],
                    'compliance_percentage': ocr_compliance,
                    'samples': ocr_samples,
                    'avg_time_hours': round(sum(ocr_times) / len(ocr_times), 2) if ocr_times else 0
                },
                'review': {
                    'sla_hours': sla_targets['review'],
                    'compliance_percentage': review_compliance,
                    'samples': review_samples,
                    'avg_time_hours': round(sum(review_times) / len(review_times), 2) if review_times else 0
                },
                'overall_compliance': round(
                    (class_compliance + ocr_compliance + review_compliance) / 3, 2
                ) if (class_compliance + ocr_compliance + review_compliance) > 0 else 0
            },
            'summary': {
                'period_days': 7,
                'documents_analyzed': len(recent_docs),
                'sla_target': f"{sla_targets['total_processing']} hours total"
            }
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, 'DASHBOARD_ERROR',
                       details={'error': str(e), 'error_type': type(e).__name__,
                               'endpoint': '/dashboard/sla-metrics'})
        return jsonify({'error': 'Failed to load SLA metrics', 'details': str(e)}), 500


# ============================================================================
# DOCUMENT STATISTICS (ADMIN ONLY)
# ============================================================================

@dashboard_bp.route('/document-statistics', methods=['GET'])
@token_required
@require_admin
def get_document_statistics(current_user_id):
    """Get detailed document statistics"""
    try:
        project_id = request.args.get('project_id')
        classification = request.args.get('classification')

        query = {}
        if project_id:
            query['project_id'] = ObjectId(project_id)
        if classification:
            query['classification'] = classification

        # Count by classification
        classification_stats = list(mongo.db.images.aggregate([
            {'$match': query},
            {'$group': {
                '_id': '$classification',
                'count': {'$sum': 1},
                'avg_processing_time': {'$avg': {'$subtract': ['$updated_at', '$created_at']}}
            }}
        ]))

        # Count by document status
        status_stats = list(mongo.db.images.aggregate([
            {'$match': query},
            {'$group': {
                '_id': '$document_status',
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ]))

        # Count by review status
        review_stats = list(mongo.db.images.aggregate([
            {'$match': query},
            {'$group': {
                '_id': '$review_status',
                'count': {'$sum': 1}
            }}
        ]))

        return jsonify({
            'status': 'success',
            'classification_stats': [
                {
                    'classification': stat['_id'],
                    'count': stat['count'],
                    'avg_processing_time_hours': round(stat.get('avg_processing_time', 0) / (1000 * 3600), 2)
                }
                for stat in classification_stats
            ],
            'status_stats': [
                {
                    'status': stat['_id'],
                    'count': stat['count']
                }
                for stat in status_stats
            ],
            'review_stats': [
                {
                    'status': stat['_id'],
                    'count': stat['count']
                }
                for stat in review_stats
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_bottleneck_recommendation(stage):
    """Get recommendation for bottleneck stage"""
    recommendations = {
        Image.STATUS_CLASSIFICATION_PENDING: 'Increase admin resources for document classification',
        Image.STATUS_OCR_PROCESSING: 'Scale up OCR processing resources or optimize provider settings',
        Image.STATUS_IN_REVIEW: 'Increase reviewer/teacher resources or review queue processing',
        None: 'System operating normally'
    }
    return recommendations.get(stage, 'Check system status')
