from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.config import settings
from app.middleware.gateway_auth import GatewayAuthMiddleware
from app.schemas.chatbot import ChatRequest, ChatResponse


def create_test_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(GatewayAuthMiddleware)

    @app.get("/health/")
    async def health() -> dict:
        return {"ok": True}

    @app.get("/private")
    async def private(request: Request) -> dict:
        return {
            "user_id": request.state.user_id,
            "user_email": request.state.user_email,
            "user_role": request.state.user_role,
            "is_staff": request.state.is_staff,
        }

    return TestClient(app)


def test_should_bypass_auth_for_exempt_paths() -> None:
    client = create_test_client()

    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_should_return_403_for_invalid_gateway_secret() -> None:
    client = create_test_client()

    response = client.get("/private")

    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_should_inject_user_state_for_valid_gateway_secret() -> None:
    client = create_test_client()

    response = client.get(
        "/private",
        headers={
            "X-Gateway-Secret": settings.GATEWAY_SECRET,
            "X-User-ID": "user-123",
            "X-User-Email": "user@example.com",
            "X-User-Role": "admin",
            "X-User-Is-Staff": "true",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-123",
        "user_email": "user@example.com",
        "user_role": "admin",
        "is_staff": True,
    }


def test_should_serialize_chat_response_to_camel_case() -> None:
    response = ChatResponse(
        response="ok",
        intent="greeting",
        entities={},
        suggestions=[],
        data={},
        conversation_id="conv-1",
        message_id="msg-1",
    )

    payload = response.model_dump(by_alias=True)

    assert payload["conversationId"] == "conv-1"
    assert payload["messageId"] == "msg-1"


def test_should_accept_chat_request_camel_case_alias() -> None:
    request = ChatRequest.model_validate(
        {"message": "hi", "conversationId": "conv-99"},
    )

    assert request.conversation_id == "conv-99"
