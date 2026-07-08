"""Tests for the questionnaire endpoints."""
from tests.conftest import register_user, login_user


async def test_list_questionnaires(client):
    """GET /questionnaires returns active questionnaires."""
    await register_user(client, "test-questionnaires@example.com", "password123", "Ivy")
    tokens = await login_user(client, "test-questionnaires@example.com", "password123")

    resp = await client.get(
        "/questionnaires",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    slugs = {q["slug"] for q in data}
    assert "basic" in slugs


async def test_submit_questionnaire_response(client):
    """POST /questionnaires/{slug}/responses stores answers."""
    await register_user(client, "test-response@example.com", "password123", "Jack")
    tokens = await login_user(client, "test-response@example.com", "password123")

    answers = {
        "gender": "male",
        "birth_date": "1999-03-20",
        "education_level": "undergraduate",
        "major": "Mathematics",
        "interests": ["algebra", "topology"],
        "mbti": "INTP",
        "location": "Beijing",
        "bio": "Math enthusiast",
    }
    resp = await client.post(
        "/questionnaires/basic/responses",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"answers": answers},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["answers"] == answers
    assert data["user_id"] == tokens["user"]["id"]


async def test_submit_questionnaire_response_updates_existing(client):
    """Submitting a response twice updates the existing response."""
    await register_user(client, "test-response-update@example.com", "password123", "Kate")
    tokens = await login_user(client, "test-response-update@example.com", "password123")

    first = {"major": "Physics"}
    await client.post(
        "/questionnaires/basic/responses",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"answers": first},
    )

    second = {"major": "Chemistry"}
    resp = await client.post(
        "/questionnaires/basic/responses",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"answers": second},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["answers"] == second


async def test_submit_response_unknown_questionnaire(client):
    """Submitting to a non-existent questionnaire returns 404."""
    await register_user(client, "test-unknown-q@example.com", "password123", "Leo")
    tokens = await login_user(client, "test-unknown-q@example.com", "password123")

    resp = await client.post(
        "/questionnaires/no-such-questionnaire/responses",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"answers": {"foo": "bar"}},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "questionnaire not found"
