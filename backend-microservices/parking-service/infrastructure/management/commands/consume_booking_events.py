"""RabbitMQ consumer for booking events — updates slot status."""
import json
import logging
import os

import pika
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError

from infrastructure.models import ProcessedEvent, CarSlot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume booking events from RabbitMQ and update slot status"

    def handle(self, *args, **options):
        rabbitmq_url = os.environ.get(
            'RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/'
        )
        self.stdout.write("Connecting to RabbitMQ...")

        connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url)
        )
        channel = connection.channel()

        channel.exchange_declare(
            'parksmart.events', exchange_type='topic', durable=True
        )
        result = channel.queue_declare('parking.slot_sync', durable=True)
        channel.queue_bind(
            result.method.queue,
            'parksmart.events',
            routing_key='slot.status_changed',
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Listening for slot.status_changed events..."
            )
        )

        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                event_id = payload.get('event_id')
                if not event_id:
                    logger.warning("Event missing event_id, dropping")
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag, requeue=False
                    )
                    return

                with transaction.atomic():
                    try:
                        ProcessedEvent.objects.create(
                            event_id=event_id,
                            event_type=method.routing_key,
                        )
                    except IntegrityError:
                        logger.info(
                            "Duplicate event %s, skipping", event_id
                        )
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return

                    slot_id = payload.get('slot_id')
                    status = payload.get('status')
                    if slot_id and status:
                        updated = CarSlot.objects.filter(
                            id=slot_id
                        ).update(status=status)
                        if updated:
                            logger.info("Slot %s → %s", slot_id, status)
                        else:
                            logger.warning("Slot %s not found", slot_id)

                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                logger.exception("Consumer error processing event")
                ch.basic_nack(
                    delivery_tag=method.delivery_tag, requeue=True
                )

        channel.basic_qos(prefetch_count=10)
        channel.basic_consume(
            queue='parking.slot_sync',
            on_message_callback=callback,
            auto_ack=False,
        )
        channel.start_consuming()
