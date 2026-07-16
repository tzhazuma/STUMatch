"""Referral invite routes."""
import base64
import hashlib
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.config import get_settings
from unimatch.database import get_db
from unimatch.models import Referral, ReferralUse, User
from unimatch.schemas import ApiResponse, ReferralApplyIn, ReferralCodeOut, ReferralStatsOut
from unimatch.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/referrals", tags=["referrals"])
settings = get_settings()


def _generate_referral_code(user_id: uuid.UUID) -> str:
    """Generate a deterministic 8-character referral code for a user."""
    digest = hashlib.sha256(str(user_id).encode("utf-8")).digest()
    return base64.b32encode(digest).decode("ascii")[:8]


async def _get_or_create_referral(db: AsyncSession, user: User) -> Referral:
    """Return the user's existing referral row or create one with a deterministic code."""
    result = await db.execute(select(Referral).where(Referral.inviter_id == user.id))
    referral = result.scalar_one_or_none()
    if referral:
        return referral

    code = _generate_referral_code(user.id)
    # In the astronomically unlikely event of a collision, append a counter.
    original_code = code
    for attempt in range(10):
        candidate = code if attempt == 0 else f"{original_code[:7]}{attempt}"
        existing = await db.execute(select(Referral).where(Referral.code == candidate))
        if not existing.scalar_one_or_none():
            code = candidate
            break
    else:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="unable to generate unique referral code",
        )

    referral = Referral(inviter_id=user.id, code=code)
    db.add(referral)
    await db.commit()
    await db.refresh(referral)
    return referral


def _build_invite_link(request: Request, code: str) -> str:
    """Build a frontend registration link containing the referral code."""
    origin = request.headers.get("origin") or settings.FRONTEND_URL
    return f"{origin.rstrip('/')}/register?referral_code={code}"


async def create_referral_use(
    db: AsyncSession, referral: Referral, invitee_id: uuid.UUID
) -> ReferralUse:
    """Create a new ReferralUse row, raising 409 if this invitee already used the code.

    This helper is exported so the registration flow in auth.py can reuse it.
    """
    existing = await db.scalar(
        select(ReferralUse).where(
            ReferralUse.referral_id == referral.id,
            ReferralUse.invitee_id == invitee_id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="you already used this referral code",
        )

    use = ReferralUse(referral_id=referral.id, invitee_id=invitee_id, status="used")
    db.add(use)
    await db.commit()
    await db.refresh(use)
    return use


@router.get("/me", response_model=ApiResponse)
async def get_my_referral(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    referral = await _get_or_create_referral(db, current_user)

    # For backward compatibility, surface the first successful use as the
    # legacy single-invitee fields.
    first_use = await db.scalar(
        select(ReferralUse)
        .where(ReferralUse.referral_id == referral.id)
        .order_by(ReferralUse.created_at)
    )

    data = ReferralCodeOut(
        code=referral.code,
        link=_build_invite_link(request, referral.code),
        status="used" if first_use is not None else referral.status,
        invitee_id=first_use.invitee_id if first_use is not None else None,
        created_at=referral.created_at,
    ).model_dump()
    return {"data": data}


@router.post("/apply", response_model=ApiResponse)
async def apply_referral_code(
    payload: ReferralApplyIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    code = payload.code.strip().upper()
    result = await db.execute(select(Referral).where(Referral.code == code))
    referral = result.scalar_one_or_none()
    if not referral:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invalid referral code")
    if referral.inviter_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot use your own code")

    await create_referral_use(db, referral, current_user.id)
    return {"data": {"code": referral.code, "status": "used"}}


@router.get("/stats", response_model=ApiResponse)
async def get_referral_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    total_sent = await db.scalar(
        select(func.count(Referral.id)).where(Referral.inviter_id == current_user.id)
    )
    total_used = await db.scalar(
        select(func.count(ReferralUse.id))
        .join(Referral)
        .where(Referral.inviter_id == current_user.id)
    )
    total_rewarded = await db.scalar(
        select(func.count(ReferralUse.id))
        .join(Referral)
        .where(
            Referral.inviter_id == current_user.id,
            ReferralUse.status == "rewarded",
        )
    )
    data = ReferralStatsOut(
        total_sent=total_sent or 0,
        total_used=total_used or 0,
        total_rewarded=total_rewarded or 0,
    ).model_dump()
    return {"data": data}
