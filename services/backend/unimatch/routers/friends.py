"""Friend request and friendship routes."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import Friendship, User
from unimatch.schemas import ApiResponse, FriendOut, FriendRequestIn, FriendRequestOut
from unimatch.security import get_current_user

router = APIRouter(prefix="/friends", tags=["friends"])


@router.post("/requests", response_model=ApiResponse)
async def send_request(
    payload: FriendRequestIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if payload.to_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="cannot send friend request to yourself")
    target = await db.get(User, payload.to_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="target user not found")

    existing = await db.execute(
        select(Friendship).where(
            Friendship.requester_id == current_user.id,
            Friendship.addressee_id == payload.to_user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="friend request already sent")

    req = Friendship(
        requester_id=current_user.id,
        addressee_id=payload.to_user_id,
        message=payload.message,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return {"data": FriendRequestOut.model_validate(req).model_dump()}


@router.get("/requests", response_model=ApiResponse)
async def list_requests(
    direction: str = "received",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if direction == "received":
        stmt = select(Friendship).where(Friendship.addressee_id == current_user.id)
    else:
        stmt = select(Friendship).where(Friendship.requester_id == current_user.id)
    result = await db.execute(stmt.order_by(Friendship.created_at.desc()))
    items = result.scalars().all()
    return {
        "data": {
            "items": [FriendRequestOut.model_validate(r).model_dump() for r in items],
            "total": len(items),
        }
    }


@router.post("/requests/{request_id}/accept", response_model=ApiResponse)
async def accept_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    req = await db.get(Friendship, request_id)
    if not req or req.addressee_id != current_user.id:
        raise HTTPException(status_code=404, detail="request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="request already processed")
    req.status = "accepted"  # type: ignore[assignment]
    await db.commit()
    await db.refresh(req)
    return {"data": FriendRequestOut.model_validate(req).model_dump()}


@router.post("/requests/{request_id}/reject", response_model=ApiResponse)
async def reject_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    req = await db.get(Friendship, request_id)
    if not req or req.addressee_id != current_user.id:
        raise HTTPException(status_code=404, detail="request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="request already processed")
    req.status = "rejected"  # type: ignore[assignment]
    await db.commit()
    await db.refresh(req)
    return {"data": FriendRequestOut.model_validate(req).model_dump()}


@router.get("", response_model=ApiResponse)
async def list_friends(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    stmt = select(Friendship).where(
        ((Friendship.requester_id == current_user.id) | (Friendship.addressee_id == current_user.id))
        & (Friendship.status == "accepted")
    )
    result = await db.execute(stmt.order_by(Friendship.created_at.desc()))
    friends = []
    for f in result.scalars().all():
        friend_id = f.addressee_id if f.requester_id == current_user.id else f.requester_id
        friend = await db.get(User, friend_id)
        if not friend:
            continue
        friends.append(
            FriendOut(
                user_id=friend.id,
                nickname=friend.nickname,
                avatar_url=friend.profile.avatar_url if friend.profile else None,
                school=friend.school,
                major=friend.profile.major if friend.profile else None,
            ).model_dump()
        )
    return {"data": friends}


@router.delete("/{user_id}", response_model=ApiResponse)
async def delete_friend(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    stmt = select(Friendship).where(
        (
            (Friendship.requester_id == current_user.id) & (Friendship.addressee_id == user_id)
        )
        | (
            (Friendship.requester_id == user_id) & (Friendship.addressee_id == current_user.id)
        )
    )
    result = await db.execute(stmt)
    friendship = result.scalar_one_or_none()
    if friendship:
        await db.delete(friendship)
        await db.commit()
    return {"data": {"ok": True}}
