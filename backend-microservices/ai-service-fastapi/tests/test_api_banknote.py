"""
API endpoint tests for banknote recognition.
Tests the /ai/detect/banknote/ endpoint via ASGI transport.
"""

import os
import io
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
import numpy as np

from app.main import app


GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET", "test-secret-for-ci")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["X-Gateway-Secret"] = GATEWAY_SECRET
        ac.headers["X-User-ID"] = "test-user-uuid"
        yield ac


def make_test_image_bytes() -> bytes:
    """Create a valid PNG image in memory."""
    import cv2
    img = np.full((100, 100, 3), [55, 200, 200], dtype=np.uint8)  # green in HSV
    img_bgr = cv2.cvtColor(img, cv2.COLOR_HSV2BGR)
    _, buffer = cv2.imencode(".png", img_bgr)
    return buffer.tobytes()


# ─── Route Prefix Tests ─────────────────────────

class TestRoutePrefixes:
    """Verify all routes use /ai/ prefix for gateway compatibility."""

    @pytest.mark.anyio
    async def test_detect_banknote_prefix(self, client: AsyncClient):
        """POST /ai/detect/banknote/ should be reachable."""
        img_bytes = make_test_image_bytes()
        # Mock DB to avoid connection
        with patch("app.routers.detection.get_db"):
            response = await client.post(
                "/ai/detect/banknote/",
                files={"image": ("test.png", img_bytes, "image/png")},
            )
        # Should not be 404 (route exists)
        assert response.status_code != 404

    @pytest.mark.anyio
    async def test_detect_license_plate_prefix(self, client: AsyncClient):
        """POST /ai/detect/license-plate/ should exist (503 OK — no ML model)."""
        img_bytes = make_test_image_bytes()
        with patch("app.routers.detection.get_db"):
            response = await client.post(
                "/ai/detect/license-plate/",
                files={"image": ("test.png", img_bytes, "image/png")},
            )
        assert response.status_code != 404

    @pytest.mark.anyio
    async def test_train_prefix(self, client: AsyncClient):
        """POST /ai/train/banknote/ should exist."""
        response = await client.post(
            "/ai/train/banknote/",
            json={"dataDir": "/tmp/data"},
        )
        assert response.status_code != 404

    @pytest.mark.anyio
    async def test_models_prefix(self, client: AsyncClient):
        """GET /ai/models/metrics/ should exist (may fail on DB but not 404)."""
        from app.database import get_db

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            response = await client.get("/ai/models/metrics/")
            assert response.status_code != 404
        finally:
            app.dependency_overrides.pop(get_db, None)


# ─── Banknote Detection Endpoint ────────────────

class TestBanknoteEndpoint:
    """Tests for POST /ai/detect/banknote/ endpoint."""

    @pytest.mark.anyio
    async def test_banknote_full_mode(self, client: AsyncClient):
        """Full mode pipeline should return complete response."""
        img_bytes = make_test_image_bytes()

        # Mock DB dependency
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch("app.routers.detection.get_db", return_value=iter([mock_db])):
            response = await client.post(
                "/ai/detect/banknote/?mode=full",
                files={"image": ("banknote.png", img_bytes, "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "decision" in data
        assert "denomination" in data
        assert "confidence" in data
        assert "method" in data
        assert "quality" in data
        assert "pipelineVersion" in data
        assert data["pipelineVersion"] == "hybrid-mvp-v1"

    @pytest.mark.anyio
    async def test_banknote_fast_mode(self, client: AsyncClient):
        """Fast mode should skip AI fallback."""
        img_bytes = make_test_image_bytes()

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch("app.routers.detection.get_db", return_value=iter([mock_db])):
            response = await client.post(
                "/ai/detect/banknote/?mode=fast",
                files={"image": ("banknote.png", img_bytes, "image/png")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "ai_fallback" not in data.get("stagesExecuted", [])

    @pytest.mark.anyio
    async def test_banknote_response_has_quality_info(self, client: AsyncClient):
        """Response should include quality gate information."""
        img_bytes = make_test_image_bytes()

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch("app.routers.detection.get_db", return_value=iter([mock_db])):
            response = await client.post(
                "/ai/detect/banknote/",
                files={"image": ("banknote.png", img_bytes, "image/png")},
            )

        data = response.json()
        quality = data.get("quality")
        assert quality is not None
        assert "blurScore" in quality
        assert "exposureScore" in quality
        assert "status" in quality

    @pytest.mark.anyio
    async def test_banknote_response_has_stages(self, client: AsyncClient):
        """Response should list executed stages."""
        img_bytes = make_test_image_bytes()

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        with patch("app.routers.detection.get_db", return_value=iter([mock_db])):
            response = await client.post(
                "/ai/detect/banknote/",
                files={"image": ("banknote.png", img_bytes, "image/png")},
            )

        data = response.json()
        stages = data.get("stagesExecuted", [])
        assert "preprocessing" in stages
        assert "detection" in stages

    @pytest.mark.anyio
    async def test_invalid_file_type_rejected(self, client: AsyncClient):
        """Non-image file should be rejected."""
        mock_db = MagicMock()

        with patch("app.routers.detection.get_db", return_value=iter([mock_db])):
            response = await client.post(
                "/ai/detect/banknote/",
                files={"image": ("test.txt", b"hello world", "text/plain")},
            )

        assert response.status_code == 400


# ─── Gateway Auth Tests ─────────────────────────

class TestGatewayAuth:
    @pytest.mark.anyio
    async def test_no_gateway_secret_rejected(self):
        """Request without gateway secret should be rejected."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/ai/models/metrics/")
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_wrong_gateway_secret_rejected(self):
        """Request with wrong gateway secret should be rejected."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["X-Gateway-Secret"] = "wrong-secret"
            response = await ac.get("/ai/models/metrics/")
        assert response.status_code == 403
