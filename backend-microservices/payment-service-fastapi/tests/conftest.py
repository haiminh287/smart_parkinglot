"""
Shared test fixtures for payment-service-fastapi.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings

GATEWAY_SECRET = settings.GATEWAY_SECRET
TEST_USER_ID = "test-user-uuid-001"
TEST_USER_EMAIL = "testuser@parksmart.com"


@pytest.fixture
async def client():
    """Async test client with gateway auth headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["X-Gateway-Secret"] = GATEWAY_SECRET
        ac.headers["X-User-ID"] = TEST_USER_ID
        ac.headers["X-User-Email"] = TEST_USER_EMAIL
        ac.headers["X-User-Role"] = "user"
        ac.headers["X-User-Is-Staff"] = "false"
        yield ac


@pytest.fixture
async def anon_client():
    """Async test client without auth headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
