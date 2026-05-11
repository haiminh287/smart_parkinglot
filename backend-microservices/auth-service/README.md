# Auth Service - Smart Parking Management System

Authentication and authorization microservice.

## Features

- Gateway-managed session authentication
- OAuth2 (Google)
- User registration/login
- Password reset
- Session management

## API Endpoints

- `POST /auth/login/` - Login with email/password
- `POST /auth/register/` - Register new user
- `POST /auth/logout/` - Logout
- `GET /auth/google/` - Get Google OAuth2 URL
- `GET /auth/me/` - Get current user info
- `POST /auth/change-password/` - Change password
- `POST /auth/forgot-password/` - Send password reset email
- `POST /auth/reset-password/` - Reset password with token

## Auth Contract Note

- **Session cookie-based auth (NO JWT refresh token endpoint).** Gateway quản lý session cookie; không có `/auth/refresh/` hay `/auth/token/refresh/` endpoint.
- Các request dạng `/auth/refresh/` hoặc `/auth/token/refresh/` bị gateway reject cố ý (`HandleUnsupportedRefresh`).
- Biến `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_LIFETIME`, `JWT_REFRESH_TOKEN_LIFETIME` từ các phiên bản cũ đã được loại bỏ khỏi contract.

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
SECRET_KEY=<django-secret>
DB_HOST=mysql
DB_PORT=3306
DB_NAME=parksmartdb
DB_USER=<mysql-user>
DB_PASSWORD=<mysql-password>
REDIS_URL=redis://redis:6379/1
GATEWAY_SECRET=<shared-secret-with-gateway>
GOOGLE_CLIENT_ID=<google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<google-oauth-secret>
```

**Lưu ý:** Runtime hiện tại dùng **MySQL** (không phải PostgreSQL) và
xác thực dựa trên **session cookie** quản lý bởi Gateway Service
(không có JWT refresh token). Các biến `DATABASE_URL`, `JWT_SECRET_KEY`,
`JWT_ACCESS_TOKEN_LIFETIME`, `JWT_REFRESH_TOKEN_LIFETIME` đã bị loại bỏ.
