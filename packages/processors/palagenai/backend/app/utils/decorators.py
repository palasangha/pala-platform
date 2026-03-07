from functools import wraps
from flask import request, jsonify
import jwt
from app.config import Config
from app.models.user import User
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.models import mongo

def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Decode token
            data = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=['HS256']
            )
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated


def token_required_sse(f):
    """Decorator to protect SSE/streaming routes with JWT authentication

    Supports both Authorization header and query parameter token
    (needed because EventSource doesn't support custom headers)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check for token in Authorization header first
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                pass

        # Fall back to query parameter (for SSE/EventSource)
        if not token:
            token = request.args.get('token')

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Decode token
            data = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=['HS256']
            )
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated


def require_role(*allowed_roles):
    """Decorator to check if user has any of the allowed roles"""
    def decorator(f):
        @wraps(f)
        def decorated(current_user_id, *args, **kwargs):
            # Get user
            user = User.find_by_id(mongo, current_user_id)
            if not user:
                AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                               details={'reason': 'User not found'})
                return jsonify({'error': 'User not found'}), 404

            # Check if user has any of the allowed roles
            user_roles = user.get('roles', [])
            has_role = any(role in user_roles for role in allowed_roles)

            if not has_role:
                AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                               details={'reason': f'Required roles: {allowed_roles}, user roles: {user_roles}'})
                return jsonify({
                    'error': 'Insufficient permissions',
                    'required_roles': list(allowed_roles),
                    'user_roles': user_roles
                }), 403

            return f(current_user_id, *args, **kwargs)

        return decorated

    return decorator


def require_permission(permission):
    """Decorator to check if user has a specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated(current_user_id, *args, **kwargs):
            # Get user
            user = User.find_by_id(mongo, current_user_id)
            if not user:
                AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                               details={'reason': 'User not found'})
                return jsonify({'error': 'User not found'}), 404

            # Check if any of user's roles has the permission
            user_roles = user.get('roles', [])
            has_permission = False

            for role_name in user_roles:
                if Role.has_permission(mongo, role_name, permission):
                    has_permission = True
                    break

            if not has_permission:
                AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                               details={'reason': f'Required permission: {permission}'})
                return jsonify({
                    'error': 'Insufficient permissions',
                    'required_permission': permission
                }), 403

            return f(current_user_id, *args, **kwargs)

        return decorated

    return decorator


def require_admin(f):
    """Shorthand decorator to require admin role"""
    @wraps(f)
    def decorated(current_user_id, *args, **kwargs):
        user = User.find_by_id(mongo, current_user_id)
        if not user:
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           details={'reason': 'User not found'})
            return jsonify({'error': 'User not found'}), 404

        if 'admin' not in user.get('roles', []):
            AuditLog.create(mongo, current_user_id, AuditLog.ACTION_UNAUTHORIZED_ACCESS,
                           details={'reason': 'Admin role required'})
            return jsonify({
                'error': 'Insufficient permissions',
                'required_role': 'admin'
            }), 403

        return f(current_user_id, *args, **kwargs)

    return decorated
