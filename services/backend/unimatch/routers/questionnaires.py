"""Questionnaire routes: list, detail, respond, view own response."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import Questionnaire, QuestionnaireResponse, User
from unimatch.schemas import (
    ApiResponse,
    QuestionnaireOut,
    QuestionnaireResponseIn,
    QuestionnaireResponseOut,
)
from unimatch.security import get_current_user

router = APIRouter(prefix="/questionnaires", tags=["questionnaires"])


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
