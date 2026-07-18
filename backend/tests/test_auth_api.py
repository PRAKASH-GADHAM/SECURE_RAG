"""Tests for authentication API endpoints.

Covers registration, login, token refresh, and profile retrieval.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPass123!",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        assert data["role"] == "user"
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Test registration with duplicate email."""
        # Register first user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "user1",
                "password": "TestPass123!",
            },
        )
        # Try to register with same email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "user2",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 409

    async def test_register_duplicate_username(self, client: AsyncClient):
        """Test registration with duplicate username."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user1@example.com",
                "username": "testuser",
                "password": "TestPass123!",
            },
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2@example.com",
                "username": "testuser",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 409

    async def test_login_success(self, client: AsyncClient):
        """Test successful login."""
        # Register user first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPass123!",
            },
        )
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPass123!",
            },
        )
        assert response.status_code == 401

    async def test_get_current_user(self, client: AsyncClient):
        """Test getting current user profile."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPass123!",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        token = login_response.json()["access_token"]

        # Get profile
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting profile without token."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_refresh_token(self, client: AsyncClient):
        """Test token refresh."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPass123!",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
