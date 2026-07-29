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

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # Email domain whitelist
    ALLOWED_EMAIL_DOMAINS: str = "shanghaitech.edu.cn"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/unimatch"
    VECTOR_DIMENSION: int = 384

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # SMTP / Email — generic (used when MAIL_PROVIDER=smtp)
    MAIL_PROVIDER: Optional[str] = None  # smtp | netease_126 | shanghaitech | mock
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # SMTP / Email — 126 preset (used when MAIL_PROVIDER=netease_126)
    NETEASE126_SMTP_HOST: Optional[str] = None
    NETEASE126_SMTP_PORT: int = 465
    NETEASE126_SENDER: Optional[str] = None
    NETEASE126_USERNAME: Optional[str] = None
    NETEASE126_PASSWORD: Optional[str] = None

    # SMTP / Email — ShanghaiTech preset (used when MAIL_PROVIDER=shanghaitech)
    SHANGHAITECH_SMTP_HOST: Optional[str] = None
    SHANGHAITECH_SMTP_PORT: int = 465
    SHANGHAITECH_SENDER: Optional[str] = None
    SHANGHAITECH_USERNAME: Optional[str] = None
    SHANGHAITECH_PASSWORD: Optional[str] = None

    # Verification code TTL (seconds) and rate limits
    CODE_TTL: int = 600
    RATE_LIMIT_PER_EMAIL: int = 5
    RATE_LIMIT_PER_PHONE: int = 5

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
    OPENCODE_API_KEY: Optional[str] = None
    OPENCODE_BASE_URL: str = "https://api.opencode.example.com/v1"
    OPENCODE_MODEL: str = "opencode-7b"
    MIMO_API_KEY: Optional[str] = None
    MIMO_BASE_URL: str = "https://api.mimo.example.com/v1"
    MIMO_MODEL: str = "mimo-7b"

    # Matching / Recommendations
    EMBEDDING_MODEL: Optional[str] = None  # e.g. BAAI/bge-m3; disabled by default
    RECOMMENDATION_WEIGHTS_PATH: str = "services/ai/outputs/recommendation_weights.json"
    MMR_LAMBDA: float = 0.7  # 1.0 = relevance only, 0.0 = diversity only

    # Moderation
    MODERATION_PROVIDER: Optional[str] = None  # openai, aliyun, tencent
    MODERATION_SENSITIVE_WORDS: Optional[str] = None  # comma-separated

    # CORS (comma-separated origins or "*" for demo; production should list exact origins)
    CORS_ORIGINS: str = "*"

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
        """Return 'smtp' if any SMTP convention is configured, else 'mock'."""
        if self.MAIL_PROVIDER and self.MAIL_PROVIDER.lower() not in ("mock", ""):
            return "smtp"
        # Auto-detect: if any SMTP host is set, treat as smtp
        if self.SMTP_HOST or self.NETEASE126_SMTP_HOST or self.SHANGHAITECH_SMTP_HOST:
            return "smtp"
        return "mock"

    @property
    def effective_smtp_host(self) -> Optional[str]:
        provider = (self.MAIL_PROVIDER or "").lower()
        if provider == "netease_126":
            return self.NETEASE126_SMTP_HOST
        if provider == "shanghaitech":
            return self.SHANGHAITECH_SMTP_HOST
        return self.SMTP_HOST

    @property
    def effective_smtp_port(self) -> int:
        provider = (self.MAIL_PROVIDER or "").lower()
        if provider == "netease_126":
            return self.NETEASE126_SMTP_PORT
        if provider == "shanghaitech":
            return self.SHANGHAITECH_SMTP_PORT
        return self.SMTP_PORT

    @property
    def effective_smtp_user(self) -> Optional[str]:
        provider = (self.MAIL_PROVIDER or "").lower()
        if provider == "netease_126":
            return self.NETEASE126_USERNAME
        if provider == "shanghaitech":
            return self.SHANGHAITECH_USERNAME
        return self.SMTP_USER

    @property
    def effective_smtp_password(self) -> Optional[str]:
        provider = (self.MAIL_PROVIDER or "").lower()
        if provider == "netease_126":
            return self.NETEASE126_PASSWORD
        if provider == "shanghaitech":
            return self.SHANGHAITECH_PASSWORD
        return self.SMTP_PASSWORD

    @property
    def effective_smtp_from(self) -> Optional[str]:
        provider = (self.MAIL_PROVIDER or "").lower()
        if provider == "netease_126":
            return self.NETEASE126_SENDER or self.NETEASE126_USERNAME
        if provider == "shanghaitech":
            return self.SHANGHAITECH_SENDER or self.SHANGHAITECH_USERNAME
        return self.SMTP_FROM or self.SMTP_USER

    @property
    def effective_ai_provider(self) -> str:
        return self.AI_PROVIDER.lower().strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
