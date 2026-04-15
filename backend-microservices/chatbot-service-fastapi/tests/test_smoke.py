"""
Smoke tests for chatbot-service-fastapi.
Verifies health endpoint, __tablename__ mapping, and route prefixes.
"""

import os
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.chatbot import (
    Conversation,
    ChatMessage,
    UserPreferences,
    UserBehavior,
    UserCommunicationStyle,
    ConversationSummary,
    ProactiveNotification,
    ActionLog,
    AIMetricLog,
)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["X-Gateway-Secret"] = os.environ.get("GATEWAY_SECRET", "test-secret-for-ci")
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
    assert data["service"] == "chatbot-service"
    assert data["version"] == "3.0.0"


# ─── Data Integrity: __tablename__ Mapping ────────

EXPECTED_TABLE_NAMES = {
    "Conversation": "chatbot_conversation",
    "ChatMessage": "chatbot_chatmessage",
    "UserPreferences": "chatbot_user_preferences",
    "UserBehavior": "chatbot_user_behavior",
    "UserCommunicationStyle": "chatbot_user_communication_style",
    "ConversationSummary": "chatbot_conversation_summary",
    "ProactiveNotification": "chatbot_proactive_notification",
    "ActionLog": "chatbot_action_log",
    "AIMetricLog": "chatbot_ai_metric_log",
}


@pytest.mark.parametrize("model_cls,expected_name", [
    (Conversation, "chatbot_conversation"),
    (ChatMessage, "chatbot_chatmessage"),
    (UserPreferences, "chatbot_user_preferences"),
    (UserBehavior, "chatbot_user_behavior"),
    (UserCommunicationStyle, "chatbot_user_communication_style"),
    (ConversationSummary, "chatbot_conversation_summary"),
    (ProactiveNotification, "chatbot_proactive_notification"),
    (ActionLog, "chatbot_action_log"),
    (AIMetricLog, "chatbot_ai_metric_log"),
])
def test_chatbot_tablename(model_cls, expected_name):
    """Chatbot models must map to correct Django table names."""
    assert model_cls.__tablename__ == expected_name, (
        f"{model_cls.__name__}: expected '{expected_name}', got '{model_cls.__tablename__}'"
    )


# ─── CamelCase Output ────────────────────────────

def test_conversation_schema_camelcase():
    """ConversationResponse should output camelCase keys."""
    from app.schemas.chatbot import ConversationResponse
    from datetime import datetime

    c = ConversationResponse(
        id="conv-1",
        user_id="user-1",
        current_state="idle",
        total_turns=0,
        clarification_count=0,
        handoff_requested=False,
        created_at=datetime.utcnow(),
    )
    output = c.model_dump(by_alias=True)
    assert "userId" in output, f"Expected camelCase 'userId', got keys: {list(output.keys())}"
    assert "currentState" in output
    assert "totalTurns" in output
    assert "handoffRequested" in output


# ─── Route Prefix Validation ─────────────────────

def test_chat_router_prefix():
    """Chat router must use /chatbot prefix (gateway sends /chatbot/...)."""
    from app.routers.chat import router
    assert router.prefix == "/chatbot", f"Expected '/chatbot', got '{router.prefix}'"


def test_conversation_router_prefix():
    """Conversation router must use /chatbot/conversations prefix."""
    from app.routers.conversation import router
    assert router.prefix == "/chatbot/conversations", (
        f"Expected '/chatbot/conversations', got '{router.prefix}'"
    )


def test_preferences_router_prefix():
    """Preferences router must use /chatbot/preferences prefix."""
    from app.routers.preferences import router
    assert router.prefix == "/chatbot/preferences", (
        f"Expected '/chatbot/preferences', got '{router.prefix}'"
    )


def test_notifications_router_prefix():
    """Notifications router must use /chatbot/notifications prefix."""
    from app.routers.notifications import router
    assert router.prefix == "/chatbot/notifications", (
        f"Expected '/chatbot/notifications', got '{router.prefix}'"
    )


def test_actions_router_prefix():
    """Actions router must use /chatbot/actions prefix."""
    from app.routers.actions import router
    assert router.prefix == "/chatbot/actions", (
        f"Expected '/chatbot/actions', got '{router.prefix}'"
    )


# ─── Endpoint Registration ───────────────────────

@pytest.mark.anyio
async def test_chat_endpoint_registered(client: AsyncClient):
    """POST /chatbot/chat/ must be a registered route (even if it needs auth)."""
    # We send an empty body to trigger validation error (not 404)
    response = await client.post("/chatbot/chat/", json={})
    assert response.status_code != 404, "POST /chatbot/chat/ returned 404 — route not registered"


@pytest.mark.anyio
async def test_quick_actions_endpoint(client: AsyncClient):
    """GET /chatbot/quick-actions/ should return quick actions."""
    response = await client.get("/chatbot/quick-actions/")
    assert response.status_code == 200
    data = response.json()
    assert "quickActions" in data
    assert len(data["quickActions"]) > 0
