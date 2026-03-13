"""
Main chat endpoint — processes user messages through orchestrator v3.

🔥 Integrates all 6 improvements:
- 2.1: 3-step intent (classify → extract → build)
- 2.2: Hybrid confidence in response
- 2.3: Safety codes in error responses
- 2.4: Anti-noise memory updates
- 2.6: AI observability metrics per request
"""

import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.chatbot import Conversation, ChatMessage
from app.schemas.chatbot import (
    ChatRequest, ChatResponse, QuickAction, FeedbackRequest,
)

router = APIRouter(prefix="/chatbot", tags=["chat"])


@router.post("/chat/", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Process user message through orchestrator v3 pipeline."""
    start_time = time.time()

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    # Get or create conversation
    conversation = None
    if payload.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id, Conversation.user_id == user_id)
            .first()
        )

    if not conversation:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            current_state="idle",
            context={},
        )
        db.add(conversation)
        db.flush()

    # Save user message
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="user",
        content=payload.message.strip(),
    )
    db.add(user_msg)
    db.flush()

    # Build conversation context with state for hybrid confidence
    conv_context = {
        **(conversation.context or {}),
        "conversationId": str(conversation.id),
        "totalTurns": conversation.total_turns or 0,
        "clarificationCount": conversation.clarification_count or 0,
        "state": conversation.current_state,
    }

    # Process through orchestrator v3 (async, with DB + all improvements)
    from app.engine.orchestrator import ChatbotOrchestrator
    from app.main import get_llm_client, get_service_client

    orchestrator = ChatbotOrchestrator(
        user_id=user_id,
        db=db,
        llm_client=get_llm_client(),
        service_client=get_service_client(),
    )
    result = await orchestrator.process_message(
        message=payload.message.strip(),
        conversation_context=conv_context,
    )

    elapsed_ms = int((time.time() - start_time) * 1000)

    # Save assistant response with full decision data
    assistant_msg = ChatMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content=result.get("response", ""),
        intent=result.get("intent", ""),
        entities=result.get("entities", {}),
        confidence=result.get("confidence"),
        decision_data={
            "suggestions": result.get("suggestions", []),
            "showMap": result.get("showMap", False),
            "showQrCode": result.get("showQrCode", False),
            # 🔥 2.2: Confidence breakdown
            "confidenceBreakdown": result.get("confidenceBreakdown", {}),
            # 🔥 2.3: Safety info
            "safetyCode": result.get("safetyCode"),
            "safetyHint": result.get("safetyHint"),
        },
        action_result=result.get("data", {}),
        processing_time_ms=elapsed_ms,
    )
    db.add(assistant_msg)

    # Update conversation context
    is_clarification = result.get("clarificationNeeded", False)
    new_context: dict[str, Any] = {
        **(conversation.context or {}),
        "lastIntent": result.get("intent"),
        "lastEntities": result.get("entities", {}),
        "lastData": result.get("data", {}),
        "lastConfidence": result.get("confidence", 0.0),
        "lastGateAction": (
            "clarify" if is_clarification
            else "confirm" if result.get("confirmationNeeded", False)
            else "execute"
        ),
        "conversationId": str(conversation.id),
    }

    # 🔥 3.0: Store/clear booking wizard state
    if "booking_wizard" in result:
        wizard_data = result.get("booking_wizard")
        if wizard_data is None:
            # Wizard completed/cancelled — remove from context
            new_context.pop("booking_wizard", None)
        else:
            new_context["booking_wizard"] = wizard_data
    conversation.context = new_context
    conversation.current_state = result.get("intent", "idle")
    conversation.total_turns = (conversation.total_turns or 0) + 1

    if is_clarification:
        conversation.clarification_count = (conversation.clarification_count or 0) + 1
    else:
        # Reset clarification counter on successful non-clarification response
        conversation.clarification_count = 0

    conversation.updated_at = datetime.utcnow()

    db.commit()

    return ChatResponse(
        response=result.get("response", ""),
        intent=result.get("intent"),
        entities=result.get("entities", {}),
        suggestions=result.get("suggestions", []),
        data=result.get("data", {}),
        conversationId=str(conversation.id),
        messageId=str(assistant_msg.id),
        confidence=result.get("confidence"),
        processingTimeMs=elapsed_ms,
        showMap=result.get("showMap", False),
        showQrCode=result.get("showQrCode", False),
        clarificationNeeded=result.get("clarificationNeeded", False),
        confirmationNeeded=result.get("confirmationNeeded", False),
        # 🔥 2.2: Hybrid confidence breakdown
        confidenceBreakdown=result.get("confidenceBreakdown", {}),
        # 🔥 2.3: Safety code + hint
        safetyCode=result.get("safetyCode"),
        safetyHint=result.get("safetyHint"),
    )


@router.get("/quick-actions/", response_model=dict)
async def quick_actions(user_id: str = Depends(get_current_user_id)):
    """Get available quick actions for the chatbot UI."""
    actions = [
        QuickAction(id="check_car_slots", label="Xem chỗ trống ô tô", icon="car", prompt="Còn bao nhiêu chỗ trống cho ô tô?"),
        QuickAction(id="check_bike_slots", label="Xem chỗ trống xe máy", icon="bike", prompt="Còn bao nhiêu chỗ trống cho xe máy?"),
        QuickAction(id="book_car", label="Đặt chỗ ô tô", icon="calendar", prompt="Tôi muốn đặt chỗ cho ô tô"),
        QuickAction(id="book_bike", label="Đặt chỗ xe máy", icon="calendar", prompt="Tôi muốn đặt chỗ cho xe máy"),
        QuickAction(id="my_bookings", label="Xem booking của tôi", icon="list", prompt="Cho tôi xem các booking của tôi"),
        QuickAction(id="rebook", label="Đặt lại như lần trước", icon="repeat", prompt="Đặt lại như lần trước"),
        QuickAction(id="current_parking", label="Xe đang đậu ở đâu?", icon="mapPin", prompt="Xe tôi đang đậu ở đâu?"),
        QuickAction(id="pricing", label="Xem bảng giá", icon="dollarSign", prompt="Giá đậu xe bao nhiêu?"),
        QuickAction(id="help", label="Trợ giúp", icon="helpCircle", prompt="Hướng dẫn sử dụng"),
    ]
    return {"quickActions": [a.model_dump(by_alias=True) for a in actions]}


@router.post("/feedback/")
async def submit_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Submit feedback / satisfaction rating for a conversation."""
    if not payload.conversation_id or not payload.rating:
        raise HTTPException(status_code=400, detail="conversationId and rating are required")

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == payload.conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.satisfaction_score = float(payload.rating)
    db.flush()

    if payload.comment:
        feedback_msg = ChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=f"[Feedback: {payload.rating}/5] {payload.comment}",
            intent="feedback",
        )
        db.add(feedback_msg)

    db.commit()
    return {"message": "Cảm ơn bạn đã phản hồi!", "rating": payload.rating}
