"""
Serializers for auth service.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, OAuthAccount


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (read-only representation)."""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'avatar', 'phone', 'address', 'role', 
                  'is_active', 'is_staff', 'no_show_count', 'force_online_payment', 'last_login', 'date_joined']
        read_only_fields = ['id', 'is_staff', 'no_show_count', 'force_online_payment', 'last_login', 'date_joined']


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin user update (PATCH/PUT). All fields optional."""
    
    class Meta:
        model = User
        fields = ['email', 'username', 'avatar', 'phone', 'address', 'role',
                  'is_active', 'is_staff']
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': False},
            'avatar': {'required': False},
            'phone': {'required': False},
            'address': {'required': False},
            'role': {'required': False},
            'is_active': {'required': False},
            'is_staff': {'required': False},
        }

    def validate(self, attrs):
        """Sync is_staff when role changes and vice-versa."""
        if 'role' in attrs and 'is_staff' not in attrs:
            attrs['is_staff'] = attrs['role'] == 'admin'
        elif 'is_staff' in attrs and 'role' not in attrs:
            if attrs['is_staff']:
                attrs['role'] = 'admin'
        return attrs


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Serializer for admin user creation (POST)."""
    
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'role', 'phone', 'is_active', 'is_staff']
        extra_kwargs = {
            'role': {'required': False},
            'phone': {'required': False},
            'is_active': {'required': False},
            'is_staff': {'required': False},
        }
    
    def create(self, validated_data: dict) -> User:
        """Create user with hashed password. Auto-set is_staff for admin role."""
        password = validated_data.pop('password')
        role = validated_data.get('role', 'user')
        if role == 'admin':
            validated_data.setdefault('is_staff', True)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'phone']
        extra_kwargs = {
            'phone': {'required': False}
        }
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            phone=validated_data.get('phone', '')
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid email or password')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "email" and "password"')


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request."""
    
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset."""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
