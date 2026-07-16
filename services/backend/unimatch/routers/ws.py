"""WebSocket chat endpoint."""
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.schemas import MessageIn
from unimatch.security import decode_token
from unimatch.services.chat_manager import ConnectionManager, send_message
from unimatch.services.moderation import ModerationService, load_moderation_configs

router = APIRouter(tags=["websocket"])
manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
        user_id = payload["sub"]
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            if event_type == "send_message":
                conversation_id = data.get("conversation_id")
                content = data.get("content", "")
                message_type = data.get("message_type", "text")

                configs = await load_moderation_configs(db)
                moderation = ModerationService(extra_words=configs)
                check = await moderation.async_moderate(content, source="chat", db=db)
                if check["triggered"]:
                    await manager.send_to(
                        user_id,
                        {"type": "error", "message": "包含违禁词"},
                    )
                    continue

                try:
                    msg = await send_message(
                        db,
                        manager,
                        user_id,
                        conversation_id,
                        MessageIn(content=content, message_type=message_type),
                        moderation,
                    )
                    await db.commit()
                except ValueError as exc:
                    await manager.send_to(
                        user_id,
                        {"type": "error", "message": str(exc)},
                    )
            elif event_type == "message_read":
                # Handled via REST; ack here
                await manager.send_to(user_id, {"type": "ack", "event": "message_read"})
            elif event_type == "typing":
                # Broadcast typing to other participant only
                pass
    except WebSocketDisconnect:
        manager.disconnect(user_id)
