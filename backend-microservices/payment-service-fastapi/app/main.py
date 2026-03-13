"""
Payment Service - FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import payment as payment_router
from app.middleware.gateway_auth import GatewayAuthMiddleware

app = FastAPI(
    title="ParkSmart Payment Service",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GatewayAuthMiddleware)
app.include_router(payment_router.router)


@app.get("/health/")
@app.get("/payments/health/")
async def health_check():
    return {"status": "healthy", "service": "payment-service", "version": "1.0.0"}
