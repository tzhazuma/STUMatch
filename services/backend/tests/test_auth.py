"""Tests for the authentication endpoints."""
from tests.conftest import register_user


async def test_send_verification_code(client):
    """Sending a verification code stores it in Redis."""
    resp = await client.post(
        "/auth/send-verification-code",
        json={"email": "test-send@example.com", "purpose": "register"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is True
    assert data["provider"] == "mock"
    assert data["target"] == "test-send@example.com"


async def test_register_with_email(client):
    """Registration returns access and refresh tokens."""
    data = await register_user(client, "test-register@example.com", "password123", "Alice")

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test-register@example.com"
    assert data["user"]["nickname"] == "Alice"
    assert data["user"]["is_verified_email"] is True


async def test_register_with_invalid_code(client):
    """Registration fails with an invalid verification code."""
    resp = await client.post(
        "/auth/send-verification-code",
        json={"email": "test-bad-code@example.com", "purpose": "register"},
    )
    assert resp.status_code == 200

    resp = await client.post(
        "/auth/register",
        json={
            "email": "test-bad-code@example.com",
            "code": "000000",
            "password": "password123",
            "nickname": "Bad",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid or expired verification code"


async def test_login(client):
    """Login returns valid tokens for a registered user."""
    await register_user(client, "test-login@example.com", "mypassword", "Bob")

    resp = await client.post(
        "/auth/login",
        json={"email": "test-login@example.com", "password": "mypassword"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert data["user"]["email"] == "test-login@example.com"
    assert data["user"]["nickname"] == "Bob"


async def test_login_invalid_password(client):
    """Login fails with an incorrect password."""
    await register_user(client, "test-login-bad@example.com", "correctpw", "Charlie")

    resp = await client.post(
        "/auth/login",
        json={"email": "test-login-bad@example.com", "password": "wrongpw"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid credentials"
