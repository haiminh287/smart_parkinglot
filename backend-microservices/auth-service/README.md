# Auth Service - Smart Parking Management System

Authentication and authorization microservice.

## Features

- Gateway-managed session authentication
- OAuth2 (Google, Facebook)
- User registration/login
- Password reset
- Session management

## API Endpoints

- `POST /auth/login/` - Login with email/password
- `POST /auth/register/` - Register new user
- `POST /auth/logout/` - Logout
- `GET /auth/google/` - Get Google OAuth2 URL
- `GET /auth/facebook/` - Get Facebook OAuth2 URL
- `GET /auth/me/` - Get current user info
- `POST /auth/change-password/` - Change password
- `POST /auth/forgot-password/` - Send password reset email
- `POST /auth/reset-password/` - Reset password with token

## Auth Contract Note

- Runtime hiện tại dùng gateway session cookie và không expose token refresh endpoint.
- Các request dạng `/auth/refresh/` hoặc `/auth/token/refresh/` không thuộc contract được support.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Run server
python manage.py runserver 8000
```

## Environment Variables

```
DATABASE_URL=postgresql://auth_user:auth_password@postgres:5432/auth_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<django-secret>
JWT_SECRET_KEY=<jwt-secret>
JWT_ACCESS_TOKEN_LIFETIME=30
JWT_REFRESH_TOKEN_LIFETIME=10080
GOOGLE_CLIENT_ID=<google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<google-oauth-secret>
FACEBOOK_APP_ID=<facebook-app-id>
FACEBOOK_APP_SECRET=<facebook-app-secret>
```
