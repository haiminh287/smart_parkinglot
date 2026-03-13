"""
Action History endpoints (for undo support).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.chatbot import ActionLog
from app.schemas.chatbot import ActionLogResponse

router = APIRouter(prefix="/chatbot/actions", tags=["actions"])


@router.get("/", response_model=dict)
async def list_actions(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get recent actions for the user (supports undo UI)."""
    actions = (
        db.query(ActionLog)
        .filter(ActionLog.user_id == user_id)
        .order_by(ActionLog.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "actions": [ActionLogResponse.model_validate(a).model_dump(mode="json", by_alias=True) for a in actions],
    }
