"""
Smoke tests for notification-service-fastapi.
Verifies health endpoint and __tablename__ mapping.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.notification import Notification, NotificationPreference


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["X-Gateway-Secret"] = "gateway-internal-secret-key"
        ac.headers["X-User-ID"] = "test-user-uuid"
        yield ac


# ─── Health Check ─────────────────────────────────

@pytest.mark.anyio
async def test_health_returns_200(client: AsyncClient):
    """GET /health/ should return 200 with service info."""
    response = await client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "notification-service"


# ─── Data Integrity: __tablename__ Mapping ────────

def test_notification_tablename():
    """Notification model must map to Django table name."""
    assert Notification.__tablename__ == "notifications_notification", (
        f"Expected 'notifications_notification', got '{Notification.__tablename__}'"
    )


def test_notification_preference_tablename():
    """NotificationPreference model must map to Django table name."""
    assert NotificationPreference.__tablename__ == "notifications_notificationpreference", (
        f"Expected 'notifications_notificationpreference', got '{NotificationPreference.__tablename__}'"
    )


# ─── CamelCase Output ────────────────────────────

def test_notification_schema_camelcase():
    """NotificationResponse should output camelCase keys."""
    from app.schemas.notification import NotificationResponse
    from datetime import datetime

    n = NotificationResponse(
        id="test-id",
        user_id="user-1",
        notification_type="booking",
        title="Test",
        message="Hello",
        data={},
        is_read=False,
        push_sent=False,
        email_sent=False,
        sms_sent=False,
        created_at=datetime.utcnow(),
    )
    output = n.model_dump(by_alias=True)
    assert "userId" in output, f"Expected camelCase 'userId', got keys: {list(output.keys())}"
    assert "notificationType" in output
    assert "isRead" in output
    assert "pushSent" in output
