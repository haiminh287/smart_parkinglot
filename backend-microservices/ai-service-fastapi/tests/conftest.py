"""
Shared test fixtures for ai-service-fastapi.
"""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
async def admin_client():
    """Async test client with admin gateway auth headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["X-Gateway-Secret"] = GATEWAY_SECRET
        ac.headers["X-User-ID"] = "admin-user-uuid-001"
        ac.headers["X-User-Email"] = "admin@parksmart.com"
        ac.headers["X-User-Role"] = "admin"
        ac.headers["X-User-Is-Staff"] = "true"
        yield ac


@pytest.fixture
async def anon_client():
    """Async test client without auth headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def fake_image_bytes():
    """Generate a small valid JPEG image for upload tests."""
    try:
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf.read()
    except ImportError:
        # Minimal JPEG header if Pillow not available
        return b"\xff\xd8\xff\xe0" + b"\x00" * 100
