from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.config import settings
from app.middleware.gateway_auth import GatewayAuthMiddleware
from app.schemas.notification import NotificationCreate, NotificationPreferenceUpdate


def create_test_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(GatewayAuthMiddleware)

    @app.get("/health/")
    async def health() -> dict:
        return {"ok": True}

    @app.get("/private")
    async def private(request: Request) -> dict:
        return {
            "user_email": request.state.user_email,
            "user_role": request.state.user_role,
            "is_staff": request.state.is_staff,
        }

    return TestClient(app)


def test_should_bypass_health_without_secret() -> None:
    client = create_test_client()

    response = client.get("/health/")

    assert response.status_code == 200


def test_should_reject_private_request_with_wrong_secret() -> None:
    client = create_test_client()

    response = client.get("/private", headers={"X-Gateway-Secret": "wrong-secret"})

    assert response.status_code == 403


def test_should_apply_default_role_and_email_when_headers_missing() -> None:
    client = create_test_client()

    response = client.get("/private", headers={"X-Gateway-Secret": settings.GATEWAY_SECRET})

    assert response.status_code == 200
    assert response.json() == {
        "user_email": "",
        "user_role": "user",
        "is_staff": False,
    }


def test_should_validate_notification_create_with_camel_case_input() -> None:
    payload = NotificationCreate.model_validate(
        {
            "userId": "u1",
            "notificationType": "system",
            "title": "t",
            "message": "m",
            "data": {"x": 1},
        },
    )

    assert payload.user_id == "u1"
    assert payload.notification_type == "system"


def test_should_serialize_preference_update_to_camel_case() -> None:
    update = NotificationPreferenceUpdate(push_enabled=True, email_enabled=False)
    payload = update.model_dump(by_alias=True)

    assert payload["pushEnabled"] is True
    assert payload["emailEnabled"] is False
