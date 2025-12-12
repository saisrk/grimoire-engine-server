"""
Error handling utilities for repository-based access control.

This module provides standardized error handling for access control scenarios,
database constraints, and validation failures.
"""

import logging
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine.base import Engine

logger = logging.getLogger(__name__)


class AccessControlError(Exception):
    """Base exception for access control errors."""
    pass


class RepositoryNotFoundError(AccessControlError):
    """Raised when a repository is not found or not accessible."""
    pass


class SpellNotFoundError(AccessControlError):
    """Raised when a spell is not found or not accessible."""
    pass


class RepositoryAccessDeniedError(AccessControlError):
    """Raised when user doesn't have access to a repository."""
    pass


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def raise_repository_not_found(repository_id: Optional[int] = None) -> None:
    """
    Raise a standardized 404 error for repository not found.
    
    Args:
        repository_id: Optional repository ID for logging
        
    Raises:
        HTTPException: 404 Not Found with standardized message
        
    Validates: Requirements 2.4, 4.5 - Clear error messages for access control
    """
    if repository_id:
        logger.warning(f"Repository access denied or not found: {repository_id}")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Repository not found"
    )


def raise_spell_not_found(spell_id: Optional[int] = None) -> None:
    """
    Raise a standardized 404 error for spell not found.
    
    Args:
        spell_id: Optional spell ID for logging
        
    Raises:
        HTTPException: 404 Not Found with standardized message
        
    Validates: Requirements 2.4 - Clear error messages for access control
    """
    if spell_id:
        logger.warning(f"Spell access denied or not found: {spell_id}")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Spell not found"
    )


def raise_repository_access_denied(repository_id: int, user_id: int) -> None:
    """
    Raise a standardized 403 error for repository access denied.
    
    Args:
        repository_id: ID of the repository
        user_id: ID of the user
        
    Raises:
        HTTPException: 403 Forbidden with clear message
        
    Validates: Requirements 2.4 - Clear error messages for unauthorized access
    """
    logger.warning(
        f"Repository access denied: user {user_id} attempted to access repository {repository_id}"
    )
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: You do not have permission to access this repository"
    )


def raise_spell_access_denied(spell_id: int, user_id: int) -> None:
    """
    Raise a standardized 403 error for spell access denied.
    
    Args:
        spell_id: ID of the spell
        user_id: ID of the user
        
    Raises:
        HTTPException: 403 Forbidden with clear message
        
    Validates: Requirements 2.4 - Clear error messages for unauthorized access
    """
    logger.warning(
        f"Spell access denied: user {user_id} attempted to access spell {spell_id}"
    )
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: You do not have permission to access this spell"
    )


def raise_validation_error(message: str, field: Optional[str] = None) -> None:
    """
    Raise a standardized 422 error for validation failures.
    
    Args:
        message: Error message describing the validation failure
        field: Optional field name that failed validation
        
    Raises:
        HTTPException: 422 Unprocessable Entity with clear message
        
    Validates: Requirements 9.3 - Clear error messages for validation failures
    """
    if field:
        logger.warning(f"Validation error in field '{field}': {message}")
        detail = f"Validation error in '{field}': {message}"
    else:
        logger.warning(f"Validation error: {message}")
        detail = f"Validation error: {message}"
    
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail
    )


def raise_repository_validation_error(repository_id: int, message: str) -> None:
    """
    Raise a standardized 422 error for repository validation failures.
    
    Args:
        repository_id: ID of the repository that failed validation
        message: Error message describing the validation failure
        
    Raises:
        HTTPException: 422 Unprocessable Entity with repository context
        
    Validates: Requirements 9.3 - Clear error messages for repository validation
    """
    logger.warning(f"Repository validation error for repository {repository_id}: {message}")
    
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Repository validation failed: {message}"
    )


def handle_database_constraint_error(error: IntegrityError, operation: str) -> None:
    """
    Handle database constraint violations with appropriate HTTP responses.
    
    Args:
        error: The IntegrityError from SQLAlchemy
        operation: Description of the operation that failed
        
    Raises:
        HTTPException: Appropriate status code based on constraint type
        
    Validates: Requirements 10.5 - Appropriate error responses for constraint failures
    """
    error_msg = str(error.orig) if hasattr(error, 'orig') else str(error)
    
    logger.error(f"Database constraint violation during {operation}: {error_msg}")
    
    # Check for specific constraint types
    if "foreign key constraint" in error_msg.lower():
        # Foreign key constraint violation
        if "repository_id" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid repository: The specified repository does not exist"
            )
        elif "user_id" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid user: The specified user does not exist"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid reference: The specified resource does not exist"
            )
    
    elif "unique constraint" in error_msg.lower():
        # Unique constraint violation
        if "repo_name" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Repository already configured"
            )
        elif "email" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource already exists"
            )
    
    elif "not null constraint" in error_msg.lower():
        # Not null constraint violation
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field"
        )
    
    else:
        # Generic constraint violation
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Data integrity constraint violation"
        )


def log_constraint_violation_attempt(
    operation: str,
    user_id: Optional[int] = None,
    repository_id: Optional[int] = None,
    spell_id: Optional[int] = None,
    error_details: Optional[str] = None
) -> None:
    """
    Log constraint violation attempts for security monitoring.
    
    Args:
        operation: Description of the operation that failed
        user_id: Optional user ID involved in the operation
        repository_id: Optional repository ID involved
        spell_id: Optional spell ID involved
        error_details: Optional additional error details
        
    Validates: Requirements 10.5 - Logging for constraint violation attempts
    """
    log_data = {
        "event": "constraint_violation_attempt",
        "operation": operation,
        "user_id": user_id,
        "repository_id": repository_id,
        "spell_id": spell_id,
        "error_details": error_details
    }
    
    # Filter out None values
    log_data = {k: v for k, v in log_data.items() if v is not None}
    
    logger.warning("Database constraint violation attempt", extra=log_data)


def validate_repository_exists_and_accessible(
    repository_id: int,
    user_id: int,
    repository_exists: bool,
    user_has_access: bool
) -> None:
    """
    Validate repository existence and user access with appropriate error responses.
    
    Args:
        repository_id: ID of the repository
        user_id: ID of the user
        repository_exists: Whether the repository exists
        user_has_access: Whether the user has access to the repository
        
    Raises:
        HTTPException: 404 if repository not found, 403 if access denied
        
    Validates: Requirements 2.4, 9.3 - Proper error responses for access control
    """
    if not repository_exists:
        raise_repository_not_found(repository_id)
    
    if not user_has_access:
        raise_repository_access_denied(repository_id, user_id)


def validate_spell_exists_and_accessible(
    spell_id: int,
    user_id: int,
    spell_exists: bool,
    user_has_access: bool
) -> None:
    """
    Validate spell existence and user access with appropriate error responses.
    
    Args:
        spell_id: ID of the spell
        user_id: ID of the user
        spell_exists: Whether the spell exists
        user_has_access: Whether the user has access to the spell
        
    Raises:
        HTTPException: 404 if spell not found, 403 if access denied
        
    Validates: Requirements 2.4 - Proper error responses for access control
    """
    if not spell_exists:
        raise_spell_not_found(spell_id)
    
    if not user_has_access:
        raise_spell_access_denied(spell_id, user_id)