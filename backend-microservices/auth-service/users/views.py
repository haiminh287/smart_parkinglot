"""
Views for authentication service using HttpOnly cookies.
"""

import secrets
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import login, logout
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
from .oauth.facebook import get_facebook_auth_url, exchange_facebook_code

from shared.gateway_permissions import IsGatewayAuthenticated


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
        from django.middleware.csrf import get_token
        csrf_token = get_token(request)
        response.set_cookie(
            key='csrftoken',
            value=csrf_token,
            httponly=False,  # Must be False so frontend can read it
            secure=False,  # False for development
            samesite='Lax'
        )
        
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
    
    auth_url = get_google_auth_url()
    
    return Response({
        'authorization_url': auth_url
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def google_callback_view(request):
    """Handle Google OAuth2 callback."""
    
    code = request.GET.get('code')
    
    if not code:
        return Response({
            'error': 'No authorization code provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = exchange_google_code(code)
        
        # Django session login
        login(request, user)
        
        response = Response({
            'user': UserSerializer(user).data,
            'message': 'Google login successful'
        })
        
        # Set HttpOnly cookie
        response.set_cookie(
            key='sessionid',
            value=request.session.session_key,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            max_age=settings.SESSION_COOKIE_AGE
        )
        
        return response
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def facebook_auth_url_view(request):
    """Get Facebook OAuth2 authorization URL."""
    
    auth_url = get_facebook_auth_url()
    
    return Response({
        'authorization_url': auth_url
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def facebook_callback_view(request):
    """Handle Facebook OAuth2 callback."""
    
    code = request.GET.get('code')
    
    if not code:
        return Response({
            'error': 'No authorization code provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = exchange_facebook_code(code)
        
        # Django session login
        login(request, user)
        
        response = Response({
            'user': UserSerializer(user).data,
            'message': 'Facebook login successful'
        })
        
        # Set HttpOnly cookie
        response.set_cookie(
            key='sessionid',
            value=request.session.session_key,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            max_age=settings.SESSION_COOKIE_AGE
        )
        
        return response
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
