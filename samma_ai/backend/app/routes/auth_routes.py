"""
Authentication Routes - Claude OAuth flow for Pala Jarvis
"""

from flask import Blueprint, request, jsonify, redirect
import secrets
import hashlib
import base64
import requests
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

# Claude OAuth Configuration (using Claude Code's client ID)
CLAUDE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
CLAUDE_AUTH_URL = "https://claude.ai/oauth/authorize"
CLAUDE_TOKEN_URL = "https://api.anthropic.com/v1/oauth/token"
REDIRECT_URI = "http://localhost:5001/api/auth/claude/callback"

# In-memory storage for OAuth state (in production, use Redis/database)
_oauth_sessions = {}
_user_tokens = {}


def generate_pkce_pair():
    """Generate PKCE code verifier and challenge."""
    # Generate random code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

    # Create code challenge (SHA256 hash of verifier)
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

    return code_verifier, code_challenge


@auth_bp.route('/auth/claude/login', methods=['GET'])
def claude_login():
    """
    Initiate Claude OAuth flow.

    Returns a redirect URL that the frontend should open.
    """
    # Generate state and PKCE parameters
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = generate_pkce_pair()

    # Store state and verifier for callback verification
    _oauth_sessions[state] = {
        'code_verifier': code_verifier,
        'created_at': datetime.utcnow(),
    }

    # Clean up old sessions (>10 minutes)
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    _oauth_sessions.clear()  # Simple cleanup for now

    # Build authorization URL
    params = {
        'client_id': CLAUDE_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': 'org:create_api_key user:profile user:inference user:sessions:claude_code user:mcp_servers',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'state': state,
    }

    auth_url = f"{CLAUDE_AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    return jsonify({
        'auth_url': auth_url,
        'state': state,
    })


@auth_bp.route('/auth/claude/callback', methods=['GET'])
def claude_callback():
    """
    Handle OAuth callback from Claude.

    Exchanges authorization code for access token.
    """
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        return f"""
        <html>
        <body>
            <h1>Authentication Failed</h1>
            <p>Error: {error}</p>
            <p><a href="http://localhost:8080">Return to Samma AI</a></p>
        </body>
        </html>
        """, 400

    if not code or not state:
        return "Missing code or state", 400

    # Verify state and get code verifier
    session = _oauth_sessions.get(state)
    if not session:
        return "Invalid or expired state", 400

    code_verifier = session['code_verifier']

    # Exchange code for token
    try:
        token_response = requests.post(
            CLAUDE_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': REDIRECT_URI,
                'client_id': CLAUDE_CLIENT_ID,
                'code_verifier': code_verifier,
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            timeout=30,
        )

        if token_response.status_code != 200:
            return f"""
            <html>
            <body>
                <h1>Token Exchange Failed</h1>
                <p>Status: {token_response.status_code}</p>
                <p>Response: {token_response.text}</p>
                <p><a href="http://localhost:8080">Return to Samma AI</a></p>
            </body>
            </html>
            """, 400

        token_data = token_response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            return "No access token received", 400

        # Generate a session ID for the frontend
        session_id = secrets.token_urlsafe(32)

        # Store token (in production, use secure storage)
        _user_tokens[session_id] = {
            'access_token': access_token,
            'token_type': token_data.get('token_type', 'bearer'),
            'expires_at': datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600)),
            'created_at': datetime.utcnow(),
        }

        # Clean up OAuth session
        _oauth_sessions.pop(state, None)

        # Return success page that closes the popup and sends token to parent
        return f"""
        <html>
        <head>
            <title>Authentication Successful</title>
        </head>
        <body>
            <h1>✓ Authentication Successful!</h1>
            <p>You can close this window and return to Samma AI.</p>
            <script>
                // Send session ID to parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'claude_auth_success',
                        session_id: '{session_id}'
                    }}, 'http://localhost:8080');
                    setTimeout(() => window.close(), 1000);
                }} else {{
                    // If not a popup, redirect to app
                    window.location.href = 'http://localhost:8080?session_id={session_id}';
                }}
            </script>
        </body>
        </html>
        """

    except Exception as e:
        return f"""
        <html>
        <body>
            <h1>Authentication Error</h1>
            <p>Error: {str(e)}</p>
            <p><a href="http://localhost:8080">Return to Samma AI</a></p>
        </body>
        </html>
        """, 500


@auth_bp.route('/auth/claude/status', methods=['GET'])
def auth_status():
    """Check if user is authenticated."""
    session_id = request.headers.get('X-Session-ID')

    if not session_id or session_id not in _user_tokens:
        return jsonify({'authenticated': False})

    token_info = _user_tokens[session_id]

    # Check if token expired
    if token_info['expires_at'] < datetime.utcnow():
        _user_tokens.pop(session_id, None)
        return jsonify({'authenticated': False, 'error': 'Token expired'})

    return jsonify({
        'authenticated': True,
        'expires_at': token_info['expires_at'].isoformat(),
    })


@auth_bp.route('/auth/claude/logout', methods=['POST'])
def logout():
    """Logout user by removing their token."""
    session_id = request.headers.get('X-Session-ID')

    if session_id:
        _user_tokens.pop(session_id, None)

    return jsonify({'success': True})


def get_user_token(session_id: str) -> str:
    """Get access token for a session ID. Used by Pala Jarvis service."""
    if not session_id or session_id not in _user_tokens:
        return None

    token_info = _user_tokens[session_id]

    # Check expiration
    if token_info['expires_at'] < datetime.utcnow():
        _user_tokens.pop(session_id, None)
        return None

    return token_info['access_token']
