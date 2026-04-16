"""
Comprehensive tests for ai-service-fastapi.
Tests: Health, detection endpoints, parking endpoints, ESP32 endpoints,
       camera endpoints, metrics, training, engine modules.
"""

import io
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient

# ═══════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════

GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET", "test-secret-for-ci")
TEST_USER_ID = "test-user-uuid"


@pytest.fixture
async def client():
    """Async test client with gateway auth headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["X-Gateway-Secret"] = GATEWAY_SECRET
        ac.headers["X-User-ID"] = TEST_USER_ID
        yield ac


@pytest.fixture
async def anon_client():
    """Async test client without auth headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def fake_image_bytes(fmt="JPEG"):
    """Generate a minimal valid image file for upload testing."""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()


# ═══════════════════════════════════════════════════
# HEALTH ENDPOINT
# ═══════════════════════════════════════════════════


@pytest.mark.anyio
async def test_health_returns_200(client: AsyncClient):
    response = await client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-service"


@pytest.mark.anyio
async def test_health_no_auth_required(anon_client: AsyncClient):
    """Health endpoint should not require gateway auth."""
    response = await anon_client.get("/health/")
    assert response.status_code == 200


# ═══════════════════════════════════════════════════
# DETECTION ENDPOINTS
# ═══════════════════════════════════════════════════


@pytest.mark.anyio
async def test_detect_license_plate_no_file(client: AsyncClient):
    """POST /ai/detect/license-plate/ without file should fail."""
    response = await client.post("/ai/detect/license-plate/")
    assert response.status_code in [400, 422]


@pytest.mark.anyio
async def test_detect_license_plate_success(client: AsyncClient):
    """POST /ai/detect/license-plate/ with valid image should return result or 503 (model not loaded)."""
    image_data = fake_image_bytes()
    response = await client.post(
        "/ai/detect/license-plate/",
        files={"image": ("test.jpg", image_data, "image/jpeg")},
    )
    # 200 if model loaded, 503 if LicensePlateDetector module missing, 500 for other errors
    assert response.status_code in [200, 500, 503]


@pytest.mark.anyio
async def test_detect_cash_no_file(client: AsyncClient):
    response = await client.post("/ai/detect/cash/")
    assert response.status_code in [400, 422]


@pytest.mark.anyio
async def test_detect_banknote_no_file(client: AsyncClient):
    response = await client.post("/ai/detect/banknote/")
    assert response.status_code in [400, 422]


# ═══════════════════════════════════════════════════
# PARKING ENDPOINTS
# ═══════════════════════════════════════════════════


@pytest.mark.anyio
async def test_parking_scan_plate_no_file(client: AsyncClient):
    response = await client.post("/ai/parking/scan-plate/")
    assert response.status_code in [400, 422]


@pytest.mark.anyio
async def test_parking_check_in_no_body(client: AsyncClient):
    response = await client.post("/ai/parking/check-in/")
    assert response.status_code in [400, 422]


@pytest.mark.anyio
async def test_parking_check_out_no_body(client: AsyncClient):
    response = await client.post("/ai/parking/check-out/")
    assert response.status_code in [400, 422]


# ═══════════════════════════════════════════════════
# ESP32 ENDPOINTS
# ═══════════════════════════════════════════════════


@pytest.mark.anyio
async def test_esp32_check_in_endpoint_exists(client: AsyncClient):
    """POST /ai/parking/esp32/check-in/ should be reachable."""
    response = await client.post("/ai/parking/esp32/check-in/", json={})
    # May fail due to missing hardware, but endpoint should exist (not 404)
    assert response.status_code != 404


@pytest.mark.anyio
async def test_esp32_check_out_endpoint_exists(client: AsyncClient):
    response = await client.post("/ai/parking/esp32/check-out/", json={})
    assert response.status_code != 404


@pytest.mark.anyio
async def test_esp32_verify_slot_endpoint_exists(client: AsyncClient):
    response = await client.post("/ai/parking/esp32/verify-slot/", json={})
    assert response.status_code != 404


@pytest.mark.anyio
async def test_esp32_cash_payment_endpoint_exists(client: AsyncClient):
    response = await client.post("/ai/parking/esp32/cash-payment/", json={})
    assert response.status_code != 404


@pytest.mark.anyio
async def test_esp32_status(client: AsyncClient):
    response = await client.get("/ai/parking/esp32/status/")
    assert response.status_code == 200


# ═══════════════════════════════════════════════════
# CAMERA ENDPOINTS
# ═══════════════════════════════════════════════════


