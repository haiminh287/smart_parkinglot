"""
Facebook OAuth2 integration.
"""

import requests
from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth import get_user_model
from ..models import OAuthAccount

User = get_user_model()

FACEBOOK_AUTH_URL = 'https://www.facebook.com/v18.0/dialog/oauth'
FACEBOOK_TOKEN_URL = 'https://graph.facebook.com/v18.0/oauth/access_token'
FACEBOOK_USER_INFO_URL = 'https://graph.facebook.com/me'


def get_facebook_auth_url(state: str):
    """Generate Facebook OAuth2 authorization URL."""

    redirect_uri = settings.FACEBOOK_REDIRECT_URI

    params = {
        'client_id': settings.FACEBOOK_APP_ID,
        'redirect_uri': redirect_uri,
        'scope': 'email,public_profile',
        'response_type': 'code',
        'state': state,
    }

    query_string = urlencode(params)

    return f'{FACEBOOK_AUTH_URL}?{query_string}'


def exchange_facebook_code(code):
    """Exchange authorization code for access token and create/login user."""

    redirect_uri = settings.FACEBOOK_REDIRECT_URI

    # Exchange code for token
    token_response = requests.get(FACEBOOK_TOKEN_URL, params={
        'code': code,
        'client_id': settings.FACEBOOK_APP_ID,
        'client_secret': settings.FACEBOOK_APP_SECRET,
        'redirect_uri': redirect_uri
    }, timeout=10)

    token_response.raise_for_status()
    token_data = token_response.json()

    if 'error' in token_data:
        raise Exception(f"Facebook OAuth error: {token_data['error']['message']}")

    access_token = token_data['access_token']

    # Get user info
    user_info_response = requests.get(
        FACEBOOK_USER_INFO_URL,
        params={
            'fields': 'id,name,email,picture',
            'access_token': access_token
        },
        timeout=10,
    )

    user_info_response.raise_for_status()
    user_info = user_info_response.json()

    # Get or create user
    email = user_info.get('email')
    facebook_user_id = user_info['id']

    if not email:
        raise Exception('Email not provided by Facebook')

    try:
        oauth_account = OAuthAccount.objects.get(provider='facebook', provider_user_id=facebook_user_id)
        user = oauth_account.user
    except OAuthAccount.DoesNotExist:
        # Check if user exists with this email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create new user
            avatar_url = user_info.get('picture', {}).get('data', {}).get('url')
            user = User.objects.create_user(
                email=email,
                username=user_info.get('name', email.split('@')[0]),
                avatar=avatar_url
            )
        
        # Create OAuth account
        OAuthAccount.objects.create(
            user=user,
            provider='facebook',
            provider_user_id=facebook_user_id,
            access_token=access_token
        )

    return user
