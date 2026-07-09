"""Pytest fixtures and helpers for UniMatch backend integration tests."""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment before any unimatch module is imported.
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://unimatch:unimatch@localhost:5432/unimatch_test"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["SECRET_KEY"] = "test-secret-key-change-in-production"
os.environ["ALLOWED_EMAIL_DOMAINS"] = "example.com"
os.environ["MAIL_PROVIDER"] = "mock"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["AI_PROVIDER"] = "deepseek"
os.environ["DEBUG"] = "false"

from unimatch.config import get_settings  # noqa: E402
from unimatch.database import Base, get_db  # noqa: E402
from unimatch.main import app, seed_questionnaires  # noqa: E402
from unimatch.services.redis_client import get_redis  # noqa: E402

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for the entire test session.

    A session-scoped loop prevents asyncpg connection-pool / event-loop
    mismatches between tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def override_get_db():
    """FastAPI dependency override yielding a test DB session."""
    async with async_session_maker() as session:
        yield session


async def override_get_redis():
    """FastAPI dependency override returning a test Redis connection."""
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis


@pytest_asyncio.fixture
async def client():
    """Async HTTP client backed by the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", trust_env=False
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    """Reset the test database and Redis before every test."""
    table_names = [table.name for table in Base.metadata.sorted_tables]
    drop_statements = [
        f"DROP TABLE IF EXISTS {name} CASCADE" for name in reversed(table_names)
    ]

    async with engine.connect() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        for stmt in drop_statements:
            await conn.execute(text(stmt))
        await conn.execute(text(
            """
            DO $$
            DECLARE
                t RECORD;
            BEGIN
                FOR t IN (
                    SELECT typname
                    FROM pg_type
                    WHERE typtype = 'e' AND typnamespace = 'public'::regnamespace
                ) LOOP
                    EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(t.typname) || ' CASCADE';
                END LOOP;
            END $$;
            """
        ))
        await conn.run_sync(Base.metadata.create_all, checkfirst=False)
        await conn.commit()
    await seed_questionnaires()

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis.flushdb()
    finally:
        await redis.aclose()
    yield


@pytest_asyncio.fixture
async def redis_client():
    """Provide a Redis client connected to the test Redis database."""
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield redis
    await redis.aclose()


@pytest_asyncio.fixture
async def db_session():
    """Provide a standalone SQLAlchemy session for the test database."""
    async with async_session_maker() as session:
        yield session
        await session.close()


async def register_user(client: AsyncClient, email: str, password: str, nickname: str) -> dict:
    """Helper: send a verification code, retrieve it, and register a new user."""
    send_resp = await client.post(
        "/auth/send-verification-code",
        json={"email": email, "purpose": "register"},
    )
    assert send_resp.status_code == 200, send_resp.text

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        code = await redis.get(f"verify:register:{email}")
    finally:
        await redis.aclose()
    assert code is not None, "verification code was not stored in Redis"

    reg_resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "code": code,
            "password": password,
            "nickname": nickname,
            "school": "Test University",
        },
    )
    assert reg_resp.status_code == 200, reg_resp.text
    return reg_resp.json()["data"]


async def login_user(client: AsyncClient, email: str, password: str) -> dict:
    """Helper: log in and return the token payload."""
    resp = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]
