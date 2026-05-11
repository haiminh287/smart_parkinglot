"""
Celery configuration for booking-service.
"""

from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "booking_service.settings")

app = Celery("booking_service")

# Load configuration from Django settings with CELERY namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    "auto-cancel-unpaid-bookings-every-minute": {
        "task": "bookings.tasks.auto_cancel_unpaid_bookings",
        "schedule": 60.0,  # Every 60 seconds
    },
    "check-no-show-bookings-every-5-minutes": {
        "task": "bookings.tasks.check_no_show_bookings",
        "schedule": 300.0,  # Every 5 minutes
    },
    "publish-outbox-events": {
        "task": "bookings.tasks.publish_outbox_events",
        "schedule": 2.0,
    },
    "process-dead-letter-events": {
        "task": "bookings.tasks.process_dead_letter_events",
        "schedule": 300.0,
    },
}

app.conf.timezone = "Asia/Ho_Chi_Minh"


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


def debug_task(self):
    print(f"Request: {self.request!r}")
