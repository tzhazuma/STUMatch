"""Match recommendation and feedback routes."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import MatchFeedback, User
from unimatch.schemas import ApiResponse, MatchFeedbackIn, MatchRecommendationOut
from unimatch.security import get_current_user
from unimatch.services.matching import MatchingService

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/recommendations/{section}", response_model=ApiResponse)
async def get_recommendations(
    section: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = MatchingService(db)
    recs = await service.recommend(current_user.id, section, limit)
    return {"data": [r.model_dump() for r in recs]}


@router.post("/{user_id}/feedback", response_model=ApiResponse)
async def submit_feedback(
    user_id: UUID,
    payload: MatchFeedbackIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    feedback = MatchFeedback(
        user_id=current_user.id,
        target_user_id=user_id,
        section=payload.section,
        action=payload.action,
    )
    db.add(feedback)
    await db.commit()
    return {"data": {"ok": True}}
