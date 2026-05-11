"""
AI Service - FastAPI Application
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.engine.camera_monitor import start_camera_monitor, stop_camera_monitor
from app.engine.esp32_device_store import seed_default_devices
from app.middleware.gateway_auth import GatewayAuthMiddleware
from app.routers import camera, detection, esp32, metrics, parking, training
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — start/stop background workers."""
    logger.info("AI Service starting up...")
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    seed_default_devices()

    # Pre-warm tất cả model nặng ngay khi startup để request đầu tiên
    # (check-in/check-out/scan-plate) không bị timeout 30s do lazy load.
    from app.engine.slot_detection import get_slot_detector
    get_slot_detector()
    logger.info("✓ YOLO slot detector warmed")

    try:
        from app.engine.plate_pipeline import get_plate_pipeline
        get_plate_pipeline(model_path=settings.PLATE_MODEL_PATH)
        logger.info("✓ Plate OCR pipeline warmed")
    except Exception as e:
        logger.warning("Plate pipeline warm failed: %s", e)

    try:
        from app.routers.detection import _get_pipeline
        _get_pipeline()
        logger.info("✓ Banknote pipeline warmed")
    except Exception as e:
        logger.warning("Banknote warm failed: %s", e)

    await start_camera_monitor()
    yield
    logger.info("AI Service shutting down...")
    await stop_camera_monitor()


app = FastAPI(
    title="ParkSmart AI Service",
    version="2.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GatewayAuthMiddleware)

app.include_router(detection.router)
app.include_router(training.router)
app.include_router(metrics.router)
app.include_router(metrics.parking_router)
app.include_router(parking.router)
app.include_router(esp32.router)
app.include_router(camera.router)

# Serve saved plate capture images (check-in / check-out detection records)
_plate_images_dir = Path(__file__).parent / "images"
_plate_images_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/ai/images", StaticFiles(directory=str(_plate_images_dir)), name="plate_images"
)


@app.get("/health/")
@app.get("/ai/health/")
async def health_check():
    return {"status": "healthy", "service": "ai-service", "version": "1.0.0"}
