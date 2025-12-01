"""
Authentication dependencies for FastAPI routes.

This module provides dependency functions for protecting routes and
extracting authenticated user information from JWT tokens.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token, get_user_by_id


# OAuth2 scheme for extracting Bearer tokens from Authorization header
# tokenUrl is the endpoint where clients can obtain tokens (will be /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependency function to get the current authenticated user.
    
    This function:
    1. Extracts the Bearer token from the Authorization header
    2. Validates and decodes the JWT token
    3. Retrieves the user from the database
    4. Returns the User object for use in route handlers
    
    Args:
        token: JWT token extracted from Authorization header
        db: Database session
        
    Returns:
        User object for the authenticated user
        
    Raises:
        HTTPException: 401 Unauthorized if:
            - Token is missing (handled by oauth2_scheme)
            - Token is invalid or malformed
            - Token is expired
            - User not found in database
            
    Example:
        @router.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    """
    # Define credentials exception for authentication failures
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode and validate the JWT token
        token_data = decode_access_token(token)
        
        # Check if user_id was extracted from token
        if token_data.user_id is None:
            raise credentials_exception
            
    except JWTError:
        # Token is invalid, expired, or malformed
        raise credentials_exception
    
    # Retrieve user from database
    user = await get_user_by_id(db, user_id=token_data.user_id)
    
    if user is None:
        # User not found in database
        raise credentials_exception
    
    return user
