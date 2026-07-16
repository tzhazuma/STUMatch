"""Profile routes: CRUD, avatar upload, consent."""
from typing import Any
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import Profile, User, UserConsent
from unimatch.schemas import (
    ApiResponse,
    AvatarOut,
    ConsentRequest,
    ProfileOut,
    ProfileUpdate,
)
from unimatch.security import get_current_user
from unimatch.services.moderation import ModerationService, load_moderation_configs
from unimatch.services.storage import StorageService

router = APIRouter(prefix="/profiles", tags=["profiles"])

PROFILE_MODERATED_FIELDS = [
    "nickname",
    "bio",
    "ideal_person",
    "dating_purpose",
    "research_direction",
]


def _has_high_severity(service: ModerationService, words: list[str]) -> bool:
    """Return True if any matched word is high severity."""
    for word in words:
        meta = service._meta.get(word)
        if meta and meta.get("severity") == "high":
            return True
    return False


async def _get_or_create_profile(db: AsyncSession, user: User) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id, nickname=user.nickname)
        db.add(profile)
        await db.flush()
    return profile


@router.get("/me", response_model=ApiResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    profile = await _get_or_create_profile(db, current_user)
    data = ProfileOut.model_validate(profile).model_dump()
    data["school"] = current_user.school
    data["is_verified_email"] = current_user.is_verified_email
    data["is_verified_school"] = current_user.is_verified_school
    return {"data": data}


@router.put("/me", response_model=ApiResponse)
async def update_profile(
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    profile = await _get_or_create_profile(db, current_user)
    update_data = payload.model_dump(exclude_unset=True)

    configs = await load_moderation_configs(db)
    moderation = ModerationService(extra_words=configs)
    for field in PROFILE_MODERATED_FIELDS:
        value = update_data.get(field)
        if not value:
            continue
        result = await moderation.async_moderate(value, source="profile", db=db)
        if result["triggered"] and _has_high_severity(moderation, result["words"]):
            raise HTTPException(
                status_code=400,
                detail=f"包含违禁词: {', '.join(result['words'])}",
            )

    for field, value in update_data.items():
        setattr(profile, field, value)
    if profile.birth_date and not profile.age:
        today = date.today()
        profile.age = today.year - profile.birth_date.year - (
            (today.month, today.day) < (profile.birth_date.month, profile.birth_date.day)
        )
    if payload.nickname:
        current_user.nickname = payload.nickname
    await db.commit()
    await db.refresh(profile)
    data = ProfileOut.model_validate(profile).model_dump()
    data["school"] = current_user.school
    data["is_verified_email"] = current_user.is_verified_email
    data["is_verified_school"] = current_user.is_verified_school
    return {"data": data}


@router.post("/avatar", response_model=ApiResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    profile = await _get_or_create_profile(db, current_user)
    storage = StorageService()
    result = await storage.upload_file(file, folder="avatars")
    profile.avatar_url = result["url"]
    await db.commit()
    await db.refresh(profile)
    return {"data": AvatarOut(avatar_url=result["url"]).model_dump()}


@router.post("/consent", response_model=ApiResponse)
async def update_consent(
    payload: ConsentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(UserConsent).where(
            UserConsent.user_id == current_user.id,
            UserConsent.consent_type == payload.consent_type,
        )
    )
    consent = result.scalar_one_or_none()
    if not consent:
        consent = UserConsent(
            user_id=current_user.id,
            consent_type=payload.consent_type,
            granted=payload.granted,
        )
        db.add(consent)
    else:
        consent.granted = payload.granted
    await db.commit()
    return {"data": {"consent_type": payload.consent_type, "granted": payload.granted}}
