"""
Chatbot Service v3.0 — FastAPI Application

🔥 Improvements:
  2.1: IntentService 3-step (classify → extract → build)
  2.2: Hybrid Confidence (0.5*LLM + 0.3*entity + 0.2*context)
  2.3: SafetyResult with reason codes
  2.4: Memory anti-noise rules
  2.5: Proactive cooldown + priority
  2.6: AI Observability metrics
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, conversation, preferences, notifications, actions
from app.middleware.gateway_auth import GatewayAuthMiddleware

logger = logging.getLogger(__name__)

# ─── Singleton infrastructure instances ───────────
_service_client = None
_llm_client = None
_rabbitmq_consumer = None
_rabbitmq_task: Optional[asyncio.Task] = None


def get_service_client():
    global _service_client
    if _service_client is None:
        from app.infrastructure.external.service_client import ServiceClient
        _service_client = ServiceClient()
    return _service_client


def get_llm_client():
    global _llm_client
    if _llm_client is None and settings.GEMINI_API_KEY:
        from app.infrastructure.llm.gemini_client import GeminiClient
        _llm_client = GeminiClient()
    return _llm_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks."""
    # ── Startup ──
    logger.info("Chatbot Service v3.0 starting up…")

    # Init Redis cache (non-blocking, graceful if unavailable)
    try:
        from app.infrastructure.cache.redis import get_redis
        redis = await get_redis()
        if redis:
            logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")

    # Pre-warm infrastructure singletons
    get_service_client()
    get_llm_client()
    logger.info("✅ Infrastructure clients initialised")

    # 🔥 2.5: Start RabbitMQ consumer for proactive events (non-blocking)
    global _rabbitmq_consumer, _rabbitmq_task
    try:
        from app.infrastructure.messaging.rabbitmq import RabbitMQConsumer
        from app.database import SessionLocal

        async def _rabbitmq_event_handler(event: dict) -> None:
            """Bridge RabbitMQ events to ProactiveService."""
            from app.application.services.proactive_service import ProactiveService

            db = SessionLocal()
            try:
                svc = ProactiveService(db=db)
                await svc.handle_event(
                    event_type=event.get("event_type", ""),
                    user_id=event.get("user_id", ""),
                    event_data=event.get("data", {}),
                )
            except Exception as exc:
                logger.error(f"Proactive event handler error: {exc}", exc_info=True)
            finally:
                db.close()

        _rabbitmq_consumer = RabbitMQConsumer(handler=_rabbitmq_event_handler)
        _rabbitmq_task = asyncio.create_task(_rabbitmq_consumer.start())
        logger.info("✅ RabbitMQ consumer task started")
    except Exception as e:
        logger.warning(f"⚠️ RabbitMQ consumer not started: {e}")

    yield

    # ── Shutdown ──
    logger.info("Chatbot Service shutting down…")

    # 🔥 2.5: Stop RabbitMQ consumer
    if _rabbitmq_consumer:
        try:
            await _rabbitmq_consumer.stop()
        except Exception:
            pass
    if _rabbitmq_task and not _rabbitmq_task.done():
        _rabbitmq_task.cancel()

    global _service_client, _llm_client
    if _service_client:
        await _service_client.close()
        _service_client = None
    try:
        from app.infrastructure.cache.redis import close_redis
        await close_redis()
    except Exception:
        pass
    logger.info("✅ Cleanup complete")


app = FastAPI(
    title="ParkSmart Chatbot Service",
    version="3.0.0",
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

app.include_router(chat.router)
app.include_router(conversation.router)
app.include_router(preferences.router)
app.include_router(notifications.router)
app.include_router(actions.router)


@app.get("/health/")
@app.get("/chatbot/health/")
async def health_check():
    return {"status": "healthy", "service": "chatbot-service", "version": "3.0.0"}
