"""Smoke tests for the AI gateway client."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from unimatch.config import Settings
from unimatch.services.ai_gateway import AIGateway


def _make_response(content: str):
    """Build a minimal OpenAI chat-completion response stub."""
    message = type("Message", (), {"content": content})()
    choice = type("Choice", (), {"message": message})()
    return type("Response", (), {"choices": [choice]})()


def _patch_openai(mock_create):
    """Patch AsyncOpenAI so new AIGateway instances use ``mock_create``."""
    return patch(
        "unimatch.services.ai_gateway.AsyncOpenAI",
        return_value=type(
            "Client",
            (),
            {
                "chat": type(
                    "Chat",
                    (),
                    {
                        "completions": type(
                            "Completions", (), {"create": mock_create}
                        )()
                    },
                )()
            },
        )(),
    )


@pytest.fixture
def lmstudio_settings():
    """Settings that select the no-key LMStudio provider for unit tests."""
    return Settings(AI_PROVIDER="lmstudio")


async def test_generate_questions_parses_json_array(lmstudio_settings):
    """generate_questions returns a list of questions with required fields."""
    questions = [
        {
            "id": "q1",
            "text": "你喜欢的编程语言是什么？",
            "type": "single_choice",
            "options": ["Python", "C++", "Java"],
        },
        {
            "id": "q2",
            "text": "描述一下你的理想学习伙伴",
            "type": "text",
        },
    ]
    content = json.dumps(questions, ensure_ascii=False)
    mock_create = AsyncMock(return_value=_make_response(content))

    with _patch_openai(mock_create):
        gateway = AIGateway(settings=lmstudio_settings)
        result = await gateway.generate_questions("academic", 2, "CS student")

    assert isinstance(result, list)
    assert len(result) == 2
    for item, expected in zip(result, questions):
        assert item["id"] == expected["id"]
        assert item["text"] == expected["text"]
        assert item["type"] == expected["type"]
    assert result[0].get("options") == ["Python", "C++", "Java"]


async def test_generate_questions_parses_json_from_markdown(lmstudio_settings):
    """generate_questions extracts JSON from a markdown code block."""
    questions = [{"id": "q1", "text": "问题一", "type": "text"}]
    content = "```json\n" + json.dumps(questions, ensure_ascii=False) + "\n```"
    mock_create = AsyncMock(return_value=_make_response(content))

    with _patch_openai(mock_create):
        gateway = AIGateway(settings=lmstudio_settings)
        result = await gateway.generate_questions("daily", 1, "user profile")

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == "q1"


async def test_generate_questions_returns_empty_list_on_invalid_json(lmstudio_settings):
    """generate_questions gracefully falls back to an empty list."""
    mock_create = AsyncMock(return_value=_make_response("not valid json"))

    with _patch_openai(mock_create):
        gateway = AIGateway(settings=lmstudio_settings)
        result = await gateway.generate_questions("daily", 1, "user profile")

    assert result == []


async def test_match_explanation_parses_json(lmstudio_settings):
    """match_explanation returns explanation and highlights from JSON content."""
    payload = {
        "explanation": "你们都热爱摄影和机器学习，话题契合。",
        "highlights": ["摄影", "机器学习"],
    }
    content = json.dumps(payload, ensure_ascii=False)
    mock_create = AsyncMock(return_value=_make_response(content))

    with _patch_openai(mock_create):
        gateway = AIGateway(settings=lmstudio_settings)
        result = await gateway.match_explanation(
            me_text="摄影，机器学习",
            target_text="摄影，深度学习",
            section="daily",
        )

    assert "explanation" in result
    assert "highlights" in result
    assert result["explanation"] == payload["explanation"]
    assert result["highlights"] == payload["highlights"]


async def test_match_explanation_parses_json_from_markdown(lmstudio_settings):
    """match_explanation extracts JSON from a markdown code block."""
    payload = {"explanation": "测试解释", "highlights": ["共同点"]}
    content = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
    mock_create = AsyncMock(return_value=_make_response(content))

    with _patch_openai(mock_create):
        gateway = AIGateway(settings=lmstudio_settings)
        result = await gateway.match_explanation(
            me_text="A", target_text="B", section="academic"
        )

    assert result["explanation"] == payload["explanation"]
    assert result["highlights"] == payload["highlights"]


async def test_match_explanation_returns_default_on_invalid_json(lmstudio_settings):
    """match_explanation returns a default message when JSON parsing fails."""
    mock_create = AsyncMock(return_value=_make_response("not json"))

    with _patch_openai(mock_create):
        gateway = AIGateway(settings=lmstudio_settings)
        result = await gateway.match_explanation(
            me_text="A", target_text="B", section="dating"
        )

    assert "explanation" in result
    assert "highlights" in result
    assert isinstance(result["highlights"], list)


async def test_match_explanation_returns_default_on_missing_key(lmstudio_settings):
    """match_explanation fills in defaults when the response JSON lacks fields."""
    content = json.dumps({"explanation": "只有解释"}, ensure_ascii=False)
    mock_create = AsyncMock(return_value=_make_response(content))

    with _patch_openai(mock_create):
        gateway = AIGateway(settings=lmstudio_settings)
        result = await gateway.match_explanation(
            me_text="A", target_text="B", section="daily"
        )

    assert result["explanation"] == "只有解释"
    assert result["highlights"] == []


async def test_gateway_returns_error_when_api_key_missing():
    """chat_completion returns an error dict when no API key is configured."""
    gateway = AIGateway()
    result = await gateway.chat_completion(
        messages=[{"role": "user", "content": "hello"}],
        provider="kimi",
    )
    assert result["provider"] == "kimi"
    assert result["content"] is None
    assert "error" in result
    assert "API key not configured" in result["error"]
