"""
Notification Service - FastAPI Application
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import notification as notification_router
from app.middleware.gateway_auth import GatewayAuthMiddleware

# ─── Logging config — đảm bảo app.services loggers xuất hiện trong uvicorn stdout ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("app").setLevel(logging.INFO)

app = FastAPI(
    title="ParkSmart Notification Service",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gateway auth middleware
app.add_middleware(GatewayAuthMiddleware)

# Include routers
app.include_router(notification_router.router)


@app.get("/health/")
@app.get("/notifications/health/")
async def health_check():
    return {"status": "healthy", "service": "notification-service", "version": "1.0.0"}


@app.on_event("startup")
async def startup():
    # Tables already exist from Django — do NOT create them
    # Use alembic stamp head for existing tables
    pass
