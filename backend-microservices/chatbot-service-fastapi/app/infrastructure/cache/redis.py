"""
Redis Cache — async caching for conversation context, rate limiting, proactive cooldowns.

Used by:
  - ProactiveService: cooldown tracking (🔥 2.5)
  - ConversationRouter: cache conversation context
  - IntentService: cache recent intent classifications
"""

import json
import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_redis = None


async def get_redis():
    """Lazy singleton for async redis connection."""
    global _redis
    if _redis is None:
        try:
            import redis.asyncio as aioredis
            _redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=20,
            )
            # Test connection
            await _redis.ping()
            logger.info("Redis connection established")
        except ImportError:
            logger.warning("redis package not installed — cache disabled")
            return None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} — cache disabled")
            _redis = None
            return None
    return _redis


async def close_redis():
    """Close redis connection on shutdown."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


class RedisCache:
    """
    High-level caching interface.

    Keys are auto-namespaced with 'chatbot:' prefix.
    """

    PREFIX = "chatbot:"

    def __init__(self, redis_client=None):
        self._redis = redis_client

    async def _get_client(self):
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Returns None if miss or error."""
        client = await self._get_client()
        if not client:
            return None
        try:
            raw = await client.get(f"{self.PREFIX}{key}")
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug(f"Cache GET error for {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl_seconds: int = 3600
    ) -> bool:
        """Set a value in cache with TTL. Returns True on success."""
        client = await self._get_client()
        if not client:
            return False
        try:
            await client.setex(
                f"{self.PREFIX}{key}",
                ttl_seconds,
                json.dumps(value, default=str),
            )
            return True
        except Exception as e:
            logger.debug(f"Cache SET error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        client = await self._get_client()
        if not client:
            return False
        try:
            await client.delete(f"{self.PREFIX}{key}")
            return True
        except Exception as e:
            logger.debug(f"Cache DELETE error for {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        client = await self._get_client()
        if not client:
            return False
        try:
            return bool(await client.exists(f"{self.PREFIX}{key}"))
        except Exception:
            return False

    # ─── Proactive cooldown helpers (🔥 2.5) ─────

    async def set_cooldown(
        self, user_id: str, event_type: str, ttl_seconds: int
    ) -> bool:
        """Set a cooldown for proactive notifications."""
        key = f"cooldown:{user_id}:{event_type}"
        return await self.set(key, {"active": True}, ttl_seconds=ttl_seconds)

    async def is_on_cooldown(self, user_id: str, event_type: str) -> bool:
        """Check if user has an active cooldown for event type."""
        key = f"cooldown:{user_id}:{event_type}"
        return await self.exists(key)

    async def increment_hourly(self, user_id: str) -> int:
        """Increment hourly notification counter. Returns new count."""
        client = await self._get_client()
        if not client:
            return 0
        key = f"{self.PREFIX}hourly:{user_id}"
        try:
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, 3600)  # 1 hour TTL
            return count
        except Exception:
            return 0

    async def get_hourly_count(self, user_id: str) -> int:
        """Get current hourly notification count."""
        client = await self._get_client()
        if not client:
            return 0
        try:
            val = await client.get(f"{self.PREFIX}hourly:{user_id}")
            return int(val) if val else 0
        except Exception:
            return 0

    # ─── Conversation context cache ──────────────

    async def cache_conversation_context(
        self, conversation_id: str, context: dict, ttl: int = 1800
    ) -> bool:
        """Cache conversation context (30min default TTL)."""
        key = f"conv:{conversation_id}"
        return await self.set(key, context, ttl_seconds=ttl)

    async def get_conversation_context(self, conversation_id: str) -> Optional[dict]:
        """Get cached conversation context."""
        key = f"conv:{conversation_id}"
        return await self.get(key)
