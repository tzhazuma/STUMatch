"""Tests for content moderation service and admin config endpoints."""
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.conftest import login_user, register_user
from unimatch.models import ModerationConfig, ModerationLog, User, UserRole
from unimatch.services.moderation import (
    DFAFilter,
    DEFAULT_WORDS_META,
    ModerationService,
    load_moderation_configs,
)


def test_default_words_count_and_categories():
    """DEFAULT_SENSITIVE_WORDS covers at least 80 words and all categories."""
    assert len(DEFAULT_WORDS_META) >= 80
    categories = {w["category"] for w in DEFAULT_WORDS_META}
    assert {"porn", "gamble", "drug", "fraud", "insult", "politics"} <= categories


def test_dfa_basic_hit():
    f = DFAFilter()
    assert f.contains("这条消息包含色情内容")
    words = f.find_all("这条消息包含色情内容")
    assert "色情" in words


def test_dfa_case_insensitive():
    f = DFAFilter()
    assert f.contains("NMSL")
    assert f.contains("Nmsl")


def test_dfa_homophone_bypass():
    f = DFAFilter()
    assert f.contains("你ma死了")
    assert f.contains("你MA死了")
    assert f.contains("你m@死了")


def test_dfa_digit_substitution():
    f = DFAFilter()
    assert f.contains("1夜情")
    assert f.contains("一1夜情")


def test_dfa_no_hit():
    f = DFAFilter()
    assert not f.contains("今天天气真好，一起去图书馆学习吗")
    assert f.find_all("今天天气真好") == []


def test_dfa_avoids_overlapping_matches():
    f = DFAFilter(["色情", "情色"])
    words = f.find_all("色情情色")
    assert set(words) == {"色情", "情色"}


def test_dfa_contact_variant():
    """Extra contact words can be detected via canonical variants."""
    f = DFAFilter(["微信"])
    assert f.contains("加我wechat")
    assert f.contains("加我vx")
    assert f.contains("加我微信")


async def test_load_moderation_configs(db_session):
    db_session.add(
        ModerationConfig(
            word="测试违禁词", category="insult", severity="medium", enabled=True
        )
    )
    await db_session.commit()
    configs = await load_moderation_configs(db_session)
    assert any(c["word"] == "测试违禁词" for c in configs)


async def test_service_with_extra_words():
    service = ModerationService(
        extra_words=[
            {"word": "测试违禁词", "category": "insult", "severity": "medium"}
        ]
    )
    result = service.check_text("这里有测试违禁词")
    assert result["triggered"] is True
    assert "测试违禁词" in result["words"]


async def test_async_moderate_logs_local_hit(db_session):
    service = ModerationService()
    result = await service.async_moderate("这条消息包含色情内容", "chat", db=db_session)
    assert result["triggered"] is True
    assert "色情" in result["words"]
    logs = (await db_session.execute(select(ModerationLog))).scalars().all()
    assert any(l.text == "这条消息包含色情内容" and l.triggered for l in logs)


async def test_cloud_moderation_called_and_logged(db_session, monkeypatch):
    service = ModerationService()
    monkeypatch.setattr(service, "provider", "openai")
    result = await service.async_moderate(
        "this contains cloud_bad marker", "chat", db=db_session
    )
    assert result["triggered"] is True
    assert result["cloud_triggered"] is True
    assert result["ai_score"] is not None
    logs = (await db_session.execute(select(ModerationLog))).scalars().all()
    assert any(
        l.text == "this contains cloud_bad marker" and l.ai_score is not None
        for l in logs
    )


async def test_cloud_moderation_skipped_for_strong_local_hit(db_session, monkeypatch):
    service = ModerationService()
    monkeypatch.setattr(service, "provider", "openai")
    # "色情" is a high-severity word, so cloud check should be skipped.
    result = await service.async_moderate("色情", "chat", db=db_session)
    assert result["triggered"] is True
    assert result["cloud_triggered"] is False
    assert result["ai_score"] is None


