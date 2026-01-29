from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.models import mongo
from app.models.user import User
from app.models.image import Image
from app.models.audit_log import AuditLog
from app.models.role import Role
from app.utils.decorators import token_required, require_admin, require_permission
from datetime import datetime

rbac_bp = Blueprint('rbac', __name__, url_prefix='/rbac')


# ============================================================================
# DOCUMENT LIST ENDPOINT
# ============================================================================

@rbac_bp.route('/documents', methods=['GET'])
@token_required
def list_documents(current_user_id):
    """List documents based on user role and permissions"""
    try:
        # Get user to check roles
        user = User.find_by_id(mongo, current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_roles = user.get('roles', [])
        is_admin = 'admin' in user_roles
        is_teacher = 'teacher' in user_roles
        is_reviewer = 'reviewer' in user_roles
        
        # Build query based on role
        query = {}
        
        # Get filters from query params
        status_filter = request.args.get('status')
        classification_filter = request.args.get('classification')
        
        # Apply status filter if provided
        if status_filter:
            query['review_status'] = status_filter
        
        # Apply classification filter if provided
        if classification_filter:
            query['classification'] = classification_filter
        
        # Role-based access control
        if is_reviewer and not (is_admin or is_teacher):
            # Reviewers can only see documents assigned to them
            query['assigned_to'] = current_user_id
        # Teachers and admins can see all documents (no additional filter)
        
        # Get pagination params
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        skip = (page - 1) * per_page
        
        # Fetch documents from ocr_results collection
        documents = list(mongo.db.ocr_results.find(query)
                        .sort('created_at', -1)
                        .skip(skip)
                        .limit(per_page))
        
        # Convert ObjectId to string
        for doc in documents:
            doc['_id'] = str(doc['_id'])
            if 'assigned_to' in doc:
                doc['assigned_to'] = str(doc['assigned_to'])
            if 'assigned_by' in doc:
                doc['assigned_by'] = str(doc['assigned_by'])
            if 'reviewed_by' in doc:
                doc['reviewed_by'] = str(doc['reviewed_by'])
        
        # Get total count
        total = mongo.db.ocr_results.count_documents(query)
        
        return jsonify({
            'documents': documents,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DOCUMENT CLASSIFICATION ENDPOINTS (ADMIN ONLY)
# ============================================================================

@rbac_bp.route('/documents/<doc_id>/classify', methods=['POST'])
@token_required
@require_admin
def classify_document(current_user_id, doc_id):
    """Classify a document (Admin only)"""
    try:
        data = request.get_json()
        classification = data.get('classification')
        reason = data.get('reason', '')

        # Validate classification
        if classification not in Image.VALID_CLASSIFICATIONS:
            return jsonify({
                'error': 'Invalid classification',
                'valid_values': Image.VALID_CLASSIFICATIONS
            }), 400

        # Get document
        image = Image.find_by_id(mongo, doc_id)
        if not image:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLASSIFY_DOCUMENT,
                           resource_type='document', resource_id=doc_id,
                           details={'error': 'Document not found', 'classification': classification})
            return jsonify({'error': 'Document not found'}), 404

        # Check if document is already classified
        if image.get('classification'):
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'error': 'Document already classified', 'current_classification': image.get('classification')})
            return jsonify({
                'error': 'Document already classified',
                'current_classification': image.get('classification')
            }), 409

        # Store previous state
        previous_state = {
            'classification': image.get('classification'),
            'document_status': image.get('document_status')
        }

        # Classify document
        Image.classify(mongo, ObjectId(doc_id), classification, current_user_id, reason)

        # Get updated document
        updated_image = Image.find_by_id(mongo, doc_id)

        # Create audit log
        new_state = {
            'classification': updated_image.get('classification'),
            'document_status': updated_image.get('document_status')
        }
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLASSIFY_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       previous_state=previous_state, new_state=new_state,
                       details={'classification': classification, 'reason': reason})

        return jsonify({
            'status': 'success',
            'message': f'Document classified as {classification}',
            'document': Image.to_dict(updated_image)
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLASSIFY_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       details={'error': str(e)})
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DOCUMENT ASSIGNMENT ENDPOINTS
# ============================================================================

@rbac_bp.route('/documents/<doc_id>/assign', methods=['POST'])
@token_required
def assign_document(current_user_id, doc_id):
    """Assign document to reviewer (Admin/Teacher only)"""
    try:
        # Check user role
        user = User.find_by_id(mongo, current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_roles = user.get('roles', [])
        if 'admin' not in user_roles and 'teacher' not in user_roles:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'action': 'assign_document', 'reason': 'Insufficient permissions'})
            return jsonify({'error': 'Only admins and teachers can assign documents'}), 403
        
        # Get request data
        data = request.get_json()
        reviewer_id = data.get('reviewer_id')
        
        if not reviewer_id:
            return jsonify({'error': 'reviewer_id is required'}), 400
        
        # Verify reviewer exists and has reviewer role
        reviewer = User.find_by_id(mongo, reviewer_id)
        if not reviewer:
            return jsonify({'error': 'Reviewer not found'}), 404
        
        if 'reviewer' not in reviewer.get('roles', []):
            return jsonify({'error': 'User is not a reviewer'}), 400
        
        # Get document from ocr_results
        document = mongo.db.ocr_results.find_one({'_id': ObjectId(doc_id)})
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        # Check if already assigned
        if document.get('review_status') == 'in_review' and document.get('assigned_to'):
            return jsonify({
                'error': 'Document already assigned',
                'assigned_to': str(document.get('assigned_to'))
            }), 409
        
        # Update document
        mongo.db.ocr_results.update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'review_status': 'in_review',
                'assigned_to': reviewer_id,
                'assigned_by': current_user_id,
                'assigned_at': datetime.utcnow()
            }}
        )
        
        # Create audit log
        AuditLog.create(mongo, current_user_id, 'document_assigned',
                       resource_type='document', resource_id=doc_id,
                       details={
                           'assigned_to': reviewer_id,
                           'assigned_to_email': reviewer.get('email'),
                           'assigned_to_name': reviewer.get('name')
                       })
        
        return jsonify({
            'status': 'success',
            'message': 'Document assigned successfully',
            'assigned_to': {
                'id': reviewer_id,
                'email': reviewer.get('email'),
                'name': reviewer.get('name')
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        return jsonify({'error': str(e)}), 500


# ============================================================================
# REVIEW QUEUE ENDPOINTS
# ============================================================================

@rbac_bp.route('/review-queue', methods=['GET'])
@token_required
def get_review_queue(current_user_id):
    """Get review queue (filtered by role)"""
    try:
        # Get pagination params
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        skip = (page - 1) * per_page

        # Get user and their roles
        user = User.find_by_id(mongo, current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_roles = user.get('roles', [])

        # Build query based on role
        # Only show documents in review status
        query = {'review_status': 'in_review'}

        # Reviewer: only see documents assigned to them
        if 'reviewer' in user_roles and 'admin' not in user_roles and 'teacher' not in user_roles:
            query['assigned_to'] = str(current_user_id)
        # Teacher and Admin: see all in_review documents
        elif 'teacher' in user_roles or 'admin' in user_roles:
            pass  # No additional filter
        else:
            return jsonify({'error': 'User does not have review permissions'}), 403

        # Get total count
        total_count = mongo.db.ocr_results.count_documents(query)
        total_pages = (total_count + per_page - 1) // per_page

        # Get documents
        documents = list(mongo.db.ocr_results.find(query)
                        .sort('created_at', -1)
                        .skip(skip)
                        .limit(per_page))

        # Convert ObjectId to string for documents
        for doc in documents:
            doc['_id'] = str(doc['_id'])
            if 'assigned_to' in doc and doc['assigned_to']:
                doc['assigned_to'] = str(doc['assigned_to'])
            if 'assigned_by' in doc and doc['assigned_by']:
                doc['assigned_by'] = str(doc['assigned_by'])
            if 'reviewed_by' in doc and doc['reviewed_by']:
                doc['reviewed_by'] = str(doc['reviewed_by'])

        # Create audit log
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_VIEW_DOCUMENT,
                       details={'queue_items': len(documents), 'roles': user_roles})

        return jsonify({
            'status': 'success',
            'queue': documents,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages
            }
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_VIEW_DOCUMENT,
                       details={'error': str(e), 'error_type': type(e).__name__})
        return jsonify({'error': 'Failed to fetch review queue', 'details': str(e)}), 500


# ============================================================================
# DOCUMENT REVIEW ENDPOINTS
# ============================================================================

@rbac_bp.route('/review/<doc_id>/claim', methods=['POST'])
@token_required
def claim_document(current_user_id, doc_id):
    """Claim a document for review"""
    try:
        # Get user and check permissions
        user = User.find_by_id(mongo, current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_roles = user.get('roles', [])
        has_permission = False
        for role in user_roles:
            if Role.has_permission(mongo, role, Role.PERMISSION_CLAIM_DOCUMENT):
                has_permission = True
                break

        if not has_permission:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'reason': 'No claim permission'})
            return jsonify({'error': 'Permission denied'}), 403

        # Get document
        image = Image.find_by_id(mongo, doc_id)
        if not image:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLAIM_DOCUMENT,
                           resource_type='document', resource_id=doc_id,
                           details={'error': 'Document not found'})
            return jsonify({'error': 'Document not found'}), 404

        # Check classification access
        classification = image.get('classification')
        if classification == Image.CLASSIFICATION_PRIVATE and 'teacher' not in user_roles and 'admin' not in user_roles:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'reason': 'Cannot access PRIVATE documents'})
            return jsonify({'error': 'Cannot access PRIVATE documents'}), 403

        # Check if already claimed
        if image.get('claimed_by'):
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLAIM_DOCUMENT,
                           resource_type='document', resource_id=doc_id,
                           details={'error': 'Document already claimed', 'claimed_by': str(image.get('claimed_by'))})
            return jsonify({
                'error': 'Document already claimed',
                'claimed_by': str(image.get('claimed_by'))
            }), 409

        # Claim document
        result = Image.claim_for_review(mongo, ObjectId(doc_id), current_user_id)

        if result.modified_count == 0:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLAIM_DOCUMENT,
                           resource_type='document', resource_id=doc_id,
                           details={'error': 'MongoDB update failed', 'modified_count': 0})
            return jsonify({'error': 'Failed to claim document'}), 500

        # Get updated document
        updated_image = Image.find_by_id(mongo, doc_id)

        # Create audit log
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLAIM_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       new_state={'claimed_by': str(current_user_id), 'review_status': 'in_review'},
                       details={'claimed_at': datetime.utcnow().isoformat()})

        return jsonify({
            'status': 'success',
            'message': 'Document claimed successfully',
            'document': Image.to_dict(updated_image)
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_CLAIM_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       details={'error': str(e), 'error_type': type(e).__name__})
        return jsonify({'error': 'Failed to claim document', 'details': str(e)}), 500


@rbac_bp.route('/review/<doc_id>/approve', methods=['POST'])
@token_required
def approve_document(current_user_id, doc_id):
    """Approve a reviewed document"""
    try:
        data = request.get_json()
        manual_edits = data.get('edit_fields', {})
        notes = data.get('notes', '')

        # Get user and check permissions
        user = User.find_by_id(mongo, current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_roles = user.get('roles', [])
        has_permission = False
        for role in user_roles:
            if Role.has_permission(mongo, role, Role.PERMISSION_APPROVE_DOCUMENT):
                has_permission = True
                break

        if not has_permission:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'reason': 'No approve permission'})
            return jsonify({'error': 'Permission denied'}), 403

        # Get document
        image = Image.find_by_id(mongo, doc_id)
        if not image:
            return jsonify({'error': 'Document not found'}), 404

        # Check if claimed by current user
        if image.get('claimed_by') != ObjectId(current_user_id):
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'reason': 'Document not claimed by this user', 'claimed_by': str(image.get('claimed_by'))})
            return jsonify({
                'error': 'Document not claimed by you',
                'claimed_by': str(image.get('claimed_by'))
            }), 403

        # Check status
        if image.get('document_status') != Image.STATUS_IN_REVIEW:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'reason': 'Document not in review status', 'status': image.get('document_status')})
            return jsonify({
                'error': 'Document not in review status',
                'status': image.get('document_status')
            }), 409

        # Store previous state
        previous_state = {'review_status': image.get('review_status'), 'document_status': image.get('document_status')}

        # Approve document
        edits_list = [{'field': k, 'value': v} for k, v in manual_edits.items()]
        Image.approve_document(mongo, ObjectId(doc_id), current_user_id, edits_list, notes)

        # Get updated document
        updated_image = Image.find_by_id(mongo, doc_id)

        # Create audit log
        new_state = {'review_status': updated_image.get('review_status'), 'document_status': updated_image.get('document_status')}
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_APPROVE_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       previous_state=previous_state, new_state=new_state,
                       details={'manual_edits': len(edits_list), 'notes': notes})

        return jsonify({
            'status': 'success',
            'message': 'Document approved successfully',
            'document': Image.to_dict(updated_image),
            'edits_count': len(edits_list)
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_APPROVE_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       details={'error': str(e), 'error_type': type(e).__name__})
        return jsonify({'error': 'Failed to approve document', 'details': str(e)}), 500


@rbac_bp.route('/review/<doc_id>/reject', methods=['POST'])
@token_required
def reject_document(current_user_id, doc_id):
    """Reject a reviewed document"""
    try:
        data = request.get_json()
        reason = data.get('reason', '')

        if not reason:
            return jsonify({'error': 'Rejection reason is required'}), 400

        # Get user and check permissions
        user = User.find_by_id(mongo, current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_roles = user.get('roles', [])
        has_permission = False
        for role in user_roles:
            if Role.has_permission(mongo, role, Role.PERMISSION_REJECT_DOCUMENT):
                has_permission = True
                break

        if not has_permission:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'reason': 'No reject permission'})
            return jsonify({'error': 'Permission denied'}), 403

        # Get document
        image = Image.find_by_id(mongo, doc_id)
        if not image:
            return jsonify({'error': 'Document not found'}), 404

        # Check if claimed by current user
        if image.get('claimed_by') != ObjectId(current_user_id):
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           resource_type='document', resource_id=doc_id,
                           details={'reason': 'Document not claimed by this user'})
            return jsonify({'error': 'Document not claimed by you'}), 403

        # Check status
        if image.get('document_status') != Image.STATUS_IN_REVIEW:
            return jsonify({
                'error': 'Document not in review status',
                'status': image.get('document_status')
            }), 409

        # Store previous state
        previous_state = {'review_status': image.get('review_status'), 'claimed_by': str(image.get('claimed_by'))}

        # Reject document
        Image.reject_document(mongo, ObjectId(doc_id), reason)

        # Get updated document
        updated_image = Image.find_by_id(mongo, doc_id)

        # Create audit log
        new_state = {'review_status': updated_image.get('review_status'), 'claimed_by': updated_image.get('claimed_by')}
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_REJECT_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       previous_state=previous_state, new_state=new_state,
                       details={'reason': reason})

        return jsonify({
            'status': 'success',
            'message': 'Document rejected',
            'document': Image.to_dict(updated_image),
            'reason': reason
        }), 200

    except Exception as e:
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_REJECT_DOCUMENT,
                       resource_type='document', resource_id=doc_id,
                       details={'error': str(e), 'error_type': type(e).__name__})
        return jsonify({'error': 'Failed to reject document', 'details': str(e)}), 500


