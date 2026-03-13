"""
Notification API routes
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

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

router = APIRouter(prefix="/notifications", tags=["notifications"])


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
    db: Session = Depends(get_db),
):
    """Create a new notification (internal use)"""
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
