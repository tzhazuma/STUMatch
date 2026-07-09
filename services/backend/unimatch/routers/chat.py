"""REST chat routes: conversations, messages, send via REST."""
import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import Conversation, Message, User
from unimatch.schemas import (
    ApiResponse,
    ConversationOut,
    ConversationParticipant,
    LastMessage,
    MessageIn,
    MessageOut,
)
from unimatch.security import get_current_user
from unimatch.services.chat_manager import get_or_create_conversation
from unimatch.services.moderation import ModerationService
from unimatch.services.storage import StorageService

router = APIRouter(prefix="", tags=["chat"])


async def _get_conversation(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> Conversation:
    conv = await db.get(Conversation, conversation_id)
    if not conv or user_id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


async def _participant(db: AsyncSession, conv: Conversation, current_id: UUID) -> User:
    other_id = conv.user_b_id if current_id == conv.user_a_id else conv.user_a_id
    user = await db.get(User, other_id)
    if not user:
        raise HTTPException(status_code=404, detail="participant not found")
    return user


@router.get("/conversations", response_model=ApiResponse)
async def list_conversations(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    stmt = (
        select(Conversation)
        .where(
            (Conversation.user_a_id == current_user.id) | (Conversation.user_b_id == current_user.id)
        )
        .order_by(Conversation.updated_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = []
    for conv in result.scalars().all():
        other = await _participant(db, conv, current_user.id)
        last = None
        if conv.messages:
            m = conv.messages[-1]
            last = LastMessage(content=m.content, created_at=m.created_at)
        unread = len([m for m in conv.messages if m.sender_id != current_user.id and not m.is_read])
        items.append(
            ConversationOut(
                id=conv.id,
                participant=ConversationParticipant(
                    id=other.id, nickname=other.nickname, avatar_url=other.profile.avatar_url if other.profile else None
                ),
                last_message=last,
                unread_count=unread,
            ).model_dump()
        )
    return {"data": {"items": items, "total": len(items), "page": page, "limit": limit}}


@router.get("/conversations/{conversation_id}/messages", response_model=ApiResponse)
async def get_messages(
    conversation_id: UUID,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    conv = await _get_conversation(db, conversation_id, current_user.id)
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    total = await db.scalar(select(Message).where(Message.conversation_id == conversation_id).count())
    return {
        "data": {
            "items": [MessageOut.model_validate(m).model_dump() for m in reversed(messages)],
            "total": total,
            "page": page,
            "limit": limit,
        }
    }


@router.post("/conversations/{conversation_id}/messages", response_model=ApiResponse)
async def send_message_rest(
    conversation_id: UUID,
    payload: MessageIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    conv = await _get_conversation(db, conversation_id, current_user.id)
    moderation = ModerationService()
    check = await asyncio.to_thread(moderation.check_text, payload.content, "chat")
    if check["triggered"]:
        raise HTTPException(status_code=400, detail="包含违禁词")
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=payload.content,
        message_type=payload.message_type,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return {"data": MessageOut.model_validate(message).model_dump()}


@router.post("/messages/{message_id}/read", response_model=ApiResponse)
async def mark_read(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    message = await db.get(Message, message_id)
    if not message or message.sender_id == current_user.id:
        raise HTTPException(status_code=404, detail="message not found")
    message.is_read = True
    await db.commit()
    await db.refresh(message)
    return {"data": MessageOut.model_validate(message).model_dump()}
