"""
Smoke tests for ai-service-fastapi.
Verifies health endpoint and __tablename__ mapping.
"""

import os
import sys
import types

import pytest
from app.main import app
from app.models.ai import CameraFeed, ModelVersion, PredictionLog
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
    assert data["service"] == "ai-service"


# ─── Data Integrity: __tablename__ Mapping ────────


@pytest.mark.parametrize(
    "model_cls,expected_name",
    [
        (CameraFeed, "api_camerafeed"),
        (PredictionLog, "api_predictionlog"),
        (ModelVersion, "api_modelversion"),
    ],
)
def test_ai_tablename(model_cls, expected_name):
    """AI models must map to correct Django table names."""
    assert (
        model_cls.__tablename__ == expected_name
    ), f"{model_cls.__name__}: expected '{expected_name}', got '{model_cls.__tablename__}'"


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
    assert (
        "plateText" in output
    ), f"Expected camelCase 'plateText', got keys: {list(output.keys())}"


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
    assert (
        "modelType" in output
    ), f"Expected camelCase 'modelType', got keys: {list(output.keys())}"
    assert "f1Score" in output
    assert "map50" in output


class _FakeModel:
    def __init__(self, ckpt_path: str | None = None):
        self.ckpt_path = ckpt_path


def test_slot_detector_load_yolo_uses_configured_path_when_exists(
    monkeypatch, tmp_path
):
    """_load_yolo should prefer configured model path when the file exists."""
    from app.engine import slot_detection

    configured_model = tmp_path / "models" / "yolo11n.pt"
    configured_model.parent.mkdir(parents=True, exist_ok=True)
    configured_model.write_bytes(b"weights")

    calls: list[str] = []

    def fake_yolo(path: str):
        calls.append(path)
        return _FakeModel(ckpt_path=path)

    monkeypatch.setattr(
        slot_detection.settings,
        "YOLO_PARKING_MODEL_PATH",
        str(configured_model),
    )
    monkeypatch.setitem(
        sys.modules, "ultralytics", types.SimpleNamespace(YOLO=fake_yolo)
    )

    detector = slot_detection.SlotDetector.__new__(slot_detection.SlotDetector)
    model = detector._load_yolo()

    assert model is not None
    assert calls == [str(configured_model)]


def test_slot_detector_load_yolo_autodownload_and_sync_when_config_missing(
    monkeypatch, tmp_path
):
    """_load_yolo should auto-download and sync weights when configured path is missing."""
    from app.engine import slot_detection

    configured_model = tmp_path / "persisted" / "yolo11n.pt"
    downloaded_model = tmp_path / "ultralytics-cache" / "yolo11n.pt"
    downloaded_model.parent.mkdir(parents=True, exist_ok=True)
    downloaded_model.write_bytes(b"auto-downloaded-weights")

    calls: list[str] = []

    def fake_yolo(path: str):
        calls.append(path)
        if path == "yolo11n.pt":
            return _FakeModel(ckpt_path=str(downloaded_model))
        return _FakeModel(ckpt_path=path)

    monkeypatch.setattr(
        slot_detection.settings,
        "YOLO_PARKING_MODEL_PATH",
        str(configured_model),
    )
    monkeypatch.setitem(
        sys.modules, "ultralytics", types.SimpleNamespace(YOLO=fake_yolo)
    )

    detector = slot_detection.SlotDetector.__new__(slot_detection.SlotDetector)
    model = detector._load_yolo()

    assert model is not None
    assert calls == ["yolo11n.pt"]
    assert configured_model.exists()
    assert configured_model.read_bytes() == b"auto-downloaded-weights"


def test_slot_detector_load_yolo_falls_back_to_none_when_all_paths_fail(
    monkeypatch, tmp_path
):
    """_load_yolo should return None if YOLO loading and auto-download fail."""
    from app.engine import slot_detection

    configured_model = tmp_path / "missing" / "yolo11n.pt"

    def fake_yolo(_path: str):
        raise RuntimeError("load failed")

    monkeypatch.setattr(
        slot_detection.settings,
        "YOLO_PARKING_MODEL_PATH",
        str(configured_model),
    )
    monkeypatch.setitem(
        sys.modules, "ultralytics", types.SimpleNamespace(YOLO=fake_yolo)
    )

    detector = slot_detection.SlotDetector.__new__(slot_detection.SlotDetector)
    model = detector._load_yolo()

    assert model is None
