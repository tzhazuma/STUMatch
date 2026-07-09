"""Application settings using Pydantic Settings."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """UniMatch configuration loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "UniMatch"
    DEBUG: bool = False
    SECRET_KEY: str = ""

    # Email domain whitelist
    ALLOWED_EMAIL_DOMAINS: str = "shanghaitech.edu.cn"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/unimatch"
    VECTOR_DIMENSION: int = 384

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # SMTP / Email
    MAIL_PROVIDER: Optional[str] = None  # smtp or mock
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # SMS
    SMS_PROVIDER: Optional[str] = None  # twilio, aliyun, tencent, mock
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM: Optional[str] = None

    # Storage
    STORAGE_PROVIDER: str = "local"  # local or minio
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET: str = "unimatch"
    STORAGE_PUBLIC_URL: str = "http://localhost:8000/static"
    LOCAL_STORAGE_PATH: str = "uploads"

    # AI Gateway
    AI_PROVIDER: str = "deepseek"
    AI_BASE_URL: Optional[str] = None
    AI_API_KEY: Optional[str] = None
    AI_MODEL: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    KIMI_API_KEY: Optional[str] = None
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "moonshot-v1-8k"
    LMSTUDIO_API_KEY: Optional[str] = "not-needed"
    LMSTUDIO_BASE_URL: str = "http://localhost:1234/v1"
    LMSTUDIO_MODEL: str = "local-model"
    OPCODE_API_KEY: Optional[str] = None
    OPCODE_BASE_URL: str = "https://api.opencode.example.com/v1"
    OPCODE_MODEL: str = "opencode-7b"
    MIMO_API_KEY: Optional[str] = None
    MIMO_BASE_URL: str = "https://api.mimo.example.com/v1"
    MIMO_MODEL: str = "mimo-7b"

    # Moderation
    MODERATION_SENSITIVE_WORDS: Optional[str] = None  # comma-separated

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    @property
    def celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @property
    def effective_email_provider(self) -> str:
        if self.MAIL_PROVIDER:
            return self.MAIL_PROVIDER
        return "mock"

    @property
    def effective_ai_provider(self) -> str:
        return self.AI_PROVIDER.lower().strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
