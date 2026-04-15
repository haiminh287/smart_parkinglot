"""
Django settings for auth_service project.
"""

import os
from pathlib import Path
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ENV = config('ENV', default='development')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# Application definition
INSTALLED_APPS = [
    # 'django.contrib.admin',  # Disabled — gateway trust model, no admin interface
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    
    # Local apps
    'users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'shared.gateway_middleware.GatewayAuthMiddleware',  # Gateway auth
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'auth_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'auth_service.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'parksmartdb',
        'USER': os.environ['DB_USER'],       # Required: set DB_USER in environment
        'PASSWORD': os.environ['DB_PASSWORD'],  # Required: set DB_PASSWORD in environment
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3307'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Custom authentication backend for UUID primary keys
AUTHENTICATION_BACKENDS = [
    'users.backends.UUIDModelBackend',  # Support UUID PKs in sessions
]

# REST Framework with CamelCase for frontend TypeScript compatibility
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Redis
REDIS_URL = config('REDIS_URL')

# OAuth2 Settings
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')
GOOGLE_REDIRECT_URI = config('GOOGLE_REDIRECT_URI', default='http://localhost:8001/api/auth/google/callback/')
FACEBOOK_APP_ID = config('FACEBOOK_APP_ID', default='')
FACEBOOK_APP_SECRET = config('FACEBOOK_APP_SECRET', default='')
FACEBOOK_REDIRECT_URI = config('FACEBOOK_REDIRECT_URI', default='http://localhost:8001/api/auth/facebook/callback/')
OAUTH_STATE_SECRET = config('OAUTH_STATE_SECRET', default=SECRET_KEY)
OAUTH_STATE_TTL_SECONDS = config('OAUTH_STATE_TTL_SECONDS', default=300, cast=int)

raw_cors_allowed_origins = config('CORS_ALLOWED_ORIGINS', default='')
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in raw_cors_allowed_origins.split(',')
    if origin.strip()
]
SESSION_COOKIE_DOMAIN = config('SESSION_COOKIE_DOMAIN', default='').strip()
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

if ENV.lower() == 'production':
    if not SESSION_COOKIE_DOMAIN:
        raise ImproperlyConfigured('SESSION_COOKIE_DOMAIN is required when ENV=production')
    if not SESSION_COOKIE_SECURE:
        raise ImproperlyConfigured('SESSION_COOKIE_SECURE must be true when ENV=production')
    if not CSRF_COOKIE_SECURE:
        raise ImproperlyConfigured('CSRF_COOKIE_SECURE must be true when ENV=production')
    if not CORS_ALLOWED_ORIGINS:
        raise ImproperlyConfigured('CORS_ALLOWED_ORIGINS is required when ENV=production')
    for origin in CORS_ALLOWED_ORIGINS:
        lower_origin = origin.lower()
        if not lower_origin.startswith('https://'):
            raise ImproperlyConfigured('CORS_ALLOWED_ORIGINS must use https:// when ENV=production')
        if 'localhost' in lower_origin or '127.0.0.1' in lower_origin:
            raise ImproperlyConfigured('CORS_ALLOWED_ORIGINS cannot include localhost when ENV=production')

# Gateway authentication - All requests must come through gateway
# Required: GATEWAY_SECRET must be set in environment, no insecure default allowed
GATEWAY_SECRET = config('GATEWAY_SECRET')
