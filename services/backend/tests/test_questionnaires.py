"""Tests for the questionnaire endpoints."""
from datetime import date

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
        "notification_consent": "yes_all",
        "school_verification_preference": "edu_email",
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

    first = {
        "gender": "male",
        "education_level": "undergraduate",
        "major": "Physics",
        "interests": ["physics"],
        "notification_consent": "yes_all",
        "school_verification_preference": "edu_email",
    }
    await client.post(
        "/questionnaires/basic/responses",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"answers": first},
    )

    second = {
        "gender": "male",
        "education_level": "master",
        "major": "Chemistry",
        "interests": ["chemistry"],
        "notification_consent": "yes_all",
        "school_verification_preference": "edu_email",
    }
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


VALID_QUESTION_TYPES = {"single_choice", "multiple_choice", "text", "rating", "tags", "date"}
REQUIRED_QUESTION_FIELDS = {"id", "text", "type"}


async def test_questionnaire_questions_have_valid_types(client):
    """Every question uses a supported type and has required metadata."""
    await register_user(client, "test-q-types@example.com", "password123", "Mia")
    tokens = await login_user(client, "test-q-types@example.com", "password123")

    resp = await client.get(
        "/questionnaires",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    for q in resp.json()["data"]:
        assert len(q["questions"]) >= 1, f"{q['slug']} has no questions"
        for question in q["questions"]:
            assert REQUIRED_QUESTION_FIELDS <= set(question.keys())
            assert question["type"] in VALID_QUESTION_TYPES
            if question["type"] in {"single_choice", "multiple_choice"}:
                assert question.get("options")
                assert all("value" in opt and "label" in opt for opt in question["options"])


async def test_basic_questionnaire_has_improved_questions(client):
    """Basic questionnaire includes notification and verification questions."""
    await register_user(client, "test-basic-q@example.com", "password123", "Noah")
    tokens = await login_user(client, "test-basic-q@example.com", "password123")

    resp = await client.get(
        "/questionnaires/basic",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    questions = {q["id"]: q for q in resp.json()["data"]["questions"]}
    assert "notification_consent" in questions
    assert "school_verification_preference" in questions
    assert questions["birth_date"]["type"] == "date"


async def test_academic_questionnaire_has_collaboration_style(client):
    """Academic questionnaire includes collaboration style question."""
    await register_user(client, "test-academic-q@example.com", "password123", "Olivia")
    tokens = await login_user(client, "test-academic-q@example.com", "password123")

    resp = await client.get(
        "/questionnaires/academic",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    questions = {q["id"]: q for q in resp.json()["data"]["questions"]}
    assert "collaboration_style" in questions
    assert questions["collaboration_style"]["type"] == "single_choice"


async def test_daily_questionnaire_has_sports_and_dietary(client):
    """Daily questionnaire includes sport/game and dietary preference questions."""
    await register_user(client, "test-daily-q@example.com", "password123", "Parker")
    tokens = await login_user(client, "test-daily-q@example.com", "password123")

    resp = await client.get(
        "/questionnaires/daily",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    questions = {q["id"]: q for q in resp.json()["data"]["questions"]}
    assert "favorite_sports" in questions
    assert "dietary_preference" in questions
    assert questions["favorite_sports"]["type"] == "multiple_choice"
    assert questions["dietary_preference"]["type"] == "single_choice"


async def test_dating_questionnaire_has_boundary_and_values(client):
    """Dating questionnaire includes boundary respect and values ranking questions."""
    await register_user(client, "test-dating-q@example.com", "password123", "Quinn")
    tokens = await login_user(client, "test-dating-q@example.com", "password123")

    resp = await client.get(
        "/questionnaires/dating",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    questions = {q["id"]: q for q in resp.json()["data"]["questions"]}
    assert "boundary_respect" in questions
    assert "long_distance_detail" in questions
    assert "values_ranking" in questions
    assert questions["boundary_respect"]["type"] == "single_choice"
    assert questions["values_ranking"]["type"] == "text"


async def test_submit_response_invalid_option_returns_422(client):
    """Submitting an answer outside the question options returns 422."""
    await register_user(client, "test-invalid-option@example.com", "password123", "Sam")
    tokens = await login_user(client, "test-invalid-option@example.com", "password123")

    resp = await client.post(
        "/questionnaires/basic/responses",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"answers": {"gender": "not_a_gender"}},
    )
    assert resp.status_code == 422
    assert "invalid option for gender" in resp.json()["detail"]


async def test_submit_response_syncs_profile_fields(client):
    """Submitting a basic questionnaire updates the corresponding Profile fields."""
    await register_user(client, "test-profile-sync@example.com", "password123", "Tina")
    tokens = await login_user(client, "test-profile-sync@example.com", "password123")

    answers = {
        "gender": "female",
        "birth_date": "1999-03-20",
        "education_level": "master",
        "major": "Computer Science",
        "interests": ["AI", "hiking"],
        "mbti": "ENFP",
        "location": "Shanghai",
        "bio": "CS master student.",
        "notification_consent": "yes_important",
        "school_verification_preference": "student_card",
    }
    resp = await client.post(
        "/questionnaires/basic/responses",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"answers": answers},
    )
    assert resp.status_code == 200

    profile_resp = await client.get(
        "/profiles/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert profile_resp.status_code == 200
    profile = profile_resp.json()["data"]
    today = date.today()
    expected_age = today.year - 1999 - ((today.month, today.day) < (3, 20))
    assert profile["gender"] == "female"
    assert profile["birth_date"] == "1999-03-20"
    assert profile["age"] == expected_age
    assert profile["education_level"] == "master"
    assert profile["major"] == "Computer Science"
    assert profile["interests"] == ["AI", "hiking"]
    assert profile["mbti"] == "ENFP"
    assert profile["location"] == "Shanghai"
    assert profile["bio"] == "CS master student."
