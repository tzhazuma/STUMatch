"""Admin routes."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.database import get_db
from unimatch.models import ModerationLog, Report, User
from unimatch.schemas import (
    AdminReportResolveIn,
    AdminUserStatusIn,
    ApiResponse,
    ReportOut,
    UserOut,
)
from unimatch.security import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=ApiResponse)
async def list_users(
    q: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    stmt = select(User)
    if q:
        stmt = stmt.where(
            (User.nickname.ilike(f"%{q}%"))
            | (User.email.ilike(f"%{q}%"))
        )
    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    total = await db.scalar(select(User).count())
    return {"data": {"items": [UserOut.model_validate(u).model_dump() for u in items], "total": total, "page": page, "limit": limit}}


@router.put("/users/{user_id}/status", response_model=ApiResponse)
async def update_user_status(
    user_id: UUID,
    payload: AdminUserStatusIn,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    user.status = payload.status  # type: ignore[assignment]
    await db.commit()
    await db.refresh(user)
    return {"data": UserOut.model_validate(user).model_dump()}


@router.get("/reports", response_model=ApiResponse)
async def list_reports(
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    stmt = select(Report)
    if status:
        stmt = stmt.where(Report.status == status)
    stmt = stmt.order_by(Report.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    total = await db.scalar(select(Report).count())
    return {"data": {"items": [ReportOut.model_validate(r).model_dump() for r in items], "total": total, "page": page, "limit": limit}}


@router.put("/reports/{report_id}", response_model=ApiResponse)
async def resolve_report(
    report_id: UUID,
    payload: AdminReportResolveIn,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    report = await db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    report.status = payload.status  # type: ignore[assignment]
    report.resolution = payload.resolution
    await db.commit()
    await db.refresh(report)
    return {"data": ReportOut.model_validate(report).model_dump()}


@router.get("/moderation-logs", response_model=ApiResponse)
async def list_moderation_logs(
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    stmt = select(ModerationLog).order_by(ModerationLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return {"data": {"items": [m.model_dump() for m in items], "total": len(items), "page": page, "limit": limit}}
