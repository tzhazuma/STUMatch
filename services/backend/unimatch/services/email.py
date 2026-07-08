"""Email providers: mock console logger + async SMTP."""
import logging
from abc import ABC, abstractmethod
from typing import Any

import aiosmtplib
from email.mime.text import MIMEText
from email.header import Header

from unimatch.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    @abstractmethod
    async def send_verification_code(self, target: str, code: str, purpose: str) -> dict[str, Any]:
        ...


class MockEmailProvider(EmailProvider):
    """Development email provider: logs the code to stdout / logger."""

    async def send_verification_code(self, target: str, code: str, purpose: str) -> dict[str, Any]:
        msg = f"[MOCK EMAIL] To: {target}, Code: {code}, Purpose: {purpose}"
        print(msg)
        logger.info(msg)
        return {"provider": "mock", "target": target, "ok": True}


class SmtpEmailProvider(EmailProvider):
    """Async SMTP email provider using aiosmtplib."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_verification_code(self, target: str, code: str, purpose: str) -> dict[str, Any]:
        subject = f"UniMatch 验证码 - {purpose}"
        body = f"您的 UniMatch 验证码是：{code}，有效期 10 分钟。"
        message = MIMEText(body, "plain", "utf-8")
        message["Subject"] = Header(subject, "utf-8")
        message["From"] = self.settings.SMTP_FROM or self.settings.SMTP_USER
        message["To"] = target

        await aiosmtplib.send(
            message,
            hostname=self.settings.SMTP_HOST,
            port=self.settings.SMTP_PORT,
            username=self.settings.SMTP_USER,
            password=self.settings.SMTP_PASSWORD,
            start_tls=self.settings.SMTP_PORT not in (465, 465),
            use_tls=self.settings.SMTP_PORT in (465,),
        )
        return {"provider": "smtp", "target": target, "ok": True}


class EmailService:
    def __init__(self, provider: EmailProvider | None = None):
        self.settings = get_settings()
        self._provider = provider

    @property
    def provider(self) -> EmailProvider:
        if self._provider is None:
            if self.settings.effective_email_provider == "smtp" and self.settings.SMTP_HOST:
                self._provider = SmtpEmailProvider(self.settings)
            else:
                self._provider = MockEmailProvider()
        return self._provider

    async def send_verification_code(self, target: str, code: str, purpose: str = "register") -> dict[str, Any]:
        return await self.provider.send_verification_code(target, code, purpose)
