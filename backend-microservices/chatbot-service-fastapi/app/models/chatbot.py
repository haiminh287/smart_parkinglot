"""
Chatbot SQLAlchemy models — table names match existing Django tables.
"""

import uuid
from datetime import datetime, time

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    Time, JSON,
)
from sqlalchemy.dialects.mysql import CHAR

from app.database import Base


# ─── CORE CHAT MODELS ────────────────────────────

class Conversation(Base):
    __tablename__ = "chatbot_conversation"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), nullable=False, index=True)
    current_state = Column(String(50), default="idle")
    context = Column(JSON, default=dict)

    total_turns = Column(Integer, default=0)
    clarification_count = Column(Integer, default=0)
    handoff_requested = Column(Boolean, default=False)
    satisfaction_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chatbot_chatmessage"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(CHAR(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system, proactive
    content = Column(Text, nullable=False)

    intent = Column(String(100), default="")
    sub_intents = Column(JSON, default=list)
    entities = Column(JSON, default=dict)
    confidence = Column(Float, nullable=True)

    decision_data = Column(JSON, default=dict)
    action_taken = Column(String(100), default="")
    action_result = Column(JSON, default=dict)

    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── MEMORY ARCHITECTURE MODELS ──────────────────

class UserPreferences(Base):
    __tablename__ = "chatbot_user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), unique=True, nullable=False, index=True)

    favorite_lot_id = Column(CHAR(36), nullable=True)
    favorite_zone_id = Column(CHAR(36), nullable=True)
    favorite_slot_code = Column(String(20), default="")
    default_vehicle_id = Column(CHAR(36), nullable=True)

    last_booked_slot = Column(JSON, default=dict)
    booking_history_summary = Column(JSON, default=list)
    total_bookings = Column(Integer, default=0)

    profile_summary = Column(Text, default="")
    summary_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserBehavior(Base):
    __tablename__ = "chatbot_user_behavior"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), unique=True, nullable=False, index=True)

    typical_arrival_time = Column(Time, nullable=True)
    typical_departure_time = Column(Time, nullable=True)
    typical_duration_minutes = Column(Integer, nullable=True)

    weekday_frequency = Column(JSON, default=dict)

    prefers_near_exit = Column(Boolean, default=False)
    prefers_shade = Column(Boolean, default=False)
    prefers_same_zone = Column(Boolean, default=True)
    prefers_same_slot = Column(Boolean, default=False)

    cancel_rate = Column(Float, default=0.0)
    no_show_rate = Column(Float, default=0.0)
    late_arrival_rate = Column(Float, default=0.0)
    overstay_rate = Column(Float, default=0.0)

    data_points = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.5)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserCommunicationStyle(Base):
    __tablename__ = "chatbot_user_communication_style"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(CHAR(36), unique=True, nullable=False, index=True)

    prefers_short = Column(Boolean, default=True)
    prefers_confirmation = Column(Boolean, default=False)
    emoji_level = Column(Integer, default=1)  # 0=none, 1=some, 2=many, 3=max
    formality = Column(String(20), default="casual")  # casual, neutral, formal

    primary_language = Column(String(10), default="vi")
    frustration_score = Column(Float, default=0.0)
    last_frustration_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationSummary(Base):
    __tablename__ = "chatbot_conversation_summary"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(CHAR(36), nullable=False, index=True)
    user_id = Column(CHAR(36), nullable=False, index=True)

    summary = Column(Text, nullable=False)
    key_decisions = Column(JSON, default=list)
    unresolved_issues = Column(JSON, default=list)
    entities_mentioned = Column(JSON, default=dict)
    sentiment = Column(String(20), default="neutral")

    created_at = Column(DateTime, default=datetime.utcnow)


# ─── PROACTIVE INTELLIGENCE MODELS ───────────────

class ProactiveNotification(Base):
    __tablename__ = "chatbot_proactive_notification"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), nullable=False, index=True)

    event_type = Column(String(30), nullable=False)
    status = Column(String(20), default="pending")  # pending, sent, read, dismissed, acted_on

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    event_data = Column(JSON, default=dict)
    suggested_actions = Column(JSON, default=list)

    user_action = Column(String(50), default="")
    user_action_at = Column(DateTime, nullable=True)

    trigger_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActionLog(Base):
    __tablename__ = "chatbot_action_log"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), nullable=False, index=True)
    conversation_id = Column(CHAR(36), nullable=True)
    message_id = Column(CHAR(36), nullable=True)

    action_type = Column(String(30), nullable=False)
    action_data = Column(JSON, default=dict)
    result_data = Column(JSON, default=dict)

    is_undoable = Column(Boolean, default=True)
    is_undone = Column(Boolean, default=False)
    undone_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ─── AI OBSERVABILITY MODEL (🔥 2.6) ─────────────

class AIMetricLog(Base):
    """
    🔥 CẢI TIẾN 2.6: AI-specific metric logging for observability.

    Tracks: intent_mismatch, clarification_rate, action_fail,
    user_override, confidence_calibration, memory_skip, proactive_suppression.
    """
    __tablename__ = "chatbot_ai_metric_log"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_type = Column(String(50), nullable=False, index=True)
    user_id = Column(CHAR(36), nullable=False, index=True)
    conversation_id = Column(CHAR(36), nullable=True, index=True)
    intent = Column(String(100), default="")
    confidence = Column(Float, nullable=True)
    extra_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
