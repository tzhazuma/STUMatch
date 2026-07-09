"""Authentication router: register, login, verification code, refresh, logout."""
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.config import get_settings
from unimatch.database import get_db
from unimatch.models import Profile, User
from unimatch.schemas import (
    ApiResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenData,
    UserOut,
    VerificationCodeRequest,
    VerificationCodeResponse,
)
from unimatch.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_password_hash,
    security_bearer,
    verify_password,
)
from unimatch.services.email import EmailService
from unimatch.services.redis_client import get_redis
from unimatch.services.sms import SmsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()


def _code_key(target: str, purpose: str) -> str:
    return f"verify:{purpose}:{target}"


def _generate_code(length: int = 6) -> str:
    return f"{secrets.randbelow(10 ** length):0{length}d}"


@router.post("/send-verification-code", response_model=ApiResponse)
async def send_verification_code(
    payload: VerificationCodeRequest,
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    target = payload.email or payload.phone
    if not target:
        raise HTTPException(status_code=400, detail="email or phone required")

    if payload.email:
        domain = payload.email.split('@')[1].lower()
        allowed = [d.strip() for d in settings.ALLOWED_EMAIL_DOMAINS.split(",")]
        if not any(domain == d or domain.endswith("." + d) for d in allowed):
            raise HTTPException(status_code=400, detail="请使用学校邮箱注册")

    code = _generate_code()
    await redis.setex(_code_key(target, payload.purpose), 600, code)
    if payload.email:
        result = await EmailService().send_verification_code(payload.email, code, payload.purpose)
    else:
        result = await SmsService().send_verification_code(payload.phone, code, payload.purpose)  # type: ignore[arg-type]
    return {"data": VerificationCodeResponse(**result).model_dump()}


@router.post("/register", response_model=ApiResponse)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    target = payload.email or payload.phone
    if not target:
        raise HTTPException(status_code=400, detail="email or phone required")
    stored = await redis.get(_code_key(target, "register"))
    if not stored or stored != payload.code:
        raise HTTPException(status_code=400, detail="invalid or expired verification code")

    if payload.email:
        existing = await db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="email already registered")
    if payload.phone:
        existing = await db.execute(select(User).where(User.phone == payload.phone))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="phone already registered")

    user = User(
        email=payload.email,
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
        nickname=payload.nickname,
        school=payload.school,
        is_verified_email=bool(payload.email),
    )

    if payload.email:
        domain = payload.email.split('@')[1].lower()
        allowed = [d.strip() for d in settings.ALLOWED_EMAIL_DOMAINS.split(",")]
        if any(domain == d or domain.endswith("." + d) for d in allowed):
            user.is_verified_school = True

    db.add(user)
    await db.flush()

    profile = Profile(user_id=user.id, nickname=payload.nickname)
    db.add(profile)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    await redis.delete(_code_key(target, "register"))
    return {
        "data": TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserOut.model_validate(user).model_dump(),
        ).model_dump()
    }


@router.post("/login", response_model=ApiResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if payload.email:
        result = await db.execute(select(User).where(User.email == payload.email))
    elif payload.phone:
        result = await db.execute(select(User).where(User.phone == payload.phone))
    else:
        raise HTTPException(status_code=400, detail="email or phone required")

    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return {
        "data": TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserOut.model_validate(user).model_dump(),
        ).model_dump()
    }


@router.post("/refresh", response_model=ApiResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        data = decode_token(payload.refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid refresh token") from exc
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="invalid token type")
    result = await db.execute(select(User).where(User.id == data["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return {
        "data": TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserOut.model_validate(user).model_dump(),
        ).model_dump()
    }


@router.post("/logout", response_model=ApiResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    if credentials:
        await blacklist_token(redis, credentials.credentials)
    return {"data": {"ok": True}}
