"""Discovery routes: sections, search, push toggle, user detail.""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import Profile, User
from unimatch.schemas import (
    ApiResponse,
    DiscoveryListResponse,
    DiscoveryProfileOut,
    DiscoveryUser,
    PushToggle,
)
from unimatch.security import get_current_user
from unimatch.services.matching import MatchingService

router = APIRouter(prefix="/discovery", tags=["discovery"])

SECTION_FIELDS = {
    "academic": ["research_direction"],
    "daily": ["bio"],
    "dating": ["dating_purpose", "family_status", "ideal_person"],
}


@router.get("/{section}", response_model=ApiResponse)
async def list_users(
    section: str,
    q: str | None = None,
    push: bool = False,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if section not in ("academic", "daily", "dating"):
        raise HTTPException(status_code=400, detail="invalid section")
    service = MatchingService(db)
    data = await service.discover(current_user.id, section, q, push, page, limit)
    return {"data": DiscoveryListResponse(**data).model_dump()}


@router.get("/{section}/users/{user_id}", response_model=ApiResponse)
async def user_detail(
    section: str,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if section not in ("academic", "daily", "dating"):
        raise HTTPException(status_code=400, detail="invalid section")
    result = await db.execute(
        select(Profile, User).join(User, User.id == Profile.user_id).where(Profile.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    profile, user = row
    data = DiscoveryProfileOut(
        user_id=profile.user_id,
        nickname=user.nickname,
        avatar_url=profile.avatar_url,
        age=profile.age,
        education_level=profile.education_level.value if profile.education_level else None,
        school=user.school,
        major=profile.major,
        mbti=profile.mbti,
        interests=profile.interests or [],
        location=profile.location,
        bio=profile.bio,
        research_direction=profile.research_direction,
        dating_purpose=profile.dating_purpose,
        family_status=profile.family_status,
        ideal_person=profile.ideal_person,
    ).model_dump()
    # Hide non-section fields
    for field in ["research_direction", "dating_purpose", "family_status", "ideal_person"]:
        if field not in SECTION_FIELDS.get(section, []):
            data[field] = None
    return {"data": data}


@router.post("/{section}/push", response_model=ApiResponse)
async def toggle_push(
    section: str,
    payload: PushToggle,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if section not in ("academic", "daily", "dating"):
        raise HTTPException(status_code=400, detail="invalid section")
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    if section == "academic":
        profile.push_academic = payload.enabled
    elif section == "daily":
        profile.push_daily = payload.enabled
    else:
        profile.push_dating = payload.enabled
    await db.commit()
    return {"data": {"section": section, "enabled": payload.enabled}}
