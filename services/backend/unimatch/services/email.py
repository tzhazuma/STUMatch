"""Email providers: mock console logger + async SMTP with error handling."""
import logging
from abc import ABC, abstractmethod
from typing import Any

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from unimatch.config import Settings, get_settings

logger = logging.getLogger(__name__)

_HTML_TEMPLATE = """\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
  <div style="text-align: center; margin-bottom: 24px;">
    <h1 style="color: #6366f1; font-size: 24px; margin: 0;">SKDMatch</h1>
    <p style="color: #64748b; font-size: 13px; margin: 4px 0 0;">科爱捏 · 校内互助交流平台</p>
  </div>
  <div style="background: #f8fafc; border-radius: 12px; padding: 24px; text-align: center;">
    <p style="color: #334155; font-size: 14px; margin: 0 0 12px;">您的验证码是</p>
    <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #6366f1; margin: 0 0 12px;">{code}</div>
    <p style="color: #94a3b8; font-size: 12px; margin: 0;">有效期 10 分钟，请勿泄露给他人</p>
  </div>
  <p style="color: #94a3b8; font-size: 11px; text-align: center; margin-top: 20px;">
    如非本人操作，请忽略此邮件。
  </p>
</div>
"""


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
    """Async SMTP email provider using aiosmtplib with resolved settings."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_verification_code(self, target: str, code: str, purpose: str) -> dict[str, Any]:
        subject = f"SKDMatch 验证码 - {purpose}"
        plain_body = f"您的 SKDMatch 验证码是：{code}，有效期 10 分钟。如非本人操作请忽略。"
        html_body = _HTML_TEMPLATE.format(code=code)

        message = MIMEMultipart("alternative")
        message["Subject"] = Header(subject, "utf-8")
        message["From"] = self.settings.effective_smtp_from or self.settings.effective_smtp_user
        message["To"] = target
        message.attach(MIMEText(plain_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        host = self.settings.effective_smtp_host
        port = self.settings.effective_smtp_port
        user = self.settings.effective_smtp_user
        password = self.settings.effective_smtp_password

        try:
            await aiosmtplib.send(
                message,
                hostname=host,
                port=port,
                username=user,
                password=password,
                start_tls=(port != 465),
                use_tls=(port == 465),
            )
            logger.info("Email sent to %s via %s:%d", target, host, port)
            return {"provider": "smtp", "target": target, "ok": True}
        except aiosmtplib.SMTPAuthenticationError as exc:
            logger.error("SMTP auth failed for %s@%s: %s", user, host, exc)
            raise
        except aiosmtplib.SMTPException as exc:
            logger.error("SMTP error sending to %s: %s", target, exc)
            raise
        except Exception as exc:
            logger.exception("Unexpected error sending email to %s", target)
            raise


class EmailService:
    def __init__(self, provider: EmailProvider | None = None):
        self.settings = get_settings()
        self._provider = provider

    @property
    def provider(self) -> EmailProvider:
        if self._provider is None:
            if self.settings.effective_email_provider == "smtp" and self.settings.effective_smtp_host:
                self._provider = SmtpEmailProvider(self.settings)
                logger.info(
                    "Email provider: SMTP (%s:%d, user=%s)",
                    self.settings.effective_smtp_host,
                    self.settings.effective_smtp_port,
                    self.settings.effective_smtp_user,
                )
            else:
                self._provider = MockEmailProvider()
                logger.info("Email provider: MOCK (no SMTP configured)")
        return self._provider

    async def send_verification_code(self, target: str, code: str, purpose: str = "register") -> dict[str, Any]:
        return await self.provider.send_verification_code(target, code, purpose)
