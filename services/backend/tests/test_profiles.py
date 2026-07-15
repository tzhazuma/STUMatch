"""Tests for the profile endpoints."""
from tests.conftest import register_user, login_user


async def test_get_profile_me(client):
    """GET /profiles/me returns the profile of the current user."""
    await register_user(client, "test-profile@example.com", "password123", "Frank")
    tokens = await login_user(client, "test-profile@example.com", "password123")

    resp = await client.get(
        "/profiles/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nickname"] == "Frank"
    assert data["user_id"] == tokens["user"]["id"]
    assert "is_verified_email" in data


async def test_update_profile_me(client):
    """PUT /profiles/me updates profile fields and computes age from birth_date."""
    await register_user(client, "test-update-profile@example.com", "password123", "Grace")
    tokens = await login_user(client, "test-update-profile@example.com", "password123")

    resp = await client.put(
        "/profiles/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "gender": "female",
            "birth_date": "1998-06-15",
            "education_level": "master",
            "major": "Computer Science",
            "interests": ["AI", "hiking", "music"],
            "location": "Shanghai",
            "bio": "Test bio",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["gender"] == "female"
    assert data["education_level"] == "master"
    assert data["major"] == "Computer Science"
    assert data["interests"] == ["AI", "hiking", "music"]
    assert data["location"] == "Shanghai"
    assert data["bio"] == "Test bio"
    assert data["age"] is not None


async def test_update_profile_nickname_propagates(client):
    """Updating the nickname in the profile also updates the user nickname."""
    await register_user(client, "test-nickname@example.com", "password123", "Hank")
    tokens = await login_user(client, "test-nickname@example.com", "password123")

    resp = await client.put(
        "/profiles/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"nickname": "HankUpdated"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["nickname"] == "HankUpdated"

    user_resp = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert user_resp.json()["data"]["nickname"] == "HankUpdated"
