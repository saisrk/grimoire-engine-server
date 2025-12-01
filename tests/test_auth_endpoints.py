"""
Integration tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient, db_session):
    """Test successful user registration."""
    response = await client.post(
        "/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "securepass123"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Check response structure
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    
    # Check user data
    user_data = data["user"]
    assert user_data["email"] == "newuser@example.com"
    assert user_data["is_active"] is True
    assert "id" in user_data
    assert "created_at" in user_data


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient, test_user):
    """Test registration with duplicate email."""
    response = await client.post(
        "/auth/signup",
        json={
            "email": test_user.email,
            "password": "anotherpass123"
        }
    )
    
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_signup_invalid_email(client: AsyncClient):
    """Test registration with invalid email format."""
    response = await client.post(
        "/auth/signup",
        json={
            "email": "not-an-email",
            "password": "securepass123"
        }
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_short_password(client: AsyncClient):
    """Test registration with password too short."""
    response = await client.post(
        "/auth/signup",
        json={
            "email": "user@example.com",
            "password": "short"
        }
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login."""
    response = await client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    
    # Check user data
    user_data = data["user"]
    assert user_data["email"] == test_user.email
    assert user_data["id"] == test_user.id


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with incorrect password."""
    response = await client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient, test_db):
    """Test login with non-existent email."""
    response = await client.post(
        "/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "somepassword123"
        }
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, test_user, auth_headers):
    """Test getting current user info with valid token."""
    response = await client.get(
        "/auth/me",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id
    assert data["is_active"] is True
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    """Test getting current user info without token."""
    response = await client.get("/auth/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    """Test getting current user info with invalid token."""
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, auth_headers):
    """Test logout with valid token."""
    response = await client.post(
        "/auth/logout",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "logged out" in data["message"].lower()


@pytest.mark.asyncio
async def test_logout_no_token(client: AsyncClient):
    """Test logout without token."""
    response = await client.post("/auth/logout")
    
    assert response.status_code == 401
