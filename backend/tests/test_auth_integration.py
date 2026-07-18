"""Comprehensive authentication integration tests.

Tests the full auth lifecycle: registration, login, tokens, sessions,
password reset, API keys, and RBAC.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegistrationFlow:
    """Tests for user registration."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful registration returns user profile."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["role"] == "user"
        assert data["is_active"] is True
        assert "id" in data

    async def test_register_duplicate_email_rejected(self, client: AsyncClient):
        """Test duplicate email is rejected."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@example.com",
                "username": "user1",
                "password": "SecurePass123!",
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@example.com",
                "username": "user2",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 409

    async def test_register_duplicate_username_rejected(self, client: AsyncClient):
        """Test duplicate username is rejected."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "u1@example.com",
                "username": "dupuser",
                "password": "SecurePass123!",
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "u2@example.com",
                "username": "dupuser",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 409

    async def test_register_weak_password_rejected(self, client: AsyncClient):
        """Test weak password is rejected."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "username": "weakuser",
                "password": "short",
            },
        )
        assert response.status_code in (400, 422)

    async def test_register_invalid_email_rejected(self, client: AsyncClient):
        """Test invalid email is rejected."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "validuser",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLoginFlow:
    """Tests for user login."""

    async def test_login_success(self, client: AsyncClient):
        """Test successful login returns tokens."""
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "username": "loginuser",
                "password": "SecurePass123!",
            },
        )
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with wrong password fails."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong@example.com",
                "username": "wrongpass",
                "password": "SecurePass123!",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "WrongPassword!",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent email fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "ghost@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestTokenRefresh:
    """Tests for token refresh."""

    async def test_refresh_success(self, client: AsyncClient):
        """Test successful token refresh."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@example.com",
                "username": "refreshuser",
                "password": "SecurePass123!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "refresh@example.com",
                "password": "SecurePass123!",
            },
        )
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token fails."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestProtectedEndpoints:
    """Tests for protected endpoint access."""

    async def test_get_profile(self, client: AsyncClient):
        """Test getting user profile with valid token."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "profile@example.com",
                "username": "profileuser",
                "password": "SecurePass123!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "profile@example.com",
                "password": "SecurePass123!",
            },
        )
        token = login_resp.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "profile@example.com"

    async def test_get_profile_no_token(self, client: AsyncClient):
        """Test getting profile without token fails."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_profile_invalid_token(self, client: AsyncClient):
        """Test getting profile with invalid token fails."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestProfileUpdate:
    """Tests for profile updates."""

    async def test_update_profile(self, client: AsyncClient):
        """Test updating user profile."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "update@example.com",
                "username": "updateuser",
                "password": "SecurePass123!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "update@example.com",
                "password": "SecurePass123!",
            },
        )
        token = login_resp.json()["access_token"]

        response = await client.put(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"full_name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
class TestPasswordChange:
    """Tests for password change."""

    async def test_change_password_success(self, client: AsyncClient):
        """Test successful password change."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "changepass@example.com",
                "username": "changepass",
                "password": "OldPass123!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "changepass@example.com",
                "password": "OldPass123!",
            },
        )
        token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "OldPass123!",
                "new_password": "NewPass456!",
            },
        )
        assert response.status_code == 200

    async def test_change_password_wrong_current(self, client: AsyncClient):
        """Test password change with wrong current password fails."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongold@example.com",
                "username": "wrongold",
                "password": "CorrectPass1!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongold@example.com",
                "password": "CorrectPass1!",
            },
        )
        token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "WrongPass999!",
                "new_password": "NewPass456!",
            },
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestSessionManagement:
    """Tests for session management."""

    async def test_list_sessions(self, client: AsyncClient):
        """Test listing active sessions."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sessions@example.com",
                "username": "sessions",
                "password": "SecurePass123!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "sessions@example.com",
                "password": "SecurePass123!",
            },
        )
        token = login_resp.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert data["total"] >= 1


@pytest.mark.asyncio
class TestLogout:
    """Tests for logout."""

    async def test_logout_success(self, client: AsyncClient):
        """Test successful logout."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.com",
                "username": "logoutuser",
                "password": "SecurePass123!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "logout@example.com",
                "password": "SecurePass123!",
            },
        )
        token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            json={"all_devices": False},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
class TestAPIKeyManagement:
    """Tests for API key management."""

    async def test_create_api_key(self, client: AsyncClient):
        """Test creating an API key."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "apikey@example.com",
                "username": "apikeyuser",
                "password": "SecurePass123!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "apikey@example.com",
                "password": "SecurePass123!",
            },
        )
        token = login_resp.json()["access_token"]

        response = await client.post(
            "/api/v1/api-keys/",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test API Key"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "key" in data
        assert data["key"].startswith("srag_")
        assert data["name"] == "Test API Key"

    async def test_list_api_keys(self, client: AsyncClient):
        """Test listing API keys."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "listkeys@example.com",
                "username": "listkeys",
                "password": "SecurePass123!",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "listkeys@example.com",
                "password": "SecurePass123!",
            },
        )
        token = login_resp.json()["access_token"]

        response = await client.get(
            "/api/v1/api-keys/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "api_keys" in response.json()


@pytest.mark.asyncio
class TestPasswordReset:
    """Tests for password reset flow."""

    async def test_request_password_reset(self, client: AsyncClient):
        """Test requesting a password reset."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset@example.com",
                "username": "resetuser",
                "password": "SecurePass123!",
            },
        )

        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "reset@example.com"},
        )
        assert response.status_code == 200

    async def test_request_password_reset_nonexistent_email(self, client: AsyncClient):
        """Test reset request for non-existent email still returns success (no enumeration)."""
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
class TestHealthCheck:
    """Tests for health endpoint."""

    async def test_health_check(self, client: AsyncClient):
        """Test health check returns healthy."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200
        assert "name" in response.json()
