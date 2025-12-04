"""
Authentication service for user registration, login, and token management.
"""

from datetime import datetime, timedelta
from typing import Annotated, Optional
import os

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, UserCreate, TokenData


# OAuth2 scheme for extracting Bearer tokens from Authorization header
# tokenUrl is the endpoint where clients can obtain tokens (will be /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with cost factor 12.
    
    Bcrypt has a maximum password length of 72 bytes. Passwords longer than
    this are truncated to ensure compatibility.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')[:72]
    
    # Generate salt and hash with cost factor 12
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(password_bytes, hashed_bytes)



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing claims to encode in the token (typically user_id)
        expires_delta: Optional custom expiration time. If not provided, uses default 24 hours
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    # Encode and sign the token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        TokenData object containing the user_id from the token
        
    Raises:
        JWTError: If token is invalid, expired, or malformed
    """
    try:
        # Decode and verify the token signature
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract user_id from payload
        user_id: Optional[int] = payload.get("sub")
        
        if user_id is None:
            raise JWTError("Token missing 'sub' claim")
        
        return TokenData(user_id=int(user_id))
    
    except JWTError as e:
        # Re-raise JWT errors for the caller to handle
        raise JWTError(f"Invalid token: {str(e)}")



# User Database Operations

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Retrieve a user by email address.
    
    Args:
        db: Database session
        email: Email address to search for
        
    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Retrieve a user by ID.
    
    Args:
        db: Database session
        user_id: User ID to search for
        
    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """
    Create a new user with hashed password.
    
    Args:
        db: Database session
        user_data: User creation data (email and password)
        
    Returns:
        Created User object
        
    Raises:
        IntegrityError: If email already exists (handled by caller)
    """
    # Hash the password
    hashed_password = hash_password(user_data.password)
    
    # Create user object
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True
    )
    
    # Add to database
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.
    
    Args:
        db: Database session
        email: User's email address
        password: Plain text password to verify
        
    Returns:
        User object if authentication succeeds, None otherwise
    """
    # Get user by email
    user = await get_user_by_email(db, email)
    
    if user is None:
        return None
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


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
