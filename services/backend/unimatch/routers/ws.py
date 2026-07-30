"""WebSocket chat endpoint."""
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.schemas import MessageIn
from unimatch.security import decode_token
from unimatch.services.chat_manager import ConnectionManager, send_message
from unimatch.services.moderation import ModerationService, load_moderation_configs

logger = logging.getLogger(__name__)

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

    # Ensure user_id is a UUID object so equality checks in send_message work.
    if isinstance(user_id, str):
        try:
            user_id = UUID(user_id)
        except (ValueError, TypeError):
            await websocket.close(code=4001)
            return

    await manager.connect(str(user_id), websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            if event_type == "send_message":
                # Accept both {type, payload:{...}} (frontend WSEvent shape) and
                # a flat {type, conversation_id, content, ...} shape.
                inner = data.get("payload") if isinstance(data.get("payload"), dict) else {}
                # Convert conversation_id to UUID for send_message.
                conv_id_raw = inner.get("conversation_id") or data.get("conversation_id")
                if not conv_id_raw:
                    await manager.send_to(str(user_id), {"type": "error", "message": "missing conversation_id"})
                    continue
                try:
                    conversation_id = UUID(conv_id_raw) if isinstance(conv_id_raw, str) else conv_id_raw
                except (ValueError, TypeError):
                    await manager.send_to(str(user_id), {"type": "error", "message": "invalid conversation_id"})
                    continue
                content = inner.get("content", "") or data.get("content", "")
                message_type = inner.get("message_type", "text") or data.get("message_type", "text")

                configs = await load_moderation_configs(db)
                moderation = ModerationService(extra_words=configs)
                check = await moderation.async_moderate(content, source="chat", db=db)
                if check["triggered"]:
                    await manager.send_to(
                        str(user_id),
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
                    logger.warning("WS send_message ValueError: %s", exc)
                    await manager.send_to(
                        str(user_id),
                        {"type": "error", "message": str(exc)},
                    )
                except Exception as exc:
                    logger.exception("WS send_message unexpected error")
                    await manager.send_to(
                        str(user_id),
                        {"type": "error", "message": f"发送失败: {type(exc).__name__}"},
                    )
            elif event_type == "message_read":
                # Handled via REST; ack here
                await manager.send_to(str(user_id), {"type": "ack", "event": "message_read"})
            elif event_type == "typing":
                # Broadcast typing to other participant only
                pass
    except WebSocketDisconnect:
        manager.disconnect(str(user_id))
    except Exception:
        logger.exception("WS unexpected error for user %s", user_id)
        manager.disconnect(str(user_id))
