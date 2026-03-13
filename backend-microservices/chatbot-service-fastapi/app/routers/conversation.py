"""
Conversation & ChatMessage endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.chatbot import Conversation, ChatMessage
from app.schemas.chatbot import (
    ConversationResponse,
    ChatMessageResponse,
    ActiveConversationResponse,
)

router = APIRouter(prefix="/chatbot/conversations", tags=["conversations"])


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all conversations for current user."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(20)
        .all()
    )
    return conversations


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new conversation."""
    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        current_state="idle",
        context={},
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/active/", response_model=ActiveConversationResponse)
async def active_conversation(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get or create active conversation for user."""
    conversation = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
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
        db.commit()
        db.refresh(conversation)

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
        .all()
    )
    messages.reverse()

    return ActiveConversationResponse(
        conversation=ConversationResponse.model_validate(conversation),
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


@router.get("/{conversation_id}/", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific conversation."""
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/messages/", response_model=dict)
async def chat_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get chat history for a conversation."""
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return {
        "messages": [ChatMessageResponse.model_validate(m).model_dump(mode="json", by_alias=True) for m in messages],
        "conversationId": str(conversation.id),
    }


@router.get("/history/latest/", response_model=dict)
async def latest_history(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get chat history for the most recent conversation."""
    conversation = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .first()
    )

    if not conversation:
        return {"messages": [], "conversationId": None}

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return {
        "messages": [ChatMessageResponse.model_validate(m).model_dump(mode="json", by_alias=True) for m in messages],
        "conversationId": str(conversation.id),
    }
