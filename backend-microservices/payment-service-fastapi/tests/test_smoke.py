"""
Smoke tests for payment-service-fastapi.
Verifies health endpoint and __tablename__ mapping.
"""

import os

import pytest
from app.main import app
from app.models.payment import Payment
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["X-Gateway-Secret"] = os.environ.get(
            "GATEWAY_SECRET", "test-secret-for-ci"
        )
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
    assert data["service"] == "payment-service"


# ─── Data Integrity: __tablename__ Mapping ────────


def test_payment_tablename():
    """Payment model must map to Django table name."""
    assert (
        Payment.__tablename__ == "payments_payment"
    ), f"Expected 'payments_payment', got '{Payment.__tablename__}'"


# ─── CamelCase Output ────────────────────────────


def test_payment_schema_camelcase():
    """PaymentResponse should output camelCase keys."""
    from decimal import Decimal

    from app.schemas.payment import PaymentResponse

    p = PaymentResponse(
        id="pay-1",
        booking_id="book-1",
        user_id="user-1",
        payment_method="momo",
        amount=Decimal("50000"),
        status="pending",
    )
    output = p.model_dump(by_alias=True)
    assert (
        "bookingId" in output
    ), f"Expected camelCase 'bookingId', got keys: {list(output.keys())}"
    assert "userId" in output
    assert "paymentMethod" in output
    assert "paymentMethod" in output
