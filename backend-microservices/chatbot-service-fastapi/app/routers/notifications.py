"""
Proactive Notification endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.chatbot import ProactiveNotification
from app.schemas.chatbot import ProactiveNotificationResponse, NotificationActionRequest

router = APIRouter(prefix="/chatbot/notifications", tags=["chatbot-notifications"])


@router.get("/", response_model=dict)
async def list_notifications(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get pending proactive notifications for the user."""
    notifications = (
        db.query(ProactiveNotification)
        .filter(
            ProactiveNotification.user_id == user_id,
            ProactiveNotification.status.in_(["pending", "sent"]),
        )
        .order_by(ProactiveNotification.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "notifications": [
            ProactiveNotificationResponse.model_validate(n).model_dump(mode="json", by_alias=True) for n in notifications
        ],
        "count": len(notifications),
    }


@router.post("/{notification_id}/", response_model=dict)
async def update_notification(
    notification_id: str,
    payload: NotificationActionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Mark proactive notification as read / dismissed / acted upon."""
    notification = (
        db.query(ProactiveNotification)
        .filter(ProactiveNotification.id == notification_id, ProactiveNotification.user_id == user_id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if payload.action == "dismiss":
        notification.status = "dismissed"
    elif payload.action == "acted":
        notification.status = "acted_on"  # BUG FIX: was 'acted' in Django, corrected to 'acted_on'
        notification.user_action = payload.user_action or ""
        notification.user_action_at = datetime.utcnow()
    else:
        notification.status = "read"

    db.commit()
    return {"status": notification.status}
