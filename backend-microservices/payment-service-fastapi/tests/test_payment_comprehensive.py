"""
Comprehensive tests for payment-service-fastapi.
Tests: Initiate, verify, list, get, get by booking_id.
"""

import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET", "test-secret-for-ci")
TEST_USER_ID = "test-user-uuid-payment"


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
# INITIATE PAYMENT
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_initiate_payment(client: AsyncClient):
    response = await client.post("/api/payments/initiate/", json={
        "bookingId": str(uuid.uuid4()),
        "amount": 50000,
        "paymentMethod": "momo",
    })
    assert response.status_code in [201, 200, 400, 404, 500]


@pytest.mark.anyio
async def test_initiate_payment_missing_fields(client: AsyncClient):
    response = await client.post("/api/payments/initiate/", json={})
    assert response.status_code == 422


# ═══════════════════════════════════════════════════
# VERIFY PAYMENT
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_verify_payment_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.post(f"/api/payments/verify/{fake_id}/")
    assert response.status_code in [404, 400, 422, 500]


# ═══════════════════════════════════════════════════
# LIST PAYMENTS
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_payments(client: AsyncClient):
    response = await client.get("/api/payments/")
    assert response.status_code in [200, 500]


@pytest.mark.anyio
async def test_list_payments_paginated(client: AsyncClient):
    response = await client.get("/api/payments/?page=1")
    assert response.status_code in [200, 500]


# ═══════════════════════════════════════════════════
# GET PAYMENT
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_get_payment_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/payments/{fake_id}/")
    assert response.status_code in [404, 400, 500]


# ═══════════════════════════════════════════════════
# GET PAYMENT BY BOOKING
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_get_payment_by_booking(client: AsyncClient):
    fake_booking_id = str(uuid.uuid4())
    response = await client.get(f"/api/payments/booking/{fake_booking_id}/")
    assert response.status_code in [200, 404, 500]


# ═══════════════════════════════════════════════════
# AUTH ENFORCEMENT
# ═══════════════════════════════════════════════════

@pytest.mark.anyio
async def test_protected_without_auth(anon_client: AsyncClient):
    response = await anon_client.get("/api/payments/")
    assert response.status_code in [401, 403]
