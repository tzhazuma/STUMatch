"""Message board routes for each section."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import MessageBoard, User
from unimatch.schemas import ApiResponse, MessageBoardIn, MessageBoardOut
from unimatch.security import get_current_user
from unimatch.services.moderation import ModerationService

router = APIRouter(prefix="/message-board", tags=["message-board"])


@router.get("/{section}", response_model=ApiResponse)
async def list_messages(
    section: str,
    owner_id: UUID | None = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    stmt = select(MessageBoard).where(MessageBoard.section == section)
    if owner_id:
        stmt = stmt.where(MessageBoard.owner_id == owner_id)
    stmt = stmt.order_by(MessageBoard.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    items = []
    for m in result.scalars().all():
        author = await db.get(User, m.author_id)
        items.append(
            MessageBoardOut(
                id=m.id,
                section=m.section,
                owner_id=m.owner_id,
                author_id=m.author_id,
                author_nickname=author.nickname if author else "未知",
                content=m.content,
                created_at=m.created_at,
            ).model_dump()
        )
    return {"data": {"items": items, "total": len(items), "page": page, "limit": limit}}


@router.post("/{section}", response_model=ApiResponse)
async def post_message(
    section: str,
    payload: MessageBoardIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    moderation = ModerationService()
    check = moderation.check_text(payload.content, source="board")
    if check["triggered"]:
        raise HTTPException(status_code=400, detail="包含违禁词")
    msg = MessageBoard(
        section=section,
        owner_id=payload.owner_id,
        author_id=current_user.id,
        content=payload.content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return {"data": MessageBoardOut.model_validate(msg).model_dump()}
