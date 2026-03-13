"""
User Preferences endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.chatbot import UserPreferences
from app.schemas.chatbot import UserPreferencesResponse, UserPreferencesUpdate

router = APIRouter(prefix="/chatbot/preferences", tags=["preferences"])


@router.get("/", response_model=UserPreferencesResponse)
async def get_preferences(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get user chatbot preferences."""
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.put("/", response_model=UserPreferencesResponse)
async def update_preferences(
    payload: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update user chatbot preferences."""
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)
        db.flush()

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prefs, key, value)

    db.commit()
    db.refresh(prefs)
    return prefs
