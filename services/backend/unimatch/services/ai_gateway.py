import json
import logging
import os
from typing import Any

from openai import AsyncOpenAI, OpenAIError
from unimatch.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AIGateway:
    """OpenAI SDK compatible gateway supporting multiple providers."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._clients: dict[str, AsyncOpenAI] = {}

    def _provider_config(self, provider: str) -> dict[str, str | None]:
        provider = provider.lower().strip()
        configs = {
            "deepseek": {
                "base_url": self.settings.DEEPSEEK_BASE_URL,
                "api_key": self.settings.DEEPSEEK_API_KEY,
                "model": self.settings.DEEPSEEK_MODEL,
            },
            "kimi": {
                "base_url": self.settings.KIMI_BASE_URL,
                "api_key": self.settings.KIMI_API_KEY,
                "model": self.settings.KIMI_MODEL,
            },
            "lmstudio": {
                "base_url": self.settings.LMSTUDIO_BASE_URL,
                "api_key": self.settings.LMSTUDIO_API_KEY or "not-needed",
                "model": self.settings.LMSTUDIO_MODEL,
            },
            "opencode": {
                "base_url": self.settings.OPENCODE_BASE_URL,
                "api_key": self.settings.OPENCODE_API_KEY,
                "model": self.settings.OPENCODE_MODEL,
            },
            "mimo": {
                "base_url": self.settings.MIMO_BASE_URL,
                "api_key": self.settings.MIMO_API_KEY,
                "model": self.settings.MIMO_MODEL,
            },
        }
        return configs.get(provider, configs.get(self.settings.AI_PROVIDER, configs["deepseek"]))

    def client(self, provider: str) -> AsyncOpenAI:
        if provider not in self._clients:
            cfg = self._provider_config(provider)
            base_url = cfg["base_url"] or ""
            api_key = cfg["api_key"] or ""
            self._clients[provider] = AsyncOpenAI(base_url=base_url, api_key=api_key)
        return self._clients[provider]

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        provider = (provider or self.settings.AI_PROVIDER).lower().strip()
        cfg = self._provider_config(provider)
        if not cfg.get("api_key") and provider not in ("lmstudio",):
            return {
                "provider": provider,
                "model": cfg.get("model"),
                "content": None,
                "error": f"API key not configured for provider {provider}",
            }
        try:
            client = self.client(provider)
            response = await client.chat.completions.create(
                model=model or cfg.get("model") or "unknown",
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return {
                "provider": provider,
                "model": model or cfg.get("model"),
                "content": response.choices[0].message.content,
            }
        except OpenAIError as e:
            logger.exception("AI provider %s failed", provider)
            return {
                "provider": provider,
                "model": cfg.get("model"),
                "content": None,
                "error": str(e),
            }

    async def generate_questions(
        self, section: str, count: int, profile_text: str
    ) -> list[dict[str, Any]]:
        prompt = (
            f"你是一个校园同学匹配平台的 AI 助手。请根据用户画像为「{section}」板块生成 {count} 个\n"
            f"进阶匹配问题，用于更精确地了解用户。问题可以是单选、多选或文本。\n"
            f"用户画像摘要：{profile_text}\n"
            "请只返回 JSON 数组，格式为：[{\"id\":\"q1\",\"text\":\"问题\",\"type\":\"single_choice\",\"options\":[\"A\",\"B\",\"C\"]}]"
        )
        result = await self.chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        content = result.get("content") or ""
        try:
            # Try to extract JSON from markdown code block
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            questions = json.loads(content.strip())
            if isinstance(questions, list):
                return questions
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI questions JSON: %s", content)
        return []

    async def match_explanation(
        self, me_text: str, target_text: str, section: str
    ) -> dict[str, Any]:
        prompt = (
            f"请用中文简洁说明两位用户在「{section}」板块的匹配理由，列出共同点。\n"
            f"当前用户：{me_text}\n"
            f"目标用户：{target_text}\n"
            "请返回 JSON：{\"explanation\":\"...\",\"highlights\":[\"...\",\"...\"]}"
        )
        result = await self.chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=512,
        )
        content = result.get("content") or ""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            data = json.loads(content.strip())
            return {
                "explanation": data.get("explanation", ""),
                "highlights": data.get("highlights", []),
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI explanation JSON: %s", content)
        return {
            "explanation": "你们有一些共同兴趣，可以聊聊看。",
            "highlights": ["共同兴趣"],
        }


def get_ai_gateway() -> AIGateway:
    return AIGateway()
