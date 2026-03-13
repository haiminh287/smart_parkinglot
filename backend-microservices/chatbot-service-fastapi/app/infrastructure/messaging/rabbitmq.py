"""
RabbitMQ Consumer — listens for proactive notification events.

Events consumed (🔥 2.5):
  - booking.expiring_soon → proactive reminder
  - booking.no_checkin    → nudge to check in
  - parking.maintenance   → alert affected users
  - booking.conflict      → warn about overlap
  - weather.alert         → suggest covered spots

Architecture:
  Other services → RabbitMQ → chatbot consumer → ProactiveService → Notification
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable

from app.config import settings

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """
    Async consumer for proactive events from RabbitMQ.

    Usage:
        consumer = RabbitMQConsumer(handler=proactive_svc.handle_event)
        await consumer.start()     # blocks / runs in background
        await consumer.stop()
    """

    EXCHANGE = "parksmart.events"
    QUEUE = "chatbot.proactive"
    ROUTING_KEYS = [
        "booking.expiring_soon",
        "booking.no_checkin",
        "parking.maintenance",
        "booking.conflict",
        "weather.alert",
    ]

    def __init__(
        self,
        handler: Callable[[dict], Awaitable[None]],
        amqp_url: Optional[str] = None,
    ):
        self.handler = handler
        self.amqp_url = amqp_url or settings.RABBITMQ_URL
        self._connection = None
        self._channel = None
        self._running = False

    async def start(self):
        """Connect and start consuming. Runs until stop() is called."""
        try:
            import aio_pika
        except ImportError:
            logger.warning("aio-pika not installed — RabbitMQ consumer disabled")
            return

        try:
            self._connection = await aio_pika.connect_robust(self.amqp_url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)

            # Declare exchange & queue
            exchange = await self._channel.declare_exchange(
                self.EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True,
            )
            queue = await self._channel.declare_queue(
                self.QUEUE, durable=True,
            )

            # Bind routing keys
            for key in self.ROUTING_KEYS:
                await queue.bind(exchange, routing_key=key)

            self._running = True
            logger.info(
                f"RabbitMQ consumer started, listening on {self.QUEUE} "
                f"({len(self.ROUTING_KEYS)} routing keys)"
            )

            # Consume
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    if not self._running:
                        break
                    async with message.process():
                        await self._handle_message(message)

        except Exception as e:
            logger.error(f"RabbitMQ consumer error: {e}", exc_info=True)

    async def stop(self):
        """Gracefully stop the consumer."""
        self._running = False
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("RabbitMQ consumer stopped")

    async def _handle_message(self, message):
        """Parse and dispatch a single message to the handler."""
        try:
            body = json.loads(message.body.decode())
            event = {
                "event_type": message.routing_key,
                "user_id": body.get("userId") or body.get("user_id", ""),
                "data": body,
            }
            logger.debug(f"Received event: {event['event_type']} for user {event['user_id']}")
            await self.handler(event)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in RabbitMQ message: {message.body!r}")
        except Exception as e:
            logger.error(f"Error handling RabbitMQ message: {e}", exc_info=True)
