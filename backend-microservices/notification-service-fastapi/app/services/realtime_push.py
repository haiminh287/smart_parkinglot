"""Push notification realtime tới FE qua realtime-service-go WebSocket."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def push_to_user(user_id: str, payload: dict[str, Any]) -> bool:
    """Gọi realtime-service /api/broadcast/notification/ để push WebSocket.

    realtime-service sẽ broadcast vào group "user_<user_id>" → FE nhận event "notification".
    Trả về True nếu broadcast OK.
    """
    if not user_id:
        logger.warning("push_to_user: no user_id — skip")
        return False

    url = f"{settings.REALTIME_SERVICE_URL.rstrip('/')}/api/broadcast/notification/"
    body = {"user_id": user_id, "data": payload}
    headers = {"X-Gateway-Secret": settings.GATEWAY_SECRET}

    try:
        # Sync httpx call — BackgroundTasks already async, no need for async client
        with httpx.Client(timeout=5) as client:
            r = client.post(url, json=body, headers=headers)
        if r.status_code == 200:
            logger.info("Realtime push OK · user=%s · type=%s",
                        user_id, payload.get("notification_type"))
            return True
        logger.warning(
            "Realtime push failed · status=%s · body=%s",
            r.status_code, r.text[:200],
        )
        return False
    except httpx.RequestError as e:
        logger.warning("Realtime service unreachable (%s) — bỏ qua push", e)
        return False
    except Exception as e:
        logger.exception("Realtime push error: %s", e)
        return False
