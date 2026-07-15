import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.models import Conversation, Message
from unimatch.schemas import MessageIn
from unimatch.services.moderation import ModerationService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage active WebSocket connections and route chat events."""

    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active[user_id] = websocket

    def disconnect(self, user_id: str) -> None:
        self.active.pop(user_id, None)

    async def send_to(self, user_id: str, message: dict[str, Any]) -> None:
        ws = self.active.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, user_ids: list[str], message: dict[str, Any]) -> None:
        for uid in user_ids:
            await self.send_to(uid, message)


async def get_or_create_conversation(db: AsyncSession, user_a: UUID, user_b: UUID) -> Conversation:
    a, b = sorted([user_a, user_b], key=lambda x: str(x))
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_a_id == a, Conversation.user_b_id == b
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        conversation = Conversation(user_a_id=a, user_b_id=b)
        db.add(conversation)
        await db.flush()
    return conversation


async def send_message(
    db: AsyncSession,
    manager: ConnectionManager,
    sender_id: UUID,
    conversation_id: UUID,
    payload: MessageIn,
    moderation: ModerationService | None = None,
) -> Message:
    if moderation is None:
        moderation = ModerationService()

    check = moderation.check_text(payload.content, source="chat")
    if check["triggered"]:
        raise ValueError("包含违禁词")

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise ValueError("Conversation not found")
    if sender_id not in (conversation.user_a_id, conversation.user_b_id):
        raise ValueError("Not a participant")

    message = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=payload.content,
        message_type=payload.message_type,
    )
    db.add(message)
    await db.flush()

    other_id = (
        conversation.user_b_id
        if sender_id == conversation.user_a_id
        else conversation.user_a_id
    )

    await manager.broadcast(
        [str(conversation.user_a_id), str(conversation.user_b_id)],
        {
            "type": "new_message",
            "conversation_id": str(conversation_id),
            "message": {
                "id": str(message.id),
                "conversation_id": str(conversation_id),
                "sender_id": str(sender_id),
                "content": message.content,
                "message_type": message.message_type,
                "is_read": message.is_read,
                "created_at": message.created_at.isoformat(),
            },
        },
    )
    await manager.send_to(
        str(other_id),
        {
            "type": "unread_update",
            "conversation_id": str(conversation_id),
        },
    )
    return message
