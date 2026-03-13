"""
Gateway authentication middleware for FastAPI.
Verifies X-Gateway-Secret header on all requests (except health checks).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    """Verify requests come through the API gateway."""

    EXEMPT_PATHS = ["/health/", "/notifications/health/", "/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)

        gateway_secret = request.headers.get("X-Gateway-Secret", "")
        if gateway_secret != settings.GATEWAY_SECRET:
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied: requests must come through the API gateway"},
            )

        request.state.user_id = request.headers.get("X-User-ID")
        request.state.user_email = request.headers.get("X-User-Email", "")
        request.state.user_role = request.headers.get("X-User-Role", "user")
        request.state.is_staff = request.headers.get("X-User-Is-Staff", "false").lower() == "true"

        return await call_next(request)
