"""Current user and user management routes."""
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import User
from unimatch.schemas import ApiResponse, UserMeUpdate, UserOut
from unimatch.security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=ApiResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"data": UserOut.model_validate(current_user).model_dump()}


@router.put("/me", response_model=ApiResponse)
async def update_me(
    payload: UserMeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if payload.email is not None:
        existing = await db.execute(select(User).where(User.email == payload.email, User.id != current_user.id))
        if existing.scalar_one_or_none():
            return {"error": "email_conflict", "message": "email already in use"}
        current_user.email = payload.email
    if payload.phone is not None:
        existing = await db.execute(select(User).where(User.phone == payload.phone, User.id != current_user.id))
        if existing.scalar_one_or_none():
            return {"error": "phone_conflict", "message": "phone already in use"}
        current_user.phone = payload.phone
    await db.commit()
    await db.refresh(current_user)
    return {"data": UserOut.model_validate(current_user).model_dump()}


@router.delete("/me", response_model=ApiResponse)
async def delete_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    current_user.status = "pending_deletion"  # type: ignore[assignment]
    await db.commit()
    return {"data": {"ok": True}}
