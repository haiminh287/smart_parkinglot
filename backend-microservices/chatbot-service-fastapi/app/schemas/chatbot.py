"""
Pydantic schemas for chatbot service.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel
from app.schemas.base import CamelModel


# ─── Chat ─────────────────────────────────────────

class ChatRequest(CamelModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(CamelModel):
    response: str
    intent: Optional[str] = None
    entities: dict = {}
    suggestions: list[str] = []
    data: dict = {}
    conversation_id: str
    message_id: str
    confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    show_map: bool = False
    show_qr_code: bool = False
    clarification_needed: bool = False
    confirmation_needed: bool = False

    # 🔥 2.2: Hybrid confidence breakdown (llm, entityCompleteness, contextMatch)
    confidence_breakdown: Optional[dict] = {}

    # 🔥 2.3: Safety result code & user-facing hint
    safety_code: Optional[str] = None
    safety_hint: Optional[str] = None


# ─── Conversation ─────────────────────────────────

class ConversationResponse(CamelModel):
    id: str
    user_id: str
    current_state: str
    total_turns: int
    clarification_count: int
    handoff_requested: bool
    satisfaction_score: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChatMessageResponse(CamelModel):
    id: str
    conversation_id: str
    role: str
    content: str
    intent: Optional[str] = ""
    entities: dict = {}
    confidence: Optional[float] = None
    decision_data: dict = {}
    action_taken: Optional[str] = ""
    action_result: dict = {}
    processing_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None


class ActiveConversationResponse(CamelModel):
    conversation: ConversationResponse
    messages: list[ChatMessageResponse]


# ─── Preferences ──────────────────────────────────

class UserPreferencesResponse(CamelModel):
    user_id: str
    favorite_lot_id: Optional[str] = None
    favorite_zone_id: Optional[str] = None
    favorite_slot_code: str = ""
    default_vehicle_id: Optional[str] = None
    last_booked_slot: dict = {}
    booking_history_summary: list = []
    total_bookings: int = 0
    profile_summary: str = ""
    summary_updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserPreferencesUpdate(CamelModel):
    favorite_lot_id: Optional[str] = None
    favorite_zone_id: Optional[str] = None
    favorite_slot_code: Optional[str] = None
    default_vehicle_id: Optional[str] = None


# ─── Proactive Notifications ─────────────────────

class ProactiveNotificationResponse(CamelModel):
    id: str
    user_id: str
    event_type: str
    status: str
    title: str
    message: str
    event_data: dict = {}
    suggested_actions: list = []
    user_action: str = ""
    user_action_at: Optional[datetime] = None
    trigger_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class NotificationActionRequest(CamelModel):
    action: str = "read"  # read, dismiss, acted
    user_action: Optional[str] = ""


# ─── Feedback ─────────────────────────────────────

class FeedbackRequest(CamelModel):
    conversation_id: str
    rating: int  # 1-5
    comment: Optional[str] = ""


# ─── Action Log ───────────────────────────────────

class ActionLogResponse(CamelModel):
    id: str
    user_id: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    action_type: str
    action_data: dict = {}
    result_data: dict = {}
    is_undoable: bool = True
    is_undone: bool = False
    undone_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ─── Quick Actions ────────────────────────────

class QuickAction(CamelModel):
    id: str
    label: str
    icon: str
    prompt: str
