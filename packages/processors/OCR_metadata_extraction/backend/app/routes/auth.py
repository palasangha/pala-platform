from flask import Blueprint, request, jsonify, redirect
from app.models import mongo
from app.models.user import User
from app.services.google_auth import GoogleAuthService
from app.config import Config
import jwt
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

# Initialize Google Auth Service
google_auth = GoogleAuthService(
    Config.GOOGLE_CLIENT_ID,
    Config.GOOGLE_CLIENT_SECRET,
    Config.GOOGLE_REDIRECT_URI
)

def create_tokens(user_id):
    """Create access and refresh tokens"""
    access_token = jwt.encode({
        'user_id': str(user_id),
        'exp': datetime.utcnow() + Config.JWT_ACCESS_TOKEN_EXPIRES
    }, Config.JWT_SECRET_KEY, algorithm='HS256')

    refresh_token = jwt.encode({
        'user_id': str(user_id),
        'exp': datetime.utcnow() + Config.JWT_REFRESH_TOKEN_EXPIRES
    }, Config.JWT_SECRET_KEY, algorithm='HS256')

    return access_token, refresh_token

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user with email and password"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Check if user already exists
        existing_user = User.find_by_email(mongo, email)
        if existing_user:
            return jsonify({'error': 'User already exists'}), 409

        # Create new user
        user = User.create(mongo, email, password=password, name=name)

        # Create tokens
        access_token, refresh_token = create_tokens(user['_id'])

        return jsonify({
            'message': 'User registered successfully',
            'user': User.to_dict(user),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with email and password"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Find user
        user = User.find_by_email(mongo, email)
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Verify password
        if not User.verify_password(user, password):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Create tokens
        access_token, refresh_token = create_tokens(user['_id'])

        return jsonify({
            'message': 'Login successful',
            'user': User.to_dict(user),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/google', methods=['GET'])
def google_login():
    """Initiate Google OAuth login"""
    try:
        auth_url = google_auth.get_authorization_url()
        return jsonify({'auth_url': auth_url}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'Authorization code not provided'}), 400

        # Exchange code for token
        token_data = google_auth.exchange_code_for_token(code)
        access_token = token_data.get('access_token')

        # Get user info
        user_info = google_auth.get_user_info(access_token)
        email = user_info.get('email')
        google_id = user_info.get('id')
        name = user_info.get('name')

        # Find or create user
        user = User.find_by_google_id(mongo, google_id)
        if not user:
            user = User.find_by_email(mongo, email)
            if user:
                # Update existing user with Google ID
                User.update(mongo, user['_id'], {'google_id': google_id})
            else:
                # Create new user
                user = User.create(mongo, email, google_id=google_id, name=name)

        # Create tokens
        access_token, refresh_token = create_tokens(user['_id'])

        # Redirect to frontend with tokens
        frontend_url = f"{Config.CORS_ORIGINS[0]}/auth/callback?access_token={access_token}&refresh_token={refresh_token}"
        return redirect(frontend_url)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({'error': 'Refresh token is required'}), 400

        # Decode refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                Config.JWT_SECRET_KEY,
                algorithms=['HS256']
            )
            user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Refresh token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid refresh token'}), 401

        # Create new access token
        access_token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.utcnow() + Config.JWT_ACCESS_TOKEN_EXPIRES
        }, Config.JWT_SECRET_KEY, algorithm='HS256')

        return jsonify({
            'access_token': access_token
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user info"""
    try:
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header missing'}), 401

        token = auth_header.split(' ')[1]

        # Decode token
        try:
            payload = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=['HS256']
            )
            user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        # Get user
        user = User.find_by_id(mongo, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': User.to_dict(user)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
