from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.models import mongo
from app.models.user import User
from app.models.image import Image
from app.models.audit_log import AuditLog
from app.models.role import Role
from app.utils.decorators import token_required, require_admin, require_permission
from datetime import datetime

rbac_bp = Blueprint('rbac', __name__)


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
        search_query = request.args.get('search', '').strip()
        
        # Apply status filter if provided (in_review, approved, rejected)
        if status_filter:
            query['review_status'] = status_filter
        
        # Apply search filter for filename (partial match, case-insensitive)
        if search_query:
            query['original_filename'] = {'$regex': search_query, '$options': 'i'}
        
        # Role-based access control for document classification
        if is_admin:
            # Admin can see ALL documents (public + private)
            pass
        elif is_teacher and not is_admin:
            # Teacher can only see PRIVATE documents
            query['classification'] = 'PRIVATE'
        elif is_reviewer and not (is_admin or is_teacher):
            # Reviewer can only see PUBLIC documents
            query['classification'] = 'PUBLIC'
        else:
            # No valid role - empty result
            return jsonify({
                'documents': [],
                'total': 0,
                'page': 1,
                'per_page': 20,
                'total_pages': 0
            }), 200
        
        # Get pagination params
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        skip = (page - 1) * per_page
        
        # Fetch documents from images collection
        documents = list(mongo.db.images.find(query)
                        .sort('created_at', -1)
                        .skip(skip)
                        .limit(per_page))

        # Convert to dict using Image.to_dict for consistent formatting
        # Also add reviewed_by_role for display purposes
        result_docs = []
        for doc in documents:
            doc_dict = Image.to_dict(doc)
            # Determine reviewer role based on classification
            if doc.get('classification') == 'PUBLIC':
                doc_dict['reviewed_by_role'] = 'Reviewer'
            elif doc.get('classification') == 'PRIVATE':
                doc_dict['reviewed_by_role'] = 'Teacher'
            else:
                doc_dict['reviewed_by_role'] = None
            # Get reviewer user name if available
            if doc.get('reviewed_by'):
                reviewer = User.find_by_id(mongo, doc.get('reviewed_by'))
                if reviewer:
                    doc_dict['reviewed_by_name'] = reviewer.get('name') or reviewer.get('email')
            result_docs.append(doc_dict)

        # Get total count
        total = mongo.db.images.count_documents(query)
        
        return jsonify({
            'documents': result_docs,
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
        
        # Get document from images collection
        document = Image.find_by_id(mongo, doc_id)
        if not document:
            return jsonify({'error': 'Document not found'}), 404

        # Check if already assigned
        if document.get('review_status') == 'in_review' and document.get('assigned_to'):
            return jsonify({
                'error': 'Document already assigned',
                'assigned_to': str(document.get('assigned_to'))
            }), 409

        # Update document
        mongo.db.images.update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'review_status': 'in_review',
                'assigned_to': reviewer_id,
                'assigned_by': current_user_id,
                'assigned_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }}
        )
        
        # Create audit log
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_DOCUMENT_ASSIGNED,
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
        total_count = mongo.db.images.count_documents(query)
        total_pages = (total_count + per_page - 1) // per_page

        # Get documents
        documents = list(mongo.db.images.find(query)
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
        AuditLog.create(mongo, current_user_id, AuditLog.ACTION_ROLES_UPDATED,
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
# AUDIT LOG ENDPOINTS (ROLE-BASED VISIBILITY)
# ============================================================================

@rbac_bp.route('/audit-logs', methods=['GET'])
@token_required
def get_audit_logs(current_user_id):
    """Get audit logs with role-based visibility"""
    try:
        # Get user to check roles
        user = User.find_by_id(mongo, current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_roles = user.get('roles', [])
        is_admin = 'admin' in user_roles
        is_teacher = 'teacher' in user_roles
        is_reviewer = 'reviewer' in user_roles

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action_type = request.args.get('action_type')

        skip = (page - 1) * per_page

        # Build query based on role
        query = {}
        
        if is_admin:
            # Admin sees all logs
            pass
        elif is_reviewer or is_teacher:
            # Reviewer/Teacher sees only their logs
            query['user_id'] = ObjectId(current_user_id)
        else:
            # No valid role - empty result
            return jsonify({
                'status': 'success',
                'audit_logs': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total_count': 0,
                    'total_pages': 0
                }
            }), 200

        if action_type:
            query['action_type'] = action_type

        # Get total count
        total_count = mongo.db.audit_logs.count_documents(query)
        total_pages = (total_count + per_page - 1) // per_page

        # Get logs
        logs = list(mongo.db.audit_logs.find(query)
                   .sort('created_at', -1)
                   .skip(skip)
                   .limit(per_page))

        # Enrich logs with document name and user details
        enriched_logs = []
        for log in logs:
            log_dict = AuditLog.to_dict(log)
            
            # Get document name if resource is a document
            if log.get('resource_type') == 'document' and log.get('resource_id'):
                doc = mongo.db.images.find_one({'_id': log['resource_id']})
                if doc:
                    log_dict['document_name'] = doc.get('original_filename', 'Unknown')
                    log_dict['document_status'] = doc.get('review_status', 'unknown')
            
            # Get user details
            if log.get('user_id'):
                acting_user = User.find_by_id(mongo, log['user_id'])
                if acting_user:
                    log_dict['changed_by_name'] = acting_user.get('name') or acting_user.get('email')
                    log_dict['changed_by_role'] = ', '.join(acting_user.get('roles', []))
            
            enriched_logs.append(log_dict)

        return jsonify({
            'status': 'success',
            'audit_logs': enriched_logs,
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


@rbac_bp.route('/audit-logs/<log_id>/restore', methods=['POST'])
@token_required
@require_admin
def restore_document_version(current_user_id, log_id):
    """Restore a document to a previous version based on audit log entry"""
    try:
        # Find the audit log entry
        log = AuditLog.find_by_id(mongo, log_id)
        if not log:
            return jsonify({'error': 'Audit log entry not found'}), 404
        
        # Check if this log has a previous_state to restore to
        previous_state = log.get('previous_state')
        if not previous_state:
            return jsonify({'error': 'No previous state to restore'}), 400
        
        # Get the document
        doc_id = log.get('resource_id')
        if not doc_id:
            return jsonify({'error': 'No document associated with this log'}), 400
        
        document = Image.find_by_id(mongo, doc_id)
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        # Store current state before restore
        current_state = {
            'classification': document.get('classification'),
            'document_status': document.get('document_status'),
            'review_status': document.get('review_status'),
            'claimed_by': str(document.get('claimed_by')) if document.get('claimed_by') else None,
            'reviewed_by': str(document.get('reviewed_by')) if document.get('reviewed_by') else None
        }
        
        # Build update data from previous_state
        update_data = {'updated_at': datetime.utcnow()}
        for key in ['classification', 'document_status', 'review_status', 'claimed_by', 'reviewed_by']:
            if key in previous_state:
                if key in ['claimed_by', 'reviewed_by'] and previous_state[key]:
                    update_data[key] = ObjectId(previous_state[key])
                else:
                    update_data[key] = previous_state[key]
        
        # Restore the document
        mongo.db.images.update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': update_data}
        )
        
        # Create audit log for the restore action
        AuditLog.create(
            mongo,
            current_user_id,
            AuditLog.ACTION_RESTORE_DOCUMENT,
            resource_type='document',
            resource_id=doc_id,
            previous_state=current_state,
            new_state=previous_state,
            details={
                'restored_from_log_id': str(log_id),
                'restored_by': str(current_user_id)
            }
        )
        
        # Get updated document
        updated_document = Image.find_by_id(mongo, doc_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Document restored to previous version',
            'document': Image.to_dict(updated_document)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

