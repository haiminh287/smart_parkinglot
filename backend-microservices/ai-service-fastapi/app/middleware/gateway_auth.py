from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    """Verify requests come through the API gateway."""

    EXEMPT_PATHS = [
        "/health/",
        "/health",
        "/ai/health/",
        "/ai/health",
        "/docs",
        "/openapi.json",
        "/ai/cameras/",
        # Saved plate crops served via <img> tags — cannot send gateway header
        "/ai/images/",
        # AI annotated overview served via <img> on admin dashboard
        "/ai/parking/detect-overview-annotated/",
        # ESP32 device endpoints — ESP32 connects directly (no gateway)
        "/ai/parking/esp32/register",
        "/ai/parking/esp32/heartbeat",
        "/ai/parking/esp32/log",
        # Existing ESP32 gate endpoints (also direct)
        "/ai/parking/esp32/check-in",
        "/ai/parking/esp32/check-out",
        "/ai/parking/esp32/verify-slot",
        "/ai/parking/esp32/cash-payment",
        "/ai/parking/esp32/status",
    ]

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)

        gateway_secret = request.headers.get("X-Gateway-Secret", "").strip()
        if gateway_secret != settings.GATEWAY_SECRET.strip():
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied: requests must come through the API gateway"},
            )

        request.state.user_id = request.headers.get("X-User-ID")
        request.state.user_email = request.headers.get("X-User-Email")
        request.state.user_role = request.headers.get("X-User-Role")
        request.state.is_staff = request.headers.get("X-User-Is-Staff", "false").lower() == "true"

        return await call_next(request)
