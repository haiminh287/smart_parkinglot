from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.config import settings
from app.middleware.gateway_auth import GatewayAuthMiddleware
from app.schemas.payment import PaymentInitiateRequest, PaymentResponse


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
            "is_staff": request.state.is_staff,
        }

    return TestClient(app)


def test_should_allow_health_without_gateway_secret() -> None:
    client = create_test_client()

    response = client.get("/health/")

    assert response.status_code == 200


def test_should_reject_private_without_gateway_secret() -> None:
    client = create_test_client()

    response = client.get("/private")

    assert response.status_code == 403


def test_should_set_staff_flag_from_header() -> None:
    client = create_test_client()

    response = client.get(
        "/private",
        headers={
            "X-Gateway-Secret": settings.GATEWAY_SECRET,
            "X-User-ID": "u1",
            "X-User-Is-Staff": "false",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": "u1", "is_staff": False}


def test_should_validate_payment_request_from_camel_case_fields() -> None:
    request = PaymentInitiateRequest.model_validate(
        {
            "bookingId": "book-1",
            "paymentMethod": "momo",
            "amount": "10000.50",
        },
    )

    assert request.booking_id == "book-1"
    assert request.amount == Decimal("10000.50")


def test_should_serialize_payment_response_to_camel_case() -> None:
    response = PaymentResponse(
        id="pay-1",
        booking_id="book-1",
        user_id="user-1",
        payment_method="momo",
        amount=Decimal("12000"),
        status="pending",
    )

    payload = response.model_dump(by_alias=True)

    assert payload["bookingId"] == "book-1"
    assert payload["paymentMethod"] == "momo"
