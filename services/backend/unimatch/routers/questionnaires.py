"""Questionnaire routes: list, detail, respond, view own response."""
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import (
    EducationLevel,
    Gender,
    Profile,
    Questionnaire,
    QuestionnaireResponse,
    User,
)
from unimatch.schemas import (
    ApiResponse,
    QuestionnaireOut,
    QuestionnaireResponseIn,
    QuestionnaireResponseOut,
)
from unimatch.security import get_current_user

router = APIRouter(prefix="/questionnaires", tags=["questionnaires"])


def _validate_answers(answers: dict[str, Any], questions: list[dict]) -> None:
    """Validate submitted answers against a questionnaire's question schema.

    Raises HTTPException(422) with a descriptive detail on the first failure.
    """
    for question in questions:
        qid = question.get("id")
        if not qid:
            continue
        qtype = question.get("type")
        required = question.get("required", False)
        value = answers.get(qid)

        if required and value in (None, "", []):
            raise HTTPException(
                status_code=422, detail=f"question {qid} is required"
            )

        if value is None:
            continue

        if qtype in {"single_choice", "multiple_choice"}:
            options = {opt.get("value") for opt in question.get("options", []) if opt.get("value") is not None}
            if qtype == "single_choice":
                if value not in options:
                    raise HTTPException(
                        status_code=422,
                        detail=f"invalid option for {qid}",
                    )
            else:
                if not isinstance(value, list):
                    raise HTTPException(
                        status_code=422,
                        detail=f"question {qid} must be a list",
                    )
                invalid = [v for v in value if v not in options]
                if invalid:
                    raise HTTPException(
                        status_code=422,
                        detail=f"invalid options for {qid}: {invalid}",
                    )

        elif qtype == "rating":
            try:
                rating_value = int(value)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=422,
                    detail=f"question {qid} must be a number",
                )
            min_val = question.get("min")
            max_val = question.get("max")
            if min_val is not None and rating_value < min_val:
                raise HTTPException(
                    status_code=422,
                    detail=f"question {qid} below minimum {min_val}",
                )
            if max_val is not None and rating_value > max_val:
                raise HTTPException(
                    status_code=422,
                    detail=f"question {qid} above maximum {max_val}",
                )

        elif qtype == "date":
            if isinstance(value, str):
                try:
                    date.fromisoformat(value)
                except ValueError:
                    raise HTTPException(
                        status_code=422,
                        detail=f"question {qid} must be a valid ISO date (YYYY-MM-DD)",
                    )
            elif not isinstance(value, date):
                raise HTTPException(
                    status_code=422,
                    detail=f"question {qid} must be a valid date",
                )


def _calculate_age(birth_date: date) -> int:
    today = date.today()
    return (
        today.year - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def _sync_profile_from_answers(profile: Profile, answers: dict[str, Any]) -> None:
    """Map known questionnaire answer keys to the user's Profile fields."""
    if "gender" in answers:
        profile.gender = Gender(answers["gender"])

    if "birth_date" in answers:
        birth_value = answers["birth_date"]
        if isinstance(birth_value, str):
            birth_date = date.fromisoformat(birth_value)
        elif isinstance(birth_value, date):
            birth_date = birth_value
        else:
            birth_date = None
        if birth_date:
            profile.birth_date = birth_date
            profile.age = _calculate_age(birth_date)

    if "education_level" in answers:
        profile.education_level = EducationLevel(answers["education_level"])

    if "major" in answers:
        profile.major = answers["major"]

    if "interests" in answers:
        interests_value = answers["interests"]
        if isinstance(interests_value, str):
            profile.interests = [
                i.strip() for i in interests_value.split(",") if i.strip()
            ]
        elif isinstance(interests_value, list):
            profile.interests = [str(i) for i in interests_value]

    if "mbti" in answers:
        profile.mbti = answers["mbti"]

    if "location" in answers:
        profile.location = answers["location"]

    if "bio" in answers:
        profile.bio = answers["bio"]

    if "research_direction" in answers:
        profile.research_direction = answers["research_direction"]

    if "dating_purpose" in answers:
        profile.dating_purpose = answers["dating_purpose"]

    if "ideal_person" in answers:
        ideal_value = answers["ideal_person"]
        if isinstance(ideal_value, list):
            profile.ideal_person = ", ".join(str(i) for i in ideal_value)
        else:
            profile.ideal_person = str(ideal_value)


async def _get_or_create_profile(db: AsyncSession, user: User) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user.id, nickname=user.nickname)
        db.add(profile)
        await db.flush()
    return profile


@router.get("", response_model=ApiResponse)
async def list_questionnaires(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(select(Questionnaire).where(Questionnaire.is_active == True))
    items = result.scalars().all()
    return {"data": [QuestionnaireOut.model_validate(q).model_dump() for q in items]}


@router.get("/{slug}", response_model=ApiResponse)
async def get_questionnaire(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(select(Questionnaire).where(Questionnaire.slug == slug))
    questionnaire = result.scalar_one_or_none()
    if not questionnaire:
        raise HTTPException(status_code=404, detail="questionnaire not found")
    return {"data": QuestionnaireOut.model_validate(questionnaire).model_dump()}


@router.post("/{slug}/responses", response_model=ApiResponse)
async def submit_response(
    slug: str,
    payload: QuestionnaireResponseIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(select(Questionnaire).where(Questionnaire.slug == slug))
    questionnaire = result.scalar_one_or_none()
    if not questionnaire:
        raise HTTPException(status_code=404, detail="questionnaire not found")

    _validate_answers(payload.answers, questionnaire.questions)

    profile = await _get_or_create_profile(db, current_user)
    _sync_profile_from_answers(profile, payload.answers)

    existing = await db.execute(
        select(QuestionnaireResponse).where(
            QuestionnaireResponse.questionnaire_id == questionnaire.id,
            QuestionnaireResponse.user_id == current_user.id,
        )
    )
    response = existing.scalar_one_or_none()
    if response:
        response.answers = payload.answers
    else:
        response = QuestionnaireResponse(
            questionnaire_id=questionnaire.id,
            user_id=current_user.id,
            answers=payload.answers,
        )
        db.add(response)
    await db.commit()
    await db.refresh(response)
    return {"data": QuestionnaireResponseOut.model_validate(response).model_dump()}


@router.get("/{slug}/responses/me", response_model=ApiResponse)
async def get_my_response(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(Questionnaire, QuestionnaireResponse)
        .join(
            QuestionnaireResponse,
            QuestionnaireResponse.questionnaire_id == Questionnaire.id,
            isouter=True,
        )
        .where(Questionnaire.slug == slug, QuestionnaireResponse.user_id == current_user.id)
    )
    row = result.first()
    if not row or not row[1]:
        return {"data": None}
    return {"data": QuestionnaireResponseOut.model_validate(row[1]).model_dump()}
