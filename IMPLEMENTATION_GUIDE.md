# OCR RBAC System - Implementation Guide

**Document Version**: 1.0
**Date**: 2026-01-22
**Status**: Ready for Development

---

## Table of Contents

1. [Pre-Implementation Checklist](#pre-implementation-checklist)
2. [Phase 1: Core RBAC Foundation](#phase-1-core-rbac-foundation)
3. [Phase 2: Classification & OCR Processing](#phase-2-classification--ocr-processing)
4. [Phase 3: Review Workflow](#phase-3-review-workflow)
5. [Phase 4: Approval & Export](#phase-4-approval--export)
6. [Phase 5: Admin Dashboard](#phase-5-admin-dashboard)
7. [Phase 6: Testing & Deployment](#phase-6-testing--deployment)
8. [Database Migrations](#database-migrations)
9. [Configuration Setup](#configuration-setup)
10. [Deployment Checklist](#deployment-checklist)

---

# Pre-Implementation Checklist

## Environment Requirements

- [ ] Python 3.8+
- [ ] Node.js 16+ (for frontend)
- [ ] MongoDB 5.0+
- [ ] Redis 6.0+ (for session/token blacklist)
- [ ] NSQ (for job queue)
- [ ] Docker & Docker Compose

## Dependencies

### Backend (Python)
```
Flask==3.0.0
Flask-PyMongo==2.3.0
PyJWT==2.8.0
Werkzeug==3.0.0
python-dotenv==1.0.0
requests==2.31.0
```

### Frontend (Node.js)
```
react==18.2.0
typescript==5.3.0
vite==5.0.0
axios==1.6.0
zustand==4.4.0
@tanstack/react-query==5.0.0
chakra-ui==2.8.0
tailwind-css==3.4.0
```

## Security Setup

- [ ] Generate JWT secret key (min 32 chars)
- [ ] Setup SSL/TLS certificates
- [ ] Configure CORS origins
- [ ] Setup environment variables (.env)
- [ ] Configure database authentication
- [ ] Setup Google OAuth credentials (if using)

---

# Phase 1: Core RBAC Foundation (Week 1-2)

## Step 1.1: Database Schema Creation

### Create Users Collection

```javascript
// MongoDB: Create indexes for users collection
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ roles: 1 });
db.users.createIndex({ created_at: -1 });
```

**Schema Definition**:
```python
# backend/app/models/user.py

from datetime import datetime
from bson.objectid import ObjectId
from flask_pymongo import ObjectId as PyMongoObjectId

class User:
    @staticmethod
    def create(email, name, password_hash, roles=['reviewer']):
        """Create new user with role"""
        user_doc = {
            '_id': ObjectId(),
            'email': email,
            'name': name,
            'password_hash': password_hash,
            'roles': roles,  # Array of role strings: ['admin', 'reviewer', 'teacher']
            'active': True,
            'security_clearance': 'standard',  # 'standard' or 'elevated' for sensitive content
            'assigned_project_ids': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'last_login': None,
            'created_by': None
        }
        return user_doc

    @staticmethod
    def find_by_email(db, email):
        """Find user by email"""
        return db.users.find_one({'email': email})

    @staticmethod
    def find_by_id(db, user_id):
        """Find user by ID"""
        return db.users.find_one({'_id': ObjectId(user_id)})

    @staticmethod
    def has_permission(db, user_id, permission):
        """Check if user has specific permission"""
        user = User.find_by_id(db, user_id)
        if not user:
            return False

        # Get user roles
        user_roles = user.get('roles', [])

        # Get permissions for each role
        for role_name in user_roles:
            role = db.roles.find_one({'name': role_name})
            if role and permission in role.get('permissions', []):
                return True

        return False
```

### Create Roles Collection

```javascript
// MongoDB: Create roles collection
db.roles.createIndex({ name: 1 }, { unique: true });
```

**Role Definitions**:
```python
# backend/app/models/role.py

class Role:
    @staticmethod
    def init_default_roles(db):
        """Initialize default roles in database"""

        admin_role = {
            '_id': ObjectId(),
            'name': 'admin',
            'description': 'System administrator with full access',
            'permissions': [
                'create_project', 'manage_users', 'classify_document',
                'run_ocr', 'view_all_documents', 'review_document',
                'edit_metadata', 'approve_final', 'export_data',
                'view_dashboards', 'view_audit_logs', 'override_state'
            ],
            'data_access_level': 'all',
            'created_at': datetime.utcnow()
        }

        reviewer_role = {
            '_id': ObjectId(),
            'name': 'reviewer',
            'description': 'OCR Reviewer - reviews public documents only',
            'permissions': [
                'view_public_documents', 'review_document', 'edit_metadata'
            ],
            'data_access_level': 'public_only',
            'created_at': datetime.utcnow()
        }

        teacher_role = {
            '_id': ObjectId(),
            'name': 'teacher',
            'description': 'Senior reviewer - reviews public and private documents',
            'permissions': [
                'view_all_documents', 'review_document', 'edit_metadata'
            ],
            'data_access_level': 'all_review_queue',  # Custom level
            'created_at': datetime.utcnow()
        }

        # Insert roles
        db.roles.insert_many([admin_role, reviewer_role, teacher_role])
        return True
```

## Step 1.2: Authentication Implementation

### JWT Token Generation

```python
# backend/app/services/auth_service.py

import jwt
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

class AuthService:
    JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'your-secret-key-min-32-chars')
    JWT_ALGORITHM = 'HS256'
    ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
    REFRESH_TOKEN_EXPIRY = 30 * 24 * 3600  # 30 days

    @staticmethod
    def hash_password(password):
        """Hash password using Werkzeug"""
        return generate_password_hash(password, method='pbkdf2:sha256')

    @staticmethod
    def verify_password(password_hash, password):
        """Verify password against hash"""
        return check_password_hash(password_hash, password)

    @staticmethod
    def generate_tokens(user_id, email, roles):
        """Generate access and refresh tokens"""
        now = datetime.utcnow()

        # Access token (1 hour)
        access_token_payload = {
            'user_id': str(user_id),
            'email': email,
            'roles': roles,
            'iat': now,
            'exp': now + timedelta(seconds=AuthService.ACCESS_TOKEN_EXPIRY),
            'type': 'access'
        }

        # Refresh token (30 days)
        refresh_token_payload = {
            'user_id': str(user_id),
            'iat': now,
            'exp': now + timedelta(seconds=AuthService.REFRESH_TOKEN_EXPIRY),
            'type': 'refresh'
        }

        access_token = jwt.encode(
            access_token_payload,
            AuthService.JWT_SECRET,
            algorithm=AuthService.JWT_ALGORITHM
        )

        refresh_token = jwt.encode(
            refresh_token_payload,
            AuthService.JWT_SECRET,
            algorithm=AuthService.JWT_ALGORITHM
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': AuthService.ACCESS_TOKEN_EXPIRY,
            'token_type': 'Bearer'
        }

    @staticmethod
    def verify_token(token):
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                AuthService.JWT_SECRET,
                algorithms=[AuthService.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None  # Token expired
        except jwt.InvalidTokenError:
            return None  # Invalid token

    @staticmethod
    def refresh_access_token(refresh_token):
        """Generate new access token using refresh token"""
        payload = AuthService.verify_token(refresh_token)

        if not payload or payload.get('type') != 'refresh':
            return None

        user_id = payload['user_id']
        # Get user from database to get current roles
        # user = User.find_by_id(db, user_id)
        # Return new access token
        # This is simplified - full implementation would fetch user details

        return AuthService.generate_tokens(user_id, 'email', [])['access_token']
```

### Login Endpoint

```python
# backend/app/routes/auth.py

from flask import Blueprint, request, jsonify
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.decorators import token_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user"""
    data = request.get_json()

    # Validate input
    if not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Missing required fields'}), 400

    db = request.app.config['MONGO_DB']

    # Check if user exists
    if User.find_by_email(db, data['email']):
        return jsonify({'error': 'Email already registered'}), 409

    # Create user
    password_hash = AuthService.hash_password(data['password'])
    user_doc = User.create(
        email=data['email'],
        name=data['name'],
        password_hash=password_hash,
        roles=['reviewer']  # Default role
    )

    db.users.insert_one(user_doc)

    # Generate tokens
    tokens = AuthService.generate_tokens(
        user_doc['_id'],
        user_doc['email'],
        user_doc['roles']
    )

    return jsonify({
        'status': 'success',
        'user_id': str(user_doc['_id']),
        'email': user_doc['email'],
        'roles': user_doc['roles'],
        **tokens
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user with email/password"""
    data = request.get_json()

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400

    db = request.app.config['MONGO_DB']

    # Find user
    user = User.find_by_email(db, data['email'])
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Verify password
    if not AuthService.verify_password(user['password_hash'], data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Generate tokens
    tokens = AuthService.generate_tokens(
        user['_id'],
        user['email'],
        user['roles']
    )

    # Update last_login
    db.users.update_one(
        {'_id': user['_id']},
        {'$set': {'last_login': datetime.utcnow()}}
    )

    return jsonify({
        'status': 'success',
        'user_id': str(user['_id']),
        'email': user['email'],
        'name': user['name'],
        'roles': user['roles'],
        **tokens
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token"""
    data = request.get_json()
    refresh_token = data.get('refresh_token')

    if not refresh_token:
        return jsonify({'error': 'Missing refresh token'}), 400

    new_access_token = AuthService.refresh_access_token(refresh_token)

    if not new_access_token:
        return jsonify({'error': 'Invalid or expired refresh token'}), 401

    return jsonify({
        'status': 'success',
        'access_token': new_access_token,
        'expires_in': AuthService.ACCESS_TOKEN_EXPIRY
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Get current user info"""
    return jsonify({
        'status': 'success',
        'user': {
            'user_id': current_user['user_id'],
            'email': current_user['email'],
            'roles': current_user['roles']
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout user (blacklist token)"""
    # Implement token blacklisting with Redis
    # redis_client.setex(f"blacklist:{token}", ACCESS_TOKEN_EXPIRY, '1')

    return jsonify({
        'status': 'success',
        'message': 'Logged out successfully'
    }), 200
```

## Step 1.3: Authorization Decorators

```python
# backend/app/utils/decorators.py

from functools import wraps
from flask import request, jsonify
from app.services.auth_service import AuthService
from app.models.user import User

def token_required(f):
    """Decorator to verify JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Missing authorization token'}), 401

        # Verify token
        payload = AuthService.verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Check if token is blacklisted
        # redis_client.get(f"blacklist:{token}") should return None

        return f(payload, *args, **kwargs)

    return decorated


def require_role(allowed_roles):
    """Decorator to verify user role"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated_function(current_user, *args, **kwargs):
            user_roles = current_user.get('roles', [])

            # Check if user has one of the allowed roles
            if not any(role in allowed_roles for role in user_roles):
                return jsonify({
                    'error': 'Forbidden',
                    'message': f'This action requires one of these roles: {allowed_roles}'
                }), 403

            return f(current_user, *args, **kwargs)

        return decorated_function
    return decorator


def require_permission(permission):
    """Decorator to verify user permission"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated_function(current_user, *args, **kwargs):
            # In real implementation, would check against roles/permissions mapping
            # db = request.app.config['MONGO_DB']
            # if not User.has_permission(db, current_user['user_id'], permission):
            #     return 403 Forbidden

            # For now, simplified check
            return f(current_user, *args, **kwargs)

        return decorated_function
    return decorator


def require_admin(f):
    """Decorator to require admin role"""
    return require_role(['admin'])(f)


def require_reviewer_or_teacher(f):
    """Decorator to require reviewer or teacher role"""
    return require_role(['reviewer', 'teacher'])(f)
```

---

# Phase 2: Classification & OCR Processing (Week 3-4)

## Step 2.1: Document Classification Endpoint

```python
# backend/app/routes/documents.py

from flask import Blueprint, request, jsonify
from app.utils.decorators import token_required, require_admin
from app.models.document import Document
from datetime import datetime
from bson.objectid import ObjectId

documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')


@documents_bp.route('/<doc_id>/classify', methods=['POST'])
@require_admin
def classify_document(current_user, doc_id):
    """Admin classifies document as Public or Private"""
    data = request.get_json()

    # Validate input
    classification = data.get('classification')
    if classification not in ['PUBLIC', 'PRIVATE']:
        return jsonify({'error': 'Invalid classification. Must be PUBLIC or PRIVATE'}), 400

    db = request.app.config['MONGO_DB']

    # Get document
    doc = db.documents.find_one({'_id': ObjectId(doc_id)})
    if not doc:
        return jsonify({'error': 'Document not found'}), 404

    # Check current status
    current_status = doc.get('status')
    if current_status not in ['UPLOADED', 'CLASSIFICATION_PENDING']:
        return jsonify({
            'error': 'Cannot change classification',
            'message': 'Document must be in CLASSIFICATION_PENDING status'
        }), 409

    # Update document
    new_status = f'CLASSIFIED_{classification}'

    db.documents.update_one(
        {'_id': ObjectId(doc_id)},
        {
            '$set': {
                'classification': classification,
                'status': new_status,
                'classified_by': ObjectId(current_user['user_id']),
                'classified_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            '$push': {
                'status_history': {
                    'status': new_status,
                    'changed_by': ObjectId(current_user['user_id']),
                    'changed_at': datetime.utcnow(),
                    'reason': data.get('reason', '')
                }
            }
        }
    )

    # Create audit log
    db.audit_logs.insert_one({
        '_id': ObjectId(),
        'action_type': 'ADMIN_CLASSIFY_DOC',
        'actor_id': ObjectId(current_user['user_id']),
        'actor_role': 'admin',
        'document_id': ObjectId(doc_id),
        'previous_state': {
            'status': current_status,
            'classification': doc.get('classification')
        },
        'new_state': {
            'status': new_status,
            'classification': classification
        },
        'reason': data.get('reason'),
        'created_at': datetime.utcnow()
    })

    return jsonify({
        'status': 'success',
        'document_id': doc_id,
        'classification': classification,
        'new_status': new_status,
        'message': f'Document classified as {classification}'
    }), 200
```

## Step 2.2: OCR Processing Endpoint

```python
# backend/app/routes/ocr.py

from flask import Blueprint, request, jsonify
from app.utils.decorators import token_required, require_admin
from app.services.ocr_service import OCRService
from datetime import datetime
from bson.objectid import ObjectId
import uuid

ocr_bp = Blueprint('ocr', __name__, url_prefix='/api/ocr')


@ocr_bp.route('/batch/process', methods=['POST'])
@require_admin
def start_batch_ocr(current_user):
    """Admin starts OCR processing on batch of documents"""
    data = request.get_json()

    # Validate input
    document_ids = data.get('document_ids', [])
    provider = data.get('provider', 'tesseract')
    settings = data.get('settings', {})

    if not document_ids:
        return jsonify({'error': 'No documents specified'}), 400

    if not isinstance(document_ids, list):
        return jsonify({'error': 'document_ids must be a list'}), 400

    db = request.app.config['MONGO_DB']

    # Validate all documents exist and are in correct status
    for doc_id in document_ids:
        doc = db.documents.find_one({'_id': ObjectId(doc_id)})
        if not doc:
            return jsonify({'error': f'Document {doc_id} not found'}), 404

        status = doc.get('status')
        if status not in ['CLASSIFIED_PUBLIC', 'CLASSIFIED_PRIVATE']:
            return jsonify({
                'error': f'Document {doc_id} not ready for OCR',
                'current_status': status
            }), 409

    # Create batch job
    job_id = f'job_{uuid.uuid4().hex[:12]}'

    batch_job = {
        '_id': ObjectId(),
        'job_id': job_id,
        'admin_id': ObjectId(current_user['user_id']),
        'document_ids': [ObjectId(d) for d in document_ids],
        'document_count': len(document_ids),
        'provider': provider,
        'settings': settings,
        'status': 'PROCESSING',
        'progress': {
            'current': 0,
            'total': len(document_ids),
            'percentage': 0
        },
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    db.ocr_jobs.insert_one(batch_job)

    # Queue OCR tasks (NSQ or async)
    for doc_id in document_ids:
        db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {
                '$set': {
                    'status': 'OCR_PROCESSING',
                    'ocr_job_id': job_id,
                    'updated_at': datetime.utcnow()
                },
                '$push': {
                    'status_history': {
                        'status': 'OCR_PROCESSING',
                        'changed_by': ObjectId(current_user['user_id']),
                        'changed_at': datetime.utcnow()
                    }
                }
            }
        )

    # Create audit log
    db.audit_logs.insert_one({
        '_id': ObjectId(),
        'action_type': 'ADMIN_RUN_OCR',
        'actor_id': ObjectId(current_user['user_id']),
        'actor_role': 'admin',
        'resource_type': 'batch_job',
        'resource_id': batch_job['_id'],
        'additional_context': {
            'document_count': len(document_ids),
            'provider': provider
        },
        'created_at': datetime.utcnow()
    })

    return jsonify({
        'status': 'success',
        'job_id': job_id,
        'document_count': len(document_ids),
        'progress': batch_job['progress'],
        'message': f'OCR batch job started for {len(document_ids)} documents'
    }), 201


@ocr_bp.route('/jobs/<job_id>/status', methods=['GET'])
@token_required
def get_ocr_status(current_user, job_id):
    """Get status of OCR batch job"""
    db = request.app.config['MONGO_DB']

    job = db.ocr_jobs.find_one({'job_id': job_id})
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify({
        'status': 'success',
        'job_id': job_id,
        'batch_status': job.get('status'),
        'progress': job.get('progress'),
        'created_at': job.get('created_at').isoformat(),
        'updated_at': job.get('updated_at').isoformat()
    }), 200
```

---

# Phase 3: Review Workflow (Week 5-6)

## Step 3.1: Review Queue Endpoint

```python
# backend/app/routes/review_queue.py

from flask import Blueprint, request, jsonify
from app.utils.decorators import token_required, require_role
from bson.objectid import ObjectId
from datetime import datetime

review_bp = Blueprint('review', __name__, url_prefix='/api/review-queue')


@review_bp.route('', methods=['GET'])
@token_required
def get_review_queue(current_user):
    """Get review queue for current user based on role"""
    db = request.app.config['MONGO_DB']
    user_id = ObjectId(current_user['user_id'])
    user_roles = current_user.get('roles', [])

    # Build query based on user role
    query = {'status': 'IN_REVIEW'}

    if 'reviewer' in user_roles:
        # Reviewers only see PUBLIC documents
        query['classification'] = 'PUBLIC'
    elif 'teacher' in user_roles:
        # Teachers see both PUBLIC and PRIVATE
        query['classification'] = {'$in': ['PUBLIC', 'PRIVATE']}
    elif 'admin' in user_roles:
        # Admins see all (no classification filter)
        pass
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    skip = (page - 1) * per_page

    # Get documents
    documents = list(db.documents.find(query).skip(skip).limit(per_page))
    total_count = db.documents.count_documents(query)

    # Convert ObjectId to string for JSON
    for doc in documents:
        doc['_id'] = str(doc['_id'])
        doc['project_id'] = str(doc['project_id'])

    return jsonify({
        'status': 'success',
        'queue': documents,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': (total_count + per_page - 1) // per_page
        }
    }), 200


@review_bp.route('/<doc_id>/claim', methods=['POST'])
@require_role(['reviewer', 'teacher'])
def claim_document(current_user, doc_id):
    """Claim document from review queue"""
    db = request.app.config['MONGO_DB']
    user_id = ObjectId(current_user['user_id'])
    user_roles = current_user.get('roles', [])

    # Find document
    doc = db.documents.find_one({'_id': ObjectId(doc_id)})
    if not doc:
        return jsonify({'error': 'Document not found'}), 404

    # Check status
    if doc.get('status') != 'IN_REVIEW':
        return jsonify({'error': 'Document not in review status'}), 409

    # Check classification access
    classification = doc.get('classification')
    if 'reviewer' in user_roles and classification == 'PRIVATE':
        return jsonify({'error': 'Forbidden: Cannot access PRIVATE document'}), 403

    # Check if already claimed (race condition handling)
    if doc.get('claimed_by') is not None:
        return jsonify({
            'error': 'Conflict: Document already claimed',
            'claimed_by': str(doc.get('claimed_by'))
        }), 409

    # Claim document (with optimistic locking)
    result = db.documents.update_one(
        {
            '_id': ObjectId(doc_id),
            'claimed_by': None  # Only update if not already claimed
        },
        {
            '$set': {
                'claimed_by': user_id,
                'claimed_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        # Document was claimed by someone else
        return jsonify({'error': 'Conflict: Document already claimed'}), 409

    # Create audit log
    action_type = 'TEACHER_CLAIM_DOC' if 'teacher' in user_roles else 'REVIEWER_CLAIM_DOC'
    db.audit_logs.insert_one({
        '_id': ObjectId(),
        'action_type': action_type,
        'actor_id': user_id,
        'actor_role': user_roles[0],
        'document_id': ObjectId(doc_id),
        'additional_context': {'classification': classification},
        'created_at': datetime.utcnow()
    })

    return jsonify({
        'status': 'success',
        'message': 'Document claimed successfully',
        'document_id': doc_id,
        'claimed_at': datetime.utcnow().isoformat()
    }), 200


@review_bp.route('/<doc_id>/approve', methods=['POST'])
@require_role(['reviewer', 'teacher'])
def approve_document(current_user, doc_id):
    """Approve document after review"""
    data = request.get_json()
    db = request.app.config['MONGO_DB']
    user_id = ObjectId(current_user['user_id'])
    user_roles = current_user.get('roles', [])

    # Find document
    doc = db.documents.find_one({'_id': ObjectId(doc_id)})
    if not doc:
        return jsonify({'error': 'Document not found'}), 404

    # Check status
    if doc.get('status') != 'IN_REVIEW':
        return jsonify({'error': 'Document not in IN_REVIEW status'}), 409

    # Check if claimed by current user
    if doc.get('claimed_by') != user_id:
        return jsonify({'error': 'Document not claimed by current user'}), 403

    # Process manual edits if provided
    manual_edits = []
    edit_fields = data.get('edit_fields', {})
    if edit_fields:
        for field_name, new_value in edit_fields.items():
            old_value = doc.get(field_name)
            manual_edits.append({
                'field_name': field_name,
                'original_value': old_value,
                'edited_value': new_value,
                'edited_by': user_id,
                'edited_at': datetime.utcnow()
            })

    # Update document
    update_data = {
        'status': 'REVIEWED_APPROVED',
        'reviewed_by': user_id,
        'reviewed_at': datetime.utcnow(),
        'review_notes': data.get('notes', ''),
        'claimed_by': None,  # Release document
        'updated_at': datetime.utcnow()
    }

    if manual_edits:
        update_data['manual_edits'] = manual_edits

    db.documents.update_one(
        {'_id': ObjectId(doc_id)},
        {
            '$set': update_data,
            '$push': {
                'status_history': {
                    'status': 'REVIEWED_APPROVED',
                    'changed_by': user_id,
                    'changed_at': datetime.utcnow()
                }
            }
        }
    )

    # Create audit log
    action_type = 'TEACHER_APPROVE_DOC_ASIC' if 'teacher' in user_roles else 'REVIEWER_APPROVE_DOC_ASIC'
    if manual_edits:
        action_type = action_type.replace('_ASIC', '_EDIT_AND_APPROVE')

    db.audit_logs.insert_one({
        '_id': ObjectId(),
        'action_type': action_type,
        'actor_id': user_id,
        'actor_role': user_roles[0],
        'document_id': ObjectId(doc_id),
        'new_state': {'status': 'REVIEWED_APPROVED'},
        'changes': [{'field': 'status', 'new_value': 'REVIEWED_APPROVED'}],
        'created_at': datetime.utcnow()
    })

    return jsonify({
        'status': 'success',
        'message': 'Document approved successfully',
        'document_id': doc_id,
        'new_status': 'REVIEWED_APPROVED',
        'edits_count': len(manual_edits)
    }), 200
```

---

# Continued in Next Section...

(This implementation guide continues with Phases 4-6, database migrations, configuration, and deployment checklists)

---

## Database Collections Index Reference

```javascript
// Create all necessary indexes for optimal performance

// Users
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ roles: 1 });
db.users.createIndex({ created_at: -1 });

// Documents
db.documents.createIndex({ project_id: 1 });
db.documents.createIndex({ status: 1 });
db.documents.createIndex({ classification: 1 });
db.documents.createIndex({ reviewed_by: 1 });
db.documents.createIndex({ processed_by: 1 });
db.documents.createIndex({ created_at: -1 });
db.documents.createIndex({ project_id: 1, status: 1 });
db.documents.createIndex({ classification: 1, status: 1 });

// Audit Logs
db.audit_logs.createIndex({ action_type: 1 });
db.audit_logs.createIndex({ actor_id: 1 });
db.audit_logs.createIndex({ document_id: 1 });
db.audit_logs.createIndex({ created_at: -1 });
db.audit_logs.createIndex({ document_id: 1, created_at: 1 });

// Review Queues
db.review_queues.createIndex({ project_id: 1 });
db.review_queues.createIndex({ status: 1 });
db.review_queues.createIndex({ classification: 1 });
db.review_queues.createIndex({ due_at: 1 });

// Roles
db.roles.createIndex({ name: 1 }, { unique: true });

// Projects
db.projects.createIndex({ user_id: 1 });
db.projects.createIndex({ 'collaborators.user_id': 1 });
```

---

## Environment Configuration Template

```bash
# .env file

# Database
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=ocr_rbac_db
MONGO_USERNAME=ocr_user
MONGO_PASSWORD=secure_password

# JWT
JWT_SECRET_KEY=your-min-32-character-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRY=3600
REFRESH_TOKEN_EXPIRY=2592000

# Redis (for token blacklist/cache)
REDIS_URL=redis://localhost:6379/0

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=flask-secret-key

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# OAuth (if using)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# OCR Providers
TESSERACT_PATH=/usr/bin/tesseract
GOOGLE_VISION_API_KEY=your-api-key
OLLAMA_HOST=http://localhost:11434

# NSQ (for job queue)
NSQ_LOOKUPD=localhost:4161
NSQD_ADDRESS=localhost:4150

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/ocr_rbac.log
```

---

## Frontend Authentication Setup (React)

```typescript
// frontend/src/stores/authStore.ts

import create from 'zustand';

interface AuthState {
  user: {
    user_id: string;
    email: string;
    name: string;
    roles: string[];
  } | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem('accessToken'),
  refreshToken: localStorage.getItem('refreshToken'),
  isAuthenticated: !!localStorage.getItem('accessToken'),

  login: async (email: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) throw new Error('Login failed');

    const data = await response.json();

    localStorage.setItem('accessToken', data.access_token);
    localStorage.setItem('refreshToken', data.refresh_token);

    set({
      user: {
        user_id: data.user_id,
        email: data.email,
        name: data.name,
        roles: data.roles
      },
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      isAuthenticated: true
    });
  },

  logout: () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false
    });
  },

  refreshAccessToken: async () => {
    const state = get();
    if (!state.refreshToken) throw new Error('No refresh token');

    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: state.refreshToken })
    });

    if (!response.ok) throw new Error('Token refresh failed');

    const data = await response.json();
    localStorage.setItem('accessToken', data.access_token);

    set({ accessToken: data.access_token });
  },

  hasPermission: (permission: string) => {
    // Simplified - full implementation would check against role permissions
    return true;
  },

  hasRole: (role: string) => {
    const state = get();
    return state.user?.roles?.includes(role) || false;
  }
}));
```

