"""
Views for authentication service using HttpOnly cookies.
"""

import secrets
import logging
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import login, logout
from django.core import signing
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, PasswordReset
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
)
from .oauth.google import get_google_auth_url, exchange_google_code

from shared.gateway_permissions import IsGatewayAuthenticated


logger = logging.getLogger(__name__)

OAUTH_STATE_SESSION_KEY = 'oauth_state_nonces'
OAUTH_ERROR_INVALID_REQUEST = 'invalid_request'
OAUTH_ERROR_INVALID_STATE = 'invalid_state'
OAUTH_ERROR_PROVIDER = 'provider_error'


def attach_csrf_cookie(request, response: Response) -> None:
    from django.middleware.csrf import get_token

    csrf_token = get_token(request)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.CSRF_COOKIE_AGE,
        path=settings.CSRF_COOKIE_PATH,
        domain=settings.CSRF_COOKIE_DOMAIN,
        secure=settings.CSRF_COOKIE_SECURE,
        httponly=settings.CSRF_COOKIE_HTTPONLY,
        samesite=settings.CSRF_COOKIE_SAMESITE,
    )


def sanitize_return_to(value: str | None) -> str:
    if not value:
        return '/'
    if not value.startswith('/') or value.startswith('//'):
        return '/'
    if value.startswith('/auth/callback'):
        return '/'
    return value


def _store_oauth_state_nonce(request, provider: str, nonce: str) -> None:
    state_store = request.session.get(OAUTH_STATE_SESSION_KEY)
    if not isinstance(state_store, dict):
        state_store = {}
    state_store[f'{provider}:{nonce}'] = True
    request.session[OAUTH_STATE_SESSION_KEY] = state_store
    request.session.modified = True


def _consume_oauth_state_nonce(request, provider: str, nonce: str) -> bool:
    state_store = request.session.get(OAUTH_STATE_SESSION_KEY)
    if not isinstance(state_store, dict):
        return False
    key = f'{provider}:{nonce}'
    if key not in state_store:
        return False
    del state_store[key]
    request.session[OAUTH_STATE_SESSION_KEY] = state_store
    request.session.modified = True
    return True


def create_oauth_state(request, provider: str, return_to: str) -> str:
    nonce = secrets.token_urlsafe(16)
    payload = {
        'provider': provider,
        'return_to': sanitize_return_to(return_to),
        'nonce': nonce,
    }
    _store_oauth_state_nonce(request, provider, nonce)
    return signing.dumps(
        payload,
        key=settings.OAUTH_STATE_SECRET,
        salt='oauth.state',
    )


def validate_oauth_state(request, raw_state: str, provider: str):
    try:
        payload = signing.loads(
            raw_state,
            key=settings.OAUTH_STATE_SECRET,
            salt='oauth.state',
            max_age=settings.OAUTH_STATE_TTL_SECONDS,
        )
    except signing.SignatureExpired:
        return None, OAUTH_ERROR_INVALID_STATE
    except signing.BadSignature:
        return None, OAUTH_ERROR_INVALID_STATE

    if payload.get('provider') != provider:
        return None, OAUTH_ERROR_INVALID_STATE

    nonce = payload.get('nonce')
    if not isinstance(nonce, str) or not nonce:
        return None, OAUTH_ERROR_INVALID_STATE
    if not _consume_oauth_state_nonce(request, provider, nonce):
        return None, OAUTH_ERROR_INVALID_STATE

    payload['return_to'] = sanitize_return_to(payload.get('return_to'))
    return payload, None


class RegisterView(generics.CreateAPIView):
    """Register new user."""
    
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Login user and set HttpOnly cookie."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Django session login (sets sessionid cookie as HttpOnly)
        login(request, user)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        response = Response({
            'user': UserSerializer(user).data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)

        # Ensure CSRF token is set in cookie (for subsequent requests)
        attach_csrf_cookie(request, response)
        
        return response


class LogoutView(APIView):
    """Logout user and clear HttpOnly cookie."""
    
    permission_classes = [AllowAny]  # Allow logout without authentication (will clear session anyway)
    
    def post(self, request):
        logout(request)
        
        response = Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
        
        # Clear HttpOnly cookie
        response.delete_cookie('sessionid')
        
        return response


class CurrentUserView(APIView):
    """Get current authenticated user."""
    
    permission_classes = [IsGatewayAuthenticated]
    
    def get(self, request):
        # Get user from user_id injected by gateway
        try:
            user = User.objects.get(id=request.user_id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


class ChangePasswordView(APIView):
    """Change user password."""
    
    permission_classes = [IsGatewayAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    """Request password reset token."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=1)
            
            PasswordReset.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )
            
            # TODO: Send email with reset link
            # send_password_reset_email(user.email, token)
            
            return Response({
                'message': 'Password reset email sent',
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response({
                'message': 'If email exists, password reset instructions will be sent'
            }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """Reset password using token."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            reset = PasswordReset.objects.get(token=token, used=False)
            
            if reset.expires_at < timezone.now():
                return Response({
                    'error': 'Reset token has expired'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Reset password
            user = reset.user
            user.set_password(new_password)
            user.save()
            
            # Mark token as used
            reset.used = True
            reset.save()
            
            return Response({
                'message': 'Password reset successfully'
            }, status=status.HTTP_200_OK)
        
        except PasswordReset.DoesNotExist:
            return Response({
                'error': 'Invalid reset token'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def google_auth_url_view(request):
    """Get Google OAuth2 authorization URL."""

    return_to = sanitize_return_to(request.GET.get('return_to'))
    state = create_oauth_state(request, 'google', return_to)
    auth_url = get_google_auth_url(state)
    
    return Response({
        'authorization_url': auth_url
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def google_callback_view(request):
    """Handle Google OAuth2 callback."""

    code = request.GET.get('code')
    raw_state = request.GET.get('state')
    
    if not code:
        return Response({
            'error': OAUTH_ERROR_INVALID_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

    if not raw_state:
        return Response({
            'error': OAUTH_ERROR_INVALID_STATE
        }, status=status.HTTP_400_BAD_REQUEST)

    state_payload, state_error = validate_oauth_state(request, raw_state, 'google')
    if state_error:
        return Response({
            'error': state_error
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = exchange_google_code(code)

        # Django session login
        login(request, user)

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        response = Response({
            'user': UserSerializer(user).data,
            'message': 'Google login successful',
            'provider': 'google',
        })

        attach_csrf_cookie(request, response)

        return response
    
    except Exception:
        logger.exception('google_callback_failed')
        return Response({
            'error': OAUTH_ERROR_PROVIDER
        }, status=status.HTTP_400_BAD_REQUEST)
