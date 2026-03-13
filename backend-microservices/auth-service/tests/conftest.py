"""
Shared test fixtures for auth-service.
"""

import uuid
import pytest
from rest_framework.test import APIClient
from users.models import User

GATEWAY_SECRET = "gateway-internal-secret-key"


@pytest.fixture
def api_client():
    """Pre-configured API client."""
    return APIClient()


@pytest.fixture
def gateway_headers():
    """Return dict of gateway auth headers for a regular user."""
    user_id = str(uuid.uuid4())
    return {
        "HTTP_X_GATEWAY_SECRET": GATEWAY_SECRET,
        "HTTP_X_USER_ID": user_id,
        "HTTP_X_USER_EMAIL": "testuser@parksmart.com",
        "HTTP_X_USER_ROLE": "user",
        "HTTP_X_USER_IS_STAFF": "false",
    }


@pytest.fixture
def admin_gateway_headers():
    """Return dict of gateway auth headers for an admin user."""
    user_id = str(uuid.uuid4())
    return {
        "HTTP_X_GATEWAY_SECRET": GATEWAY_SECRET,
        "HTTP_X_USER_ID": user_id,
        "HTTP_X_USER_EMAIL": "admin@parksmart.com",
        "HTTP_X_USER_ROLE": "admin",
        "HTTP_X_USER_IS_STAFF": "true",
    }


@pytest.fixture
def auth_client(api_client, gateway_headers):
    """API client with gateway auth credentials."""
    api_client.credentials(**gateway_headers)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_gateway_headers):
    """API client with admin gateway auth credentials."""
    client = APIClient()
    client.credentials(**admin_gateway_headers)
    return client


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        email="fixture@parksmart.com",
        username="fixtureuser",
        password="TestPass123!",
        role="user",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(
        email="admin_fixture@parksmart.com",
        username="admin_fixture",
        password="AdminPass123!",
        role="admin",
        is_staff=True,
    )
