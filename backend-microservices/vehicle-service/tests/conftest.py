"""
Shared test fixtures for vehicle-service.
"""

import uuid
import pytest
from rest_framework.test import APIClient

GATEWAY_SECRET = "gateway-internal-secret-key"
TEST_USER_ID = str(uuid.uuid4())


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def gateway_headers():
    return {
        "HTTP_X_GATEWAY_SECRET": GATEWAY_SECRET,
        "HTTP_X_USER_ID": TEST_USER_ID,
        "HTTP_X_USER_EMAIL": "testuser@parksmart.com",
        "HTTP_X_USER_ROLE": "user",
        "HTTP_X_USER_IS_STAFF": "false",
    }


@pytest.fixture
def auth_client(api_client, gateway_headers):
    api_client.credentials(**gateway_headers)
    return api_client