# ============================================================================
# USER ROLE MANAGEMENT ENDPOINTS (ADMIN ONLY)
# ============================================================================

@rbac_bp.route('/users', methods=['GET'])
@token_required
@require_admin
def list_users(current_user_id):
    """List all users"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        skip = (page - 1) * per_page

        # Get total count
        total_count = mongo.db.users.count_documents({})

        # Get users
        users = list(mongo.db.users.find({}).skip(skip).limit(per_page).sort('created_at', -1))

        # Convert to dict
        users_list = []
        for user in users:
            users_list.append({
                'id': str(user['_id']),
                'email': user.get('email'),
                'name': user.get('name'),
                'roles': user.get('roles', []),
                'created_at': user.get('created_at').isoformat() if user.get('created_at') else None
            })

        return jsonify({
            'status': 'success',
            'users': users_list,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rbac_bp.route('/users/<user_id>/roles', methods=['GET'])
@token_required
@require_admin
def get_user_roles(current_user_id, user_id):
    """Get roles for a user"""
    try:
        user = User.find_by_id(mongo, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'roles': user.get('roles', [])
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rbac_bp.route('/users/<user_id>/roles', methods=['POST'])
@token_required
@require_admin
def update_user_roles(current_user_id, user_id):
    """Update roles for a user"""
    try:
        data = request.get_json()
        roles = data.get('roles', [])

        if not roles:
            return jsonify({'error': 'Roles list cannot be empty'}), 400

        # Validate roles
        for role in roles:
            if role not in Role.VALID_ROLES:
                return jsonify({
                    'error': 'Invalid role',
                    'invalid_role': role,
                    'valid_roles': Role.VALID_ROLES
                }), 400

        # Get user
        user = User.find_by_id(mongo, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Store previous roles
        previous_roles = user.get('roles', [])

        # Update roles
        User.set_roles(mongo, user_id, roles)

        # Create audit log
        AuditLog.create(mongo, current_user_id, 'ROLES_UPDATED',
                       resource_type='user', resource_id=user_id,
                       previous_state={'roles': previous_roles},
                       new_state={'roles': roles})

        return jsonify({
            'status': 'success',
            'message': 'Roles updated successfully',
            'user_id': user_id,
            'previous_roles': previous_roles,
            'new_roles': roles
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# AUDIT LOG ENDPOINTS (ADMIN ONLY)
# ============================================================================

@rbac_bp.route('/audit-logs', methods=['GET'])
@token_required
@require_admin
def get_audit_logs(current_user_id):
    """Get audit logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action_type = request.args.get('action_type')
        user_id = request.args.get('user_id')

        skip = (page - 1) * per_page

        # Build query
        query = {}
        if action_type:
            query['action_type'] = action_type
        if user_id:
            query['user_id'] = ObjectId(user_id)

        # Get total count
        total_count = mongo.db.audit_logs.count_documents(query)
        total_pages = (total_count + per_page - 1) // per_page

        # Get logs
        logs = list(mongo.db.audit_logs.find(query)
                   .sort('created_at', -1)
                   .skip(skip)
                   .limit(per_page))

        return jsonify({
            'status': 'success',
            'audit_logs': [AuditLog.to_dict(log) for log in logs],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rbac_bp.route('/audit-logs/document/<doc_id>', methods=['GET'])
@token_required
@require_admin
def get_document_audit_trail(current_user_id, doc_id):
    """Get audit trail for a document"""
    try:
        logs = AuditLog.find_by_resource(mongo, doc_id, skip=0, limit=1000)

        return jsonify({
            'status': 'success',
            'document_id': doc_id,
            'audit_trail': [AuditLog.to_dict(log) for log in logs]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
