"""
Smoke tests for ai-service-fastapi.
Verifies health endpoint and __tablename__ mapping.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.ai import CameraFeed, PredictionLog, ModelVersion


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
    assert data["service"] == "ai-service"


# ─── Data Integrity: __tablename__ Mapping ────────

@pytest.mark.parametrize("model_cls,expected_name", [
    (CameraFeed, "api_camerafeed"),
    (PredictionLog, "api_predictionlog"),
    (ModelVersion, "api_modelversion"),
])
def test_ai_tablename(model_cls, expected_name):
    """AI models must map to correct Django table names."""
    assert model_cls.__tablename__ == expected_name, (
        f"{model_cls.__name__}: expected '{expected_name}', got '{model_cls.__tablename__}'"
    )


# ─── CamelCase Output ────────────────────────────

def test_detection_schema_camelcase():
    """DetectionResult should output camelCase keys."""
    from app.schemas.ai import DetectionResult

    d = DetectionResult(
        plate_text="51F-123.45",
        confidence=0.95,
        bbox=[10.0, 20.0, 100.0, 50.0],
    )
    output = d.model_dump(by_alias=True)
    assert "plateText" in output, f"Expected camelCase 'plateText', got keys: {list(output.keys())}"


def test_model_version_schema_camelcase():
    """ModelVersionResponse should output camelCase keys."""
    from app.schemas.ai import ModelVersionResponse

    mv = ModelVersionResponse(
        id="mv-1",
        model_type="yolo",
        version="v1.0",
        status="production",
        f1_score=0.92,
        map50=0.85,
    )
    output = mv.model_dump(by_alias=True)
    assert "modelType" in output, f"Expected camelCase 'modelType', got keys: {list(output.keys())}"
    assert "f1Score" in output
    assert "map50" in output
