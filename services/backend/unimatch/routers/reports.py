"""Report routes."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import Report, User
from unimatch.schemas import ApiResponse, ReportIn, ReportOut
from unimatch.security import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ApiResponse)
async def create_report(
    payload: ReportIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    report = Report(
        reporter_id=current_user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        description=payload.description,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return {"data": ReportOut.model_validate(report).model_dump()}