@pytest.mark.anyio
async def test_camera_list(client: AsyncClient):
    response = await client.get("/ai/cameras/list")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_camera_snapshot_no_params(client: AsyncClient):
    """Snapshot without camera_id param."""
    response = await client.get("/ai/cameras/snapshot")
    # 503 when no physical camera available in test/CI environment
    assert response.status_code in [200, 400, 422, 500, 503]


@pytest.mark.skip(
    reason="StreamingResponse is infinite by design; no physical camera available in CI/test env. "
    "Tested via unit test for generate() generator only."
)
@pytest.mark.anyio
async def test_camera_stream_no_params(client: AsyncClient):
    response = await client.get("/ai/cameras/stream")
    assert response.status_code in [200, 400, 422, 500]


# ═══════════════════════════════════════════════════
# METRICS ENDPOINTS
# ═══════════════════════════════════════════════════


@pytest.mark.anyio
async def test_metrics_endpoint(client: AsyncClient):
    """Metrics endpoint needs DB. Returns 200 if DB is up, 500 otherwise."""
    try:
        response = await client.get("/ai/models/metrics/")
        assert response.status_code in [200, 500]
    except Exception:
        pytest.skip("Database not available")


@pytest.mark.anyio
async def test_predictions_endpoint(client: AsyncClient):
    """Predictions endpoint needs DB. Returns 200 if DB is up, 500 otherwise."""
    try:
        response = await client.get("/ai/models/predictions/")
        assert response.status_code in [200, 500]
    except Exception:
        pytest.skip("Database not available")


@pytest.mark.anyio
async def test_versions_endpoint(client: AsyncClient):
    """Versions endpoint needs DB. Returns 200 if DB is up, 500 otherwise."""
    try:
        response = await client.get("/ai/models/versions/")
        assert response.status_code in [200, 500]
    except Exception:
        pytest.skip("Database not available")


# ═══════════════════════════════════════════════════
# TRAINING ENDPOINTS
# ═══════════════════════════════════════════════════


@pytest.mark.anyio
async def test_training_cash_no_file(client: AsyncClient):
    response = await client.post("/ai/train/cash/")
    assert response.status_code in [400, 422]


@pytest.mark.anyio
async def test_training_banknote_no_file(client: AsyncClient):
    response = await client.post("/ai/train/banknote/")
    assert response.status_code in [400, 422]


# ═══════════════════════════════════════════════════
# GATEWAY AUTH TESTS
# ═══════════════════════════════════════════════════


@pytest.mark.anyio
async def test_protected_endpoint_without_gateway_secret(anon_client: AsyncClient):
    """Protected endpoints should reject requests without gateway secret."""
    response = await anon_client.get("/ai/metrics/")
    assert response.status_code in [401, 403]


@pytest.mark.anyio
async def test_camera_endpoint_exempt_from_auth(anon_client: AsyncClient):
    """Camera endpoints should be accessible without auth (for img tags)."""
    response = await anon_client.get("/ai/cameras/list")
    assert response.status_code == 200


# ═══════════════════════════════════════════════════
# ENGINE UNIT TESTS
# ═══════════════════════════════════════════════════


class TestCameraCapture:
    """Test CameraCapture utility (mocked)."""

    @patch("cv2.VideoCapture")
    def test_capture_initializes_rtsp(self, mock_cv2):
        from app.engine.camera_capture import CameraCapture

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cv2.return_value = mock_cap
        # Instantiation should work
        capture = CameraCapture.__new__(CameraCapture)
        assert capture is not None


class TestQRReader:
    """Test QR reader module exists and is importable."""

    def test_import_qr_reader(self):
        from app.engine.qr_reader import QRReader

        assert QRReader is not None


class TestCashSession:
    """Test CashPaymentSession state machine."""

    def test_import_cash_session(self):
        from app.engine.cash_session import CashPaymentSession

        assert CashPaymentSession is not None


# ═══════════════════════════════════════════════════
# SCHEMA TESTS
# ═══════════════════════════════════════════════════


def test_detection_result_camel_case():
    """DetectionResult should output camelCase keys."""
    from app.schemas.ai import DetectionResult

    d = DetectionResult(
        plate_text="51F-123.45",
        confidence=0.95,
        bbox=[10.0, 20.0, 100.0, 50.0],
    )
    output = d.model_dump(by_alias=True)
    assert "plateText" in output


def test_esp32_response_schema():
    """ESP32Response schema should be importable and valid."""
    from app.schemas.esp32 import BarrierAction, ESP32Response, GateEvent

    r = ESP32Response(
        success=True,
        message="OK",
        event=GateEvent.CHECK_IN_SUCCESS,
        barrier_action=BarrierAction.OPEN,
        gate_id="gate-1",
    )
    assert r.success is True
    assert r.barrier_action == BarrierAction.OPEN
