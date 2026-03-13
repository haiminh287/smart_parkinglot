"""
AI Service - FastAPI Application
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.engine.camera_monitor import start_camera_monitor, stop_camera_monitor
from app.routers import detection, training, metrics, parking, esp32, camera
from app.routers.esp32 import seed_default_devices
from app.middleware.gateway_auth import GatewayAuthMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — start/stop background workers."""
    logger.info("AI Service starting up...")
    seed_default_devices()
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
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GatewayAuthMiddleware)

app.include_router(detection.router)
app.include_router(training.router)
app.include_router(metrics.router)
app.include_router(parking.router)
app.include_router(esp32.router)
app.include_router(camera.router)


@app.get("/health/")
@app.get("/ai/health/")
async def health_check():
    return {"status": "healthy", "service": "ai-service", "version": "1.0.0"}
