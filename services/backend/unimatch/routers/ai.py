"""AI routes: generate questions, match explanation."""
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from unimatch.database import get_db
from unimatch.models import Profile, User
from unimatch.schemas import (
    ApiResponse,
    AIGenerateQuestionsIn,
    AIGenerateQuestionsOut,
    AIMatchExplanationIn,
    AIMatchExplanationOut,
)
from unimatch.security import get_current_user
from unimatch.services.ai_gateway import AIGateway, get_ai_gateway

router = APIRouter(prefix="/ai", tags=["ai"])


def _profile_text(profile: Profile | None, user: User) -> str:
    if not profile:
        return f"昵称：{user.nickname}"
    parts = [f"昵称：{user.nickname}"]
    if profile.age:
        parts.append(f"年龄：{profile.age}")
    if profile.school:
        parts.append(f"学校：{profile.school}")
    if profile.major:
        parts.append(f"专业：{profile.major}")
    if profile.interests:
        parts.append(f"兴趣：{','.join(profile.interests)}")
    if profile.location:
        parts.append(f"所在地：{profile.location}")
    if profile.bio:
        parts.append(f"简介：{profile.bio}")
    return "；".join(parts)


@router.post("/generate-questions", response_model=ApiResponse)
async def generate_questions(
    payload: AIGenerateQuestionsIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    gateway: AIGateway = Depends(get_ai_gateway),
) -> dict[str, Any]:
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    text = _profile_text(profile, current_user)
    questions = await gateway.generate_questions(payload.section, payload.count, text)
    return {"data": AIGenerateQuestionsOut(questions=questions).model_dump()}


@router.post("/match-explanation", response_model=ApiResponse)
async def match_explanation(
    payload: AIMatchExplanationIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    gateway: AIGateway = Depends(get_ai_gateway),
) -> dict[str, Any]:
    my_profile = await db.get(Profile, current_user.id)
    target_user = await db.get(User, payload.target_user_id)
    if not target_user:
        return {"data": {"explanation": "", "highlights": []}}
    target_profile = await db.execute(select(Profile).where(Profile.user_id == target_user.id))
    target_profile = target_profile.scalar_one_or_none()
    me_text = _profile_text(my_profile, current_user)
    target_text = _profile_text(target_profile, target_user)
    explanation = await gateway.match_explanation(me_text, target_text, payload.section)
    return {"data": AIMatchExplanationOut(**explanation).model_dump()}
