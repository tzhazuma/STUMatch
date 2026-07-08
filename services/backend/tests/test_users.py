"""Tests for the users endpoints."""
from tests.conftest import register_user, login_user


async def test_get_me(client):
    """GET /users/me returns the current authenticated user."""
    await register_user(client, "test-me@example.com", "password123", "Diana")
    tokens = await login_user(client, "test-me@example.com", "password123")

    resp = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == "test-me@example.com"
    assert data["nickname"] == "Diana"
    assert data["role"] == "user"
    assert data["status"] == "active"


async def test_get_me_unauthorized(client):
    """GET /users/me without a token returns 401."""
    resp = await client.get("/users/me")
    assert resp.status_code == 401


async def test_update_me(client):
    """PUT /users/me updates the current user's email."""
    await register_user(client, "test-update-me@example.com", "password123", "Eve")
    tokens = await login_user(client, "test-update-me@example.com", "password123")

    resp = await client.put(
        "/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"email": "test-update-me-new@example.com"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == "test-update-me-new@example.com"

    resp = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.json()["data"]["email"] == "test-update-me-new@example.com"
