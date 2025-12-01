"""
Tests for authentication dependencies.

These tests verify that the get_current_user dependency correctly
extracts and validates JWT tokens and retrieves user information.
"""

import pytest
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.user import User, UserCreate
from app.services.auth_service import create_user, create_access_token


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token(db_session: AsyncSession):
    """
    Test that get_current_user returns the correct user with a valid token.
    """
    # Create a test user
    user_data = UserCreate(email="test@example.com", password="testpassword123")
    user = await create_user(db_session, user_data)
    
    # Create a valid token for the user
    token = create_access_token(data={"sub": str(user.id)})
    
    # Call get_current_user with the token
    current_user = await get_current_user(token=token, db=db_session)
    
    # Verify the correct user is returned
    assert current_user.id == user.id
    assert current_user.email == user.email
    assert current_user.is_active is True


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token(db_session: AsyncSession):
    """
    Test that get_current_user raises HTTPException with an invalid token.
    """
    # Use an invalid token
    invalid_token = "invalid.token.here"
    
    # Verify that HTTPException is raised
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=invalid_token, db=db_session)
    
    # Verify the exception details
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_with_expired_token(db_session: AsyncSession):
    """
    Test that get_current_user raises HTTPException with an expired token.
    """
    # Create a test user
    user_data = UserCreate(email="expired@example.com", password="testpassword123")
    user = await create_user(db_session, user_data)
    
    # Create an expired token (negative expiration time)
    expired_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(seconds=-1)
    )
    
    # Verify that HTTPException is raised
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=expired_token, db=db_session)
    
    # Verify the exception details
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_with_nonexistent_user(db_session: AsyncSession):
    """
    Test that get_current_user raises HTTPException when user doesn't exist.
    """
    # Create a token for a non-existent user ID
    token = create_access_token(data={"sub": "99999"})
    
    # Verify that HTTPException is raised
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db_session)
    
    # Verify the exception details
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_with_missing_sub_claim(db_session: AsyncSession):
    """
    Test that get_current_user raises HTTPException when token lacks 'sub' claim.
    """
    # Create a token without the 'sub' claim
    token = create_access_token(data={"user": "123"})  # Wrong claim name
    
    # Verify that HTTPException is raised
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db_session)
    
    # Verify the exception details
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail
