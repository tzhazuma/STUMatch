"""Tests for the referral invite feature."""
import pytest
from httpx import AsyncClient

from tests.conftest import register_user


@pytest.mark.asyncio
async def test_get_my_referral_creates_deterministic_code(client: AsyncClient):
    data = await register_user(client, "user-a@example.com", "password123", "User A")
    token = data["access_token"]

    resp = await client.get("/referrals/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert len(body["code"]) == 8
    assert body["status"] == "pending"
    assert body["link"].endswith(f"?referral_code={body['code']}")

    # Second call returns the same code.
    resp2 = await client.get("/referrals/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.json()["data"]["code"] == body["code"]


@pytest.mark.asyncio
async def test_apply_referral_code(client: AsyncClient):
    inviter = await register_user(client, "inviter@example.com", "password123", "Inviter")
    inviter_token = inviter["access_token"]

    code_resp = await client.get(
        "/referrals/me", headers={"Authorization": f"Bearer {inviter_token}"}
    )
    code = code_resp.json()["data"]["code"]

    invitee = await register_user(client, "invitee@example.com", "password123", "Invitee")
    invitee_token = invitee["access_token"]

    apply_resp = await client.post(
        "/referrals/apply",
        json={"code": code},
        headers={"Authorization": f"Bearer {invitee_token}"},
    )
    assert apply_resp.status_code == 200, apply_resp.text
    assert apply_resp.json()["data"]["status"] == "used"

    # Cannot apply again.
    repeat = await client.post(
        "/referrals/apply",
        json={"code": code},
        headers={"Authorization": f"Bearer {invitee_token}"},
    )
    assert repeat.status_code == 409


@pytest.mark.asyncio
async def test_cannot_apply_own_code(client: AsyncClient):
    data = await register_user(client, "self@example.com", "password123", "Self")
    token = data["access_token"]

    code_resp = await client.get("/referrals/me", headers={"Authorization": f"Bearer {token}"})
    code = code_resp.json()["data"]["code"]

    resp = await client.post(
        "/referrals/apply",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_referral_stats(client: AsyncClient):
    inviter = await register_user(client, "stats@example.com", "password123", "Stats")
    inviter_token = inviter["access_token"]

    code = (
        await client.get("/referrals/me", headers={"Authorization": f"Bearer {inviter_token}"})
    ).json()["data"]["code"]

    stats_before = await client.get(
        "/referrals/stats", headers={"Authorization": f"Bearer {inviter_token}"}
    )
    assert stats_before.json()["data"] == {
        "total_sent": 1,
        "total_used": 0,
        "total_rewarded": 0,
    }

    invitee = await register_user(client, "stats-user@example.com", "password123", "Invitee")
    invitee_token = invitee["access_token"]
    await client.post(
        "/referrals/apply",
        json={"code": code},
        headers={"Authorization": f"Bearer {invitee_token}"},
    )

    stats_after = await client.get(
        "/referrals/stats", headers={"Authorization": f"Bearer {inviter_token}"}
    )
    assert stats_after.json()["data"]["total_used"] == 1


@pytest.mark.asyncio
async def test_register_with_referral_code(client: AsyncClient):
    inviter = await register_user(client, "reg-inviter@example.com", "password123", "Inviter")
    inviter_token = inviter["access_token"]
    code = (
        await client.get("/referrals/me", headers={"Authorization": f"Bearer {inviter_token}"})
    ).json()["data"]["code"]

    # Send verification code for the new user.
    email = "reg-invitee@example.com"
    send_resp = await client.post(
        "/auth/send-verification-code", json={"email": email, "purpose": "register"}
    )
    assert send_resp.status_code == 200

    from redis.asyncio import Redis
    from unimatch.config import get_settings

    settings = get_settings()
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        verification_code = await redis.get(f"verify:register:{email}")
    finally:
        await redis.aclose()

    reg_resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "code": verification_code,
            "password": "password123",
            "nickname": "RegInvitee",
            "school": "Test University",
            "referral_code": code,
        },
    )
    assert reg_resp.status_code == 200, reg_resp.text

    stats = await client.get("/referrals/stats", headers={"Authorization": f"Bearer {inviter_token}"})
    assert stats.json()["data"]["total_used"] == 1


@pytest.mark.asyncio
async def test_referral_code_can_be_used_by_multiple_invitees(client: AsyncClient):
    inviter = await register_user(client, "multi-inviter@example.com", "password123", "Multi Inviter")
    inviter_token = inviter["access_token"]

    code = (
        await client.get("/referrals/me", headers={"Authorization": f"Bearer {inviter_token}"})
    ).json()["data"]["code"]

    invitee_a = await register_user(client, "invitee-a@example.com", "password123", "Invitee A")
    invitee_b = await register_user(client, "invitee-b@example.com", "password123", "Invitee B")

    for invitee_token in (invitee_a["access_token"], invitee_b["access_token"]):
        resp = await client.post(
            "/referrals/apply",
            json={"code": code},
            headers={"Authorization": f"Bearer {invitee_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "used"

    stats = await client.get("/referrals/stats", headers={"Authorization": f"Bearer {inviter_token}"})
    assert stats.json()["data"]["total_used"] == 2


@pytest.mark.asyncio
async def test_same_invitee_cannot_apply_same_code_twice(client: AsyncClient):
    inviter = await register_user(client, "repeat-inviter@example.com", "password123", "Repeat Inviter")
    inviter_token = inviter["access_token"]

    code = (
        await client.get("/referrals/me", headers={"Authorization": f"Bearer {inviter_token}"})
    ).json()["data"]["code"]

    invitee = await register_user(client, "repeat-invitee@example.com", "password123", "Repeat Invitee")
    invitee_token = invitee["access_token"]

    first = await client.post(
        "/referrals/apply",
        json={"code": code},
        headers={"Authorization": f"Bearer {invitee_token}"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/referrals/apply",
        json={"code": code},
        headers={"Authorization": f"Bearer {invitee_token}"},
    )
    assert second.status_code == 409
    assert "already used" in second.json()["detail"].lower()
