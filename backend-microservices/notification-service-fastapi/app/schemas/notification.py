"""
Pydantic schemas for notification-service
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel
from app.schemas.base import CamelModel


class NotificationCreate(CamelModel):
    user_id: str
    notification_type: str  # booking, payment, incident, system, marketing
    title: str
    message: str
    data: dict = {}


class NotificationResponse(CamelModel):
    id: str
    user_id: str
    notification_type: str
    title: str
    message: str
    data: dict
    is_read: bool
    read_at: Optional[datetime] = None
    push_sent: bool
    email_sent: bool
    sms_sent: bool
    created_at: datetime


class NotificationPreferenceResponse(CamelModel):
    id: str
    user_id: str
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    booking_notifications: bool
    payment_notifications: bool
    incident_notifications: bool
    marketing_notifications: bool


class NotificationPreferenceUpdate(CamelModel):
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    booking_notifications: Optional[bool] = None
    payment_notifications: Optional[bool] = None
    incident_notifications: Optional[bool] = None
    marketing_notifications: Optional[bool] = None


class MarkReadRequest(CamelModel):
    notification_ids: list[str]


class PaginatedResponse(CamelModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: list[Any]
