"""
Authentication API routes.

This module provides endpoints for user registration, login, logout,
and retrieving current user information.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {
            "description": "Unauthorized - Invalid or missing authentication credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            }
        }
    }
)


@router.post(
    "/signup",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "is_active": True,
                            "created_at": "2024-01-01T00:00:00Z"
                        }
                    }
                }
            }
        },
        409: {
            "description": "Email already registered",
            "content": {
                "application/json": {
                    "example": {"detail": "Email already registered"}
                }
            }
        },
        422: {
            "description": "Validation error - invalid email or password too short",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "password"],
                                "msg": "ensure this value has at least 8 characters",
                                "type": "value_error.any_str.min_length"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def signup(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """
    Register a new user account.
    
    Creates a new user with the provided email and password. The password
    is hashed using bcrypt before storage. Returns an access token and
    user information upon successful registration.
    
    **Requirements:**
    - Email must be a valid email format
    - Password must be at least 8 characters long
    - Email must not already be registered
    
    **Returns:**
    - `access_token`: JWT token for authentication (expires in 24 hours)
    - `token_type`: Always "bearer"
    - `user`: User information (id, email, is_active, created_at)
    """
    try:
        # Create user with hashed password
        user = await create_user(db, user_data)
        
        # Generate access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        # Return token and user information
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump()
        }
        
    except IntegrityError:
        # Email already exists
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )


@router.post(
    "/login",
    response_model=dict,
    summary="Login and get access token",
    responses={
        200: {
            "description": "Successfully authenticated",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "is_active": True,
                            "created_at": "2024-01-01T00:00:00Z"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication failed - incorrect email or password",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password"}
                }
            }
        }
    }
)
async def login(
    credentials: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """
    Authenticate a user and return an access token.
    
    Validates the provided email and password. If authentication succeeds,
    returns a JWT access token and user information.
    
    **Use this token** in the Authorization header for protected endpoints:
    ```
    Authorization: Bearer <access_token>
    ```
    
    **Returns:**
    - `access_token`: JWT token for authentication (expires in 24 hours)
    - `token_type`: Always "bearer"
    - `user`: User information (id, email, is_active, created_at)
    """
    # Authenticate user
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if user is None:
        # Authentication failed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Return token and user information
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump()
    }


@router.post(
    "/logout",
    response_model=dict,
    summary="Logout current user",
    responses={
        200: {
            "description": "Successfully logged out",
            "content": {
                "application/json": {
                    "example": {"message": "Successfully logged out"}
                }
            }
        }
    }
)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """
    Log out the current user (requires authentication).
    
    This endpoint accepts an authenticated request and returns a success
    confirmation. In a stateless JWT system, actual token invalidation
    happens on the client side by removing the token.
    
    **Note:** After logout, remove the token from your client storage.
    The token will remain valid until expiration (24 hours) unless you
    implement server-side token blacklisting.
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    return {
        "message": "Successfully logged out"
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
    responses={
        200: {
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "user@example.com",
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                }
            }
        }
    }
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)]
) -> UserResponse:
    """
    Get current authenticated user information (requires authentication).
    
    This is a protected endpoint that requires a valid Bearer token.
    Returns the user information for the authenticated user.
    
    **Authentication required:** Include Bearer token in Authorization header.
    
    **Use this endpoint to:**
    - Verify your token is valid
    - Get your current user details
    - Check authentication status
    """
    return UserResponse.model_validate(current_user)
