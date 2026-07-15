"""Tests for the legal pages and registration consent recording."""
import uuid

from sqlalchemy import select

from tests.conftest import register_user

from unimatch.models import UserConsent


async def test_get_terms_of_service(client):
    """GET /legal/terms returns the Markdown terms of service document."""
    resp = await client.get("/legal/terms")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "用户服务协议"
    assert "# UniMatch" in data["content"]
    assert "2026-07-15" in data["updated_at"]


async def test_get_privacy_policy(client):
    """GET /legal/privacy returns the Markdown privacy policy document."""
    resp = await client.get("/legal/privacy")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "隐私政策"
    assert "最后更新日期" in data["content"]
    assert "2026-07-15" in data["updated_at"]


async def test_registration_records_user_consents(client, db_session):
    """Registering a user records granted consents for ToS and privacy policy."""
    user_data = await register_user(
        client, "legal-consent@example.com", "password123", "ConsentUser"
    )
    user_id = uuid.UUID(user_data["user"]["id"])

    result = await db_session.execute(
        select(UserConsent).where(UserConsent.user_id == user_id)
    )
    consents = result.scalars().all()

    consent_types = {c.consent_type: c.granted for c in consents}
    assert consent_types.get("terms_of_service") is True
    assert consent_types.get("privacy_policy") is True
    assert len(consents) == 2
