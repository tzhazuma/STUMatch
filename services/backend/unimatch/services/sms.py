"""SMS providers: mock + Twilio/Aliyun/Tencent placeholders."""
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from unimatch.config import get_settings

logger = logging.getLogger(__name__)


class SmsProvider(ABC):
    @abstractmethod
    async def send_verification_code(self, phone: str, code: str, purpose: str) -> dict[str, Any]:
        ...


class MockSmsProvider(SmsProvider):
    async def send_verification_code(self, phone: str, code: str, purpose: str) -> dict[str, Any]:
        msg = f"[MOCK SMS] To: {phone}, Code: {code}, Purpose: {purpose}"
        print(msg)
        logger.info(msg)
        return {"provider": "mock", "target": phone, "ok": True}


class TwilioSmsProvider(SmsProvider):
    """Minimal Twilio SMS provider using HTTPX."""

    async def send_verification_code(self, phone: str, code: str, purpose: str) -> dict[str, Any]:
        settings = get_settings()
        sid = settings.TWILIO_ACCOUNT_SID
        token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_FROM
        if not sid or not token or not from_number:
            logger.warning("Twilio not configured, falling back to mock SMS")
            return await MockSmsProvider().send_verification_code(phone, code, purpose)

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        body = f"您的 UniMatch 验证码是：{code}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                auth=(sid, token),
                data={"From": from_number, "To": phone, "Body": body},
            )
            resp.raise_for_status()
        return {"provider": "twilio", "target": phone, "ok": True}


class AliyunSmsProvider(SmsProvider):
    """Placeholder for Aliyun Cloud SMS."""

    async def send_verification_code(self, phone: str, code: str, purpose: str) -> dict[str, Any]:
        logger.warning("Aliyun SMS not implemented; using mock")
        return await MockSmsProvider().send_verification_code(phone, code, purpose)


class TencentSmsProvider(SmsProvider):
    """Placeholder for Tencent Cloud SMS."""

    async def send_verification_code(self, phone: str, code: str, purpose: str) -> dict[str, Any]:
        logger.warning("Tencent SMS not implemented; using mock")
        return await MockSmsProvider().send_verification_code(phone, code, purpose)


class SmsService:
    def __init__(self, provider: SmsProvider | None = None):
        self._provider = provider

    @property
    def provider(self) -> SmsProvider:
        if self._provider is None:
            settings = get_settings()
            provider_name = (settings.SMS_PROVIDER or "mock").lower()
            if provider_name == "twilio":
                self._provider = TwilioSmsProvider()
            elif provider_name == "aliyun":
                self._provider = AliyunSmsProvider()
            elif provider_name == "tencent":
                self._provider = TencentSmsProvider()
            else:
                self._provider = MockSmsProvider()
        return self._provider

    async def send_verification_code(self, phone: str, code: str, purpose: str = "register") -> dict[str, Any]:
        return await self.provider.send_verification_code(phone, code, purpose)
