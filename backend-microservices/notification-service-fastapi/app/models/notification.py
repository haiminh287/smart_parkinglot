"""
SQLAlchemy models for notification-service.
CRITICAL: __tablename__ MUST match Django table names to prevent data loss.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Index, Integer
from sqlalchemy.sql import func

from app.database import Base


class NotificationPreference(Base):
    """User notification preferences — matches Django table 'notifications_notificationpreference'"""
    __tablename__ = "notifications_notificationpreference"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), unique=True, index=True, nullable=False)

    # Notification channels
    push_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)

    # Notification types
    booking_notifications = Column(Boolean, default=True)
    payment_notifications = Column(Boolean, default=True)
    incident_notifications = Column(Boolean, default=True)
    marketing_notifications = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Notification(Base):
    """Notification model — matches Django table 'notifications_notification'"""
    __tablename__ = "notifications_notification"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True, nullable=False)

    notification_type = Column(String(20), nullable=False)  # booking, payment, incident, system, marketing
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, default=dict)

    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    # Delivery status
    push_sent = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    sms_sent = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_notification_user_created", "user_id", "created_at"),
        Index("ix_notification_is_read", "is_read"),
    )
