"""
Google OAuth2 integration.
"""

import requests
from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth import get_user_model
from ..models import OAuthAccount

User = get_user_model()

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USER_INFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'


def get_google_auth_url(state: str):
    """Generate Google OAuth2 authorization URL."""

    redirect_uri = settings.GOOGLE_REDIRECT_URI

    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state,
    }

    query_string = urlencode(params)

    return f'{GOOGLE_AUTH_URL}?{query_string}'


def exchange_google_code(code):
    """Exchange authorization code for access token and create/login user."""

    redirect_uri = settings.GOOGLE_REDIRECT_URI

    # Exchange code for token
    token_response = requests.post(GOOGLE_TOKEN_URL, data={
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }, timeout=10)

    token_response.raise_for_status()
    token_data = token_response.json()

    if 'error' in token_data:
        raise Exception(f"Google OAuth error: {token_data['error']}")

    access_token = token_data['access_token']

    # Get user info
    user_info_response = requests.get(
        GOOGLE_USER_INFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    user_info_response.raise_for_status()
    user_info = user_info_response.json()

    # Get or create user
    email = user_info['email']
    google_user_id = user_info['id']

    try:
        oauth_account = OAuthAccount.objects.get(provider='google', provider_user_id=google_user_id)
        user = oauth_account.user
    except OAuthAccount.DoesNotExist:
        # Check if user exists with this email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create_user(
                email=email,
                username=user_info.get('name', email.split('@')[0]),
                avatar=user_info.get('picture')
            )
        
        # Create OAuth account
        OAuthAccount.objects.create(
            user=user,
            provider='google',
            provider_user_id=google_user_id,
            access_token=access_token,
            refresh_token=token_data.get('refresh_token')
        )

    return user
