"""Bridge: consume booking events from RabbitMQ and forward to
realtime-service WebSocket broadcast."""
import json
import logging
import os

import pika
import requests
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Bridge booking events to realtime-service WebSocket broadcast"

    def handle(self, *args, **options):
        rabbitmq_url = os.environ.get(
            'RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/'
        )
        realtime_url = os.environ.get(
            'REALTIME_SERVICE_URL', 'http://realtime-service-go:8006'
        )
        gateway_secret = os.environ.get('GATEWAY_SECRET', '')

        connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url)
        )
        channel = connection.channel()

        channel.exchange_declare(
            'parksmart.events', exchange_type='topic', durable=True
        )
        result = channel.queue_declare('realtime.broadcast', durable=True)
        channel.queue_bind(
            result.method.queue,
            'parksmart.events',
            routing_key='slot.status_changed',
        )
        channel.queue_bind(
            result.method.queue,
            'parksmart.events',
            routing_key='booking.*',
        )

        self.stdout.write(
            self.style.SUCCESS("Bridging events to realtime-service...")
        )

        headers = {
            'Content-Type': 'application/json',
            'X-Gateway-Secret': gateway_secret,
        }

        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                routing_key = method.routing_key

                if routing_key == 'slot.status_changed':
                    requests.post(
                        f"{realtime_url}/api/broadcast/slot-status/",
                        json={
                            'slot_id': payload.get('slot_id'),
                            'status': payload.get('status'),
                            'booking_id': payload.get('booking_id'),
                        },
                        headers=headers,
                        timeout=3,
                    )
                elif routing_key.startswith('booking.'):
                    user_id = payload.get('user_id')
                    if user_id:
                        requests.post(
                            f"{realtime_url}/api/broadcast/booking/",
                            json={
                                'userId': user_id,
                                'bookingId': payload.get('booking_id'),
                                'status': payload.get(
                                    'check_in_status'
                                ),
                                'eventType': routing_key,
                            },
                            headers=headers,
                            timeout=3,
                        )

                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as exc:
                logger.warning("Broadcast bridge error: %s", exc)
                # ack anyway — broadcast is best-effort
                ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_qos(prefetch_count=10)
        channel.basic_consume(
            queue='realtime.broadcast',
            on_message_callback=callback,
            auto_ack=False,
        )
        channel.start_consuming()