async def _admin_headers(client, db_session, email, password, nickname):
    data = await register_user(client, email, password, nickname)
    user = await db_session.get(User, UUID(data["user"]["id"]))
    user.role = UserRole.ADMIN
    await db_session.commit()
    tokens = await login_user(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_admin_moderation_config_crud(client, db_session):
    headers = await _admin_headers(
        client, db_session, "admin-crud@example.com", "password123", "AdminCrud"
    )

    # Create
    resp = await client.post(
        "/admin/moderation-configs",
        headers=headers,
        json={"word": "测试词", "category": "fraud", "severity": "high"},
    )
    assert resp.status_code == 200
    config_id = resp.json()["data"]["id"]

    # List
    resp = await client.get("/admin/moderation-configs", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert any(c["word"] == "测试词" for c in items)

    # Toggle
    resp = await client.put(
        f"/admin/moderation-configs/{config_id}/toggle", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["enabled"] is False

    # Delete
    resp = await client.delete(
        f"/admin/moderation-configs/{config_id}", headers=headers
    )
    assert resp.status_code == 200

    resp = await client.get("/admin/moderation-configs", headers=headers)
    items = resp.json()["data"]["items"]
    assert not any(c["word"] == "测试词" for c in items)


async def test_admin_config_duplicate_word_rejected(client, db_session):
    headers = await _admin_headers(
        client, db_session, "admin-dup@example.com", "password123", "AdminDup"
    )
    payload = {"word": "唯一词", "category": "insult", "severity": "medium"}
    resp = await client.post("/admin/moderation-configs", headers=headers, json=payload)
    assert resp.status_code == 200
    resp = await client.post("/admin/moderation-configs", headers=headers, json=payload)
    assert resp.status_code == 409


async def test_message_board_moderation_blocks_and_logs(client, db_session):
    await register_user(client, "board-user@example.com", "password123", "BoardUser")
    tokens = await login_user(client, "board-user@example.com", "password123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    user_id = tokens["user"]["id"]

    resp = await client.post(
        "/message-board/academic",
        headers=headers,
        json={"owner_id": user_id, "content": "这是一条色情消息"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "包含违禁词"

    logs = (await db_session.execute(select(ModerationLog))).scalars().all()
    assert any(
        l.text == "这是一条色情消息" and l.source == "board" and l.triggered
        for l in logs
    )


async def test_ws_chat_moderation_blocks_banned_word(db_session):
    """WebSocket chat path uses DB configs and async_moderate to block words."""
    db_session.add(
        ModerationConfig(
            word="ws_bad_word", category="insult", severity="high", enabled=True
        )
    )
    await db_session.commit()

    configs = await load_moderation_configs(db_session)
    moderation = ModerationService(extra_words=configs)
    result = await moderation.async_moderate(
        "hello ws_bad_word", source="chat", db=db_session
    )
    assert result["triggered"] is True
    assert "ws_bad_word" in result["words"]

    logs = (await db_session.execute(select(ModerationLog))).scalars().all()
    assert any(
        l.text == "hello ws_bad_word" and l.source == "chat" and l.triggered
        for l in logs
    )


async def test_profile_update_rejects_high_severity_word(client, db_session):
    await register_user(client, "profile-bad@example.com", "password123", "GoodNick")
    tokens = await login_user(client, "profile-bad@example.com", "password123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.put(
        "/profiles/me",
        headers=headers,
        json={"nickname": "色情昵称", "bio": "正常简介"},
    )
    assert resp.status_code == 400
    assert "色情" in resp.json()["detail"]

    logs = (await db_session.execute(select(ModerationLog))).scalars().all()
    assert any(
        l.text == "色情昵称" and l.source == "profile" and l.triggered for l in logs
    )


async def test_profile_update_accepts_clean_text(client, db_session):
    await register_user(client, "profile-clean@example.com", "password123", "CleanNick")
    tokens = await login_user(client, "profile-clean@example.com", "password123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.put(
        "/profiles/me",
        headers=headers,
        json={"nickname": "CleanNick2", "bio": "喜欢读书和旅行"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nickname"] == "CleanNick2"
    assert data["bio"] == "喜欢读书和旅行"
