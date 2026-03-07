from google.oauth2 import id_token
from google.auth.transport import requests
import requests as req

class GoogleAuthService:
    """Service for Google OAuth authentication"""

    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_endpoint = 'https://oauth2.googleapis.com/token'
        self.userinfo_endpoint = 'https://www.googleapis.com/oauth2/v2/userinfo'

    def get_authorization_url(self):
        """Get Google OAuth authorization URL"""
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"access_type=offline&"
            f"prompt=consent"
        )
        return auth_url

    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }

        response = req.post(self.token_endpoint, data=data)
        response.raise_for_status()
        return response.json()

    def get_user_info(self, access_token):
        """Get user information from Google"""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = req.get(self.userinfo_endpoint, headers=headers)
        response.raise_for_status()
        return response.json()

    def verify_id_token(self, token):
        """Verify Google ID token"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                self.client_id
            )
            return idinfo
        except ValueError:
            return None
