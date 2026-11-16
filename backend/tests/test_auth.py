"""
Unit & Integration Tests for Identity & Authentication (Module M04)
Tests registration, login, token rotation, revocation, lockout, and password management.
"""

import pytest
from httpx import AsyncClient
from app.core.security import hash_password, verify_password
from app.main import app


# ------------------------------------------------------------------------------
# 1. Password Hashing Unit Tests
# ------------------------------------------------------------------------------

def test_argon2_password_hashing():
    """Verify that password hashing uses Argon2id and verifies correctly."""
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)
    assert hashed.startswith("$argon2id$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


# ------------------------------------------------------------------------------
# 2. Registration Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_customer_success(async_client: AsyncClient):
    """Test successful customer registration."""
    payload = {
        "email": "Fatima.Zahra@Example.Com",  # Mixed case to test normalization
        "password": "LuxuryPassword456!",
        "phone": "03001234567",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "fatima.zahra@example.com"
    assert data["status"] == "active"
    assert data["user_type"] == "customer"
    assert "password_hash" not in data
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient):
    """Test that duplicate email registration returns 409 conflict."""
    payload = {
        "email": "ahmad.khan@example.com",
        "password": "Password1234!",
    }
    res1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_validation_failure(async_client: AsyncClient):
    """Test that invalid email or short password fails with 422 validation error."""
    payload = {
        "email": "not-an-email",
        "password": "short",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


# ------------------------------------------------------------------------------
# 3. Authentication & Login Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """Test that valid credentials return access and refresh tokens."""
    # Register user first
    reg = {
        "email": "zainab@example.com",
        "password": "CorrectPassword123!",
    }
    await async_client.post("/api/v1/auth/register", json=reg)

    # Login
    login_payload = {
        "email": "zainab@example.com",
        "password": "CorrectPassword123!",
    }
    response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient):
    """Test that incorrect password fails with 401."""
    reg = {
        "email": "tariq@example.com",
        "password": "CorrectPassword123!",
    }
    await async_client.post("/api/v1/auth/register", json=reg)

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "tariq@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_brute_force_lockout(async_client: AsyncClient):
    """Test that 5 consecutive failed logins trigger temporary account lockout."""
    reg = {
        "email": "lockout_target@example.com",
        "password": "CorrectPassword123!",
    }
    await async_client.post("/api/v1/auth/register", json=reg)

    # Fail 5 times
    for i in range(5):
        res = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "lockout_target@example.com", "password": f"WrongAttempt{i}!"},
        )
        assert res.status_code == 401

    # 6th attempt should be rejected with 423 Locked
    res6 = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "lockout_target@example.com", "password": "CorrectPassword123!"},
    )
    assert res6.status_code == 423
    data = res6.json()
    assert data["error"]["code"] == "ACCOUNT_LOCKED"


# ------------------------------------------------------------------------------
# 4. Current User (/auth/me) Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_user_me(async_client: AsyncClient):
    """Test retrieving authenticated user profile."""
    reg = {"email": "me_user@example.com", "password": "Password123!"}
    await async_client.post("/api/v1/auth/register", json=reg)

    login_res = await async_client.post("/api/v1/auth/login", json=reg)
    token = login_res.json()["access_token"]

    # Request /auth/me with Bearer token
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me_user@example.com"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_current_user_missing_or_invalid_token(async_client: AsyncClient):
    """Test that missing or tampered token returns 401."""
    # Missing token
    res1 = await async_client.get("/api/v1/auth/me")
    assert res1.status_code == 401

    # Tampered token
    res2 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.tampered.token"},
    )
    assert res2.status_code == 401


# ------------------------------------------------------------------------------
# 5. Refresh Token Rotation & Revocation Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation(async_client: AsyncClient):
    """Test that refresh tokens rotate and cannot be reused after rotation."""
    reg = {"email": "rotation_user@example.com", "password": "Password123!"}
    await async_client.post("/api/v1/auth/register", json=reg)

    login_res = await async_client.post("/api/v1/auth/login", json=reg)
    orig_refresh = login_res.json()["refresh_token"]

    # 1. Rotate refresh token
    rotate_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": orig_refresh},
    )
    assert rotate_res.status_code == 200
    new_tokens = rotate_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    new_refresh = new_tokens["refresh_token"]
    assert new_refresh != orig_refresh

    # 2. Reusing old refresh token must be rejected with 401
    reuse_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": orig_refresh},
    )
    assert reuse_res.status_code == 401
    assert reuse_res.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"

    # 3. New refresh token works
    second_rotate = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert second_rotate.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(async_client: AsyncClient):
    """Test that logout revokes the refresh token."""
    reg = {"email": "logout_user@example.com", "password": "Password123!"}
    await async_client.post("/api/v1/auth/register", json=reg)

    login_res = await async_client.post("/api/v1/auth/login", json=reg)
    refresh_token = login_res.json()["refresh_token"]

    # Logout
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Attempting to refresh with logged-out token must fail
    refresh_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 401


# ------------------------------------------------------------------------------
# 6. Password Change & Reset Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_change_password_flow(async_client: AsyncClient):
    """Test changing password while authenticated."""
    reg = {"email": "pw_change@example.com", "password": "OldPassword123!"}
    await async_client.post("/api/v1/auth/register", json=reg)

    login_res = await async_client.post("/api/v1/auth/login", json=reg)
    token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    # Change password
    change_res = await async_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "OldPassword123!",
            "new_password": "NewLuxuryPassword999!",
        },
    )
    assert change_res.status_code == 200

    # Old password login must fail
    old_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pw_change@example.com", "password": "OldPassword123!"},
    )
    assert old_login.status_code == 401

    # New password login must succeed
    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pw_change@example.com", "password": "NewLuxuryPassword999!"},
    )
    assert new_login.status_code == 200

    # Previous refresh token must be revoked
    old_refresh = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert old_refresh.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_flow(async_client: AsyncClient):
    """Test self-service password reset request and confirmation."""
    from app.modules.auth.service import create_password_reset_token
    from app.core.database import get_db

    reg = {"email": "reset_user@example.com", "password": "OldPassword123!"}
    await async_client.post("/api/v1/auth/register", json=reg)

    # 1. Request password reset via API
    req_res = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "reset_user@example.com"},
    )
    assert req_res.status_code == 200

    # 2. Get reset token directly from service for confirmation test
    async for db in app.dependency_overrides[get_db]():
        raw_reset_token = await create_password_reset_token(db, "reset_user@example.com")
        await db.commit()
        break

    assert raw_reset_token is not None

    # 3. Confirm password reset with token
    confirm_res = await async_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": raw_reset_token,
            "new_password": "BrandNewPassword2026!",
        },
    )
    assert confirm_res.status_code == 200

    # 4. Login with newly reset password succeeds
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "reset_user@example.com", "password": "BrandNewPassword2026!"},
    )
    assert login_res.status_code == 200

    # 5. Reusing the reset token fails
    reuse_res = await async_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": raw_reset_token,
            "new_password": "AnotherPassword123!",
        },
    )
    assert reuse_res.status_code == 400
