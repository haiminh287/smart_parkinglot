"""
Comprehensive tests for chatbot-service-fastapi.
Tests: Chat, conversations CRUD, quick-actions, feedback,
       notifications, actions, preferences.
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


GATEWAY_SECRET = "gateway-internal-secret-key"
TEST_USER_ID = "test-user-uuid-chatbot"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["X-Gateway-Secret"] = GATEWAY_SECRET
        ac.headers["X-User-ID"] = TEST_USER_ID
        yield ac


@pytest.fixture
async def anon_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ═══════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_health(client: AsyncClient):
    response = await client.get("/health/")
    assert response.status_code == 200


# ═══════════════════════════════════════════════════
# CHAT ENDPOINT
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_chat_send_message(client: AsyncClient):
    response = await client.post("/chatbot/chat/", json={
        "message": "Xin chào, tôi muốn đặt chỗ đậu xe",
    })
    assert response.status_code in [200, 201]
    data = response.json()
    assert "response" in data or "message" in data or "reply" in data


@pytest.mark.anyio
async def test_chat_empty_message(client: AsyncClient):
    response = await client.post("/chatbot/chat/", json={
        "message": "",
    })
    assert response.status_code in [200, 400, 422]


@pytest.mark.anyio
async def test_chat_with_conversation_id(client: AsyncClient):
    conv_id = str(uuid.uuid4())
    response = await client.post("/chatbot/chat/", json={
        "message": "Tôi muốn hủy booking",
        "conversation_id": conv_id,
    })
    assert response.status_code in [200, 201, 404]


# ═══════════════════════════════════════════════════
# QUICK ACTIONS
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_quick_actions(client: AsyncClient):
    response = await client.get("/chatbot/quick-actions/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


# ═══════════════════════════════════════════════════
# FEEDBACK
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_feedback_submit(client: AsyncClient):
    response = await client.post("/chatbot/feedback/", json={
        "conversationId": str(uuid.uuid4()),
        "rating": 5,
        "comment": "Very helpful!",
    })
    assert response.status_code in [200, 201, 404, 422]


# ═══════════════════════════════════════════════════
# CONVERSATIONS
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_conversations(client: AsyncClient):
    response = await client.get("/chatbot/conversations/")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_create_conversation(client: AsyncClient):
    response = await client.post("/chatbot/conversations/", json={})
    assert response.status_code in [200, 201]


@pytest.mark.anyio
async def test_get_active_conversation(client: AsyncClient):
    response = await client.get("/chatbot/conversations/active/")
    assert response.status_code in [200, 404]


@pytest.mark.anyio
async def test_get_conversation_by_id(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/chatbot/conversations/{fake_id}/")
    assert response.status_code in [200, 404]


@pytest.mark.anyio
async def test_get_conversation_messages(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/chatbot/conversations/{fake_id}/messages/")
    assert response.status_code in [200, 404]


@pytest.mark.anyio
async def test_latest_history(client: AsyncClient):
    response = await client.get("/chatbot/conversations/history/latest/")
    assert response.status_code == 200


# ═══════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_actions(client: AsyncClient):
    response = await client.get("/chatbot/actions/")
    assert response.status_code == 200


# ═══════════════════════════════════════════════════
# PREFERENCES
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_get_preferences(client: AsyncClient):
    response = await client.get("/chatbot/preferences/")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_update_preferences(client: AsyncClient):
    response = await client.put("/chatbot/preferences/", json={
        "favorite_lot_id": str(uuid.uuid4()),
    })
    assert response.status_code in [200, 422]


# ═══════════════════════════════════════════════════
# CHATBOT NOTIFICATIONS
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_chatbot_notifications(client: AsyncClient):
    response = await client.get("/chatbot/notifications/")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_action_on_notification(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.post(f"/chatbot/notifications/{fake_id}/", json={
        "action": "acknowledge",
    })
    assert response.status_code in [200, 404]


# ═══════════════════════════════════════════════════
# AUTH ENFORCEMENT
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_protected_without_auth(anon_client: AsyncClient):
    response = await anon_client.post("/chatbot/chat/", json={"message": "hello"})
    assert response.status_code in [401, 403]
