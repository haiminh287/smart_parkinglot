"""
Notification API routes
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.notification import Notification, NotificationPreference
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    MarkReadRequest,
)
from app.services.email_sender import send_notification_email
from app.services.realtime_push import push_to_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _lookup_user_email(user_id: str) -> Optional[str]:
    """Lookup user email từ auth-service nội bộ.

    Trả về None nếu không lookup được — caller dùng ADMIN_EMAIL fallback.
    """
    import httpx
    try:
        url = f"{settings.AUTH_SERVICE_URL.rstrip('/')}/auth/users/{user_id}/"
        headers = {"X-Gateway-Secret": settings.GATEWAY_SECRET}
        with httpx.Client(timeout=3) as client:
            r = client.get(url, headers=headers)
        if r.status_code == 200:
            return (r.json() or {}).get("email")
    except Exception as e:
        logger.warning("Lookup user email failed for %s: %s", user_id, e)
    return None


def _dispatch_side_effects(notification: Notification, pref: NotificationPreference):
    """Email + Realtime push — gọi từ BackgroundTasks sau khi DB commit."""
    n_type = notification.notification_type
    payload = {
        "id": str(notification.id),
        "user_id": str(notification.user_id),
        "notification_type": n_type,
        "title": notification.title,
        "message": notification.message,
        "data": notification.data or {},
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }

    # 1. Realtime push qua WebSocket
    push_to_user(str(notification.user_id), payload)

    # 2. Email — chỉ gửi nếu user enable email + enable theo type
    if not pref or not pref.email_enabled:
        return
    type_enabled = True
    if n_type == "booking" and not pref.booking_notifications:
        type_enabled = False
    elif n_type == "payment" and not pref.payment_notifications:
        type_enabled = False
    elif n_type == "incident" and not pref.incident_notifications:
        type_enabled = False
    elif n_type == "marketing" and not pref.marketing_notifications:
        type_enabled = False
    if not type_enabled:
        return

    # Lookup recipient email
    to_email = (notification.data or {}).get("email")
    if not to_email:
        to_email = _lookup_user_email(str(notification.user_id))
    if not to_email:
        to_email = settings.ADMIN_EMAIL  # fallback
        logger.info("No user email found · fallback to ADMIN_EMAIL=%s", to_email)

    sent_ok = send_notification_email(
        to_email=to_email,
        notification_type=n_type,
        title=notification.title,
        message=notification.message,
        data=notification.data or {},
    )
    # Update email_sent flag (best-effort, separate session not used here for simplicity)
    if sent_ok:
        try:
            from app.database import SessionLocal
            with SessionLocal() as s:
                s.query(Notification).filter(Notification.id == notification.id).update(
                    {"email_sent": True}
                )
                s.commit()
        except Exception:
            logger.exception("Failed to update email_sent flag for %s", notification.id)


@router.get("/", response_model=dict)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    notification_type: Optional[str] = None,
    is_read: Optional[bool] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List notifications for the current user with pagination"""
    query = db.query(Notification).filter(Notification.user_id == user_id)

    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    total = query.count()
    notifications = (
        query.order_by(desc(Notification.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "count": total,
        "next": f"/notifications/?page={page + 1}&page_size={page_size}" if page * page_size < total else None,
        "previous": f"/notifications/?page={page - 1}&page_size={page_size}" if page > 1 else None,
        "results": [NotificationResponse.model_validate(n) for n in notifications],
    }


@router.get("/unread-count/")
async def unread_count(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get count of unread notifications"""
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).count()
    return {"unread_count": count}


@router.post("/", response_model=NotificationResponse, status_code=201)
async def create_notification(
    data: NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create notification + (background) send email + realtime push.

    Email + WS push chạy trong BackgroundTasks → endpoint response nhanh,
    không bị chặn bởi SMTP/HTTP I/O. Failure không ảnh hưởng response.
    """
    notification = Notification(
        user_id=data.user_id,
        notification_type=data.notification_type,
        title=data.title,
        message=data.message,
        data=data.data,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Lookup user preferences (auto-create default nếu chưa có)
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == data.user_id
    ).first()
    if not pref:
        pref = NotificationPreference(user_id=data.user_id)
        db.add(pref)
        db.commit()
        db.refresh(pref)

    # Side effects async — không block response
    background_tasks.add_task(_dispatch_side_effects, notification, pref)

    return notification


@router.post("/mark-read/")
async def mark_read(
    data: MarkReadRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Mark notifications as read"""
    now = datetime.utcnow()
    updated = (
        db.query(Notification)
        .filter(
            Notification.id.in_(data.notification_ids),
            Notification.user_id == user_id,
        )
        .update({"is_read": True, "read_at": now}, synchronize_session="fetch")
    )
    db.commit()
    return {"marked_read": updated}


@router.post("/mark-all-read/")
async def mark_all_read(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read"""
    now = datetime.utcnow()
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .update({"is_read": True, "read_at": now}, synchronize_session="fetch")
    )
    db.commit()
    return {"marked_read": updated}


@router.get("/preferences/", response_model=NotificationPreferenceResponse)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get notification preferences"""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id
    ).first()
    if not pref:
        # Create default preferences
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.put("/preferences/", response_model=NotificationPreferenceResponse)
async def update_preferences(
    data: NotificationPreferenceUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update notification preferences"""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id
    ).first()
    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pref, key, value)

    db.commit()
    db.refresh(pref)
    return pref
