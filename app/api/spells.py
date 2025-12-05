"""
Spell CRUD API endpoints.

This module provides REST API endpoints for managing spells:
- GET /api/spells - List all spells with pagination
- GET /api/spells/{id} - Get a single spell by ID
- POST /api/spells - Create a new spell
- PUT /api/spells/{id} - Update an existing spell
- DELETE /api/spells/{id} - Delete a spell
- POST /api/spells/{id}/apply - Apply a spell to generate a context-aware patch
"""

import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.utils.logging import safe_log_data
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.spell import Spell, SpellCreate, SpellUpdate, SpellResponse
from app.models.spell_application import (
    SpellApplication,
    SpellApplicationRequest,
    SpellApplicationResponse,
    SpellApplicationSummary,
    AdaptationConstraints
)
from app.services.llm_service import get_llm_service
from app.services.patch_generator import PatchGeneratorService

router = APIRouter(prefix="/api/spells", tags=["spells"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[SpellResponse])
async def list_spells(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[SpellResponse]:
    """
    List all spells with pagination.
    
    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        db: Database session dependency
        
    Returns:
        List of spell objects with metadata
        
    Example:
        GET /api/spells?skip=0&limit=10
        Response: [{"id": 1, "title": "Fix undefined variable", ...}, ...]
    """
    result = await db.execute(
        select(Spell)
        .offset(skip)
        .limit(limit)
    )
    spells = result.scalars().all()
    return spells


@router.get("/{spell_id}", response_model=SpellResponse)
async def get_spell(
    spell_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get a single spell by ID.
    
    Args:
        spell_id: ID of the spell to retrieve
        db: Database session dependency
        
    Returns:
        Spell object with all fields including applications list
        
    Raises:
        HTTPException: 404 if spell not found
        
    Example:
        GET /api/spells/1
        Response: {
            "id": 1, 
            "title": "Fix undefined variable",
            "applications": [
                {
                    "id": 1,
                    "spell_id": 1,
                    "repository": "myorg/myrepo",
                    "commit_sha": "abc123",
                    "files_touched": ["app/auth.py"],
                    "created_at": "2025-12-05T10:30:00Z"
                }
            ],
            ...
        }
    """
    result = await db.execute(
        select(Spell)
        .where(Spell.id == spell_id)
        .options(selectinload(Spell.applications))
    )
    spell = result.scalar_one_or_none()
    
    if spell is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found"
        )
    
    # Convert applications to SpellApplicationSummary with JSON parsing
    from app.models.spell_application import SpellApplicationSummary
    applications_summaries = [
        SpellApplicationSummary.from_orm_with_json_parse(app)
        for app in spell.applications
    ]
    
    # Build response with parsed applications
    return {
        "id": spell.id,
        "title": spell.title,
        "description": spell.description,
        "error_type": spell.error_type,
        "error_pattern": spell.error_pattern,
        "solution_code": spell.solution_code,
        "tags": spell.tags,
        "auto_generated": spell.auto_generated,
        "confidence_score": spell.confidence_score,
        "human_reviewed": spell.human_reviewed,
        "created_at": spell.created_at,
        "updated_at": spell.updated_at,
        "applications": [app.model_dump() for app in applications_summaries]
    }


@router.post("", response_model=SpellResponse, status_code=status.HTTP_201_CREATED)
async def create_spell(
    spell: SpellCreate,
    db: AsyncSession = Depends(get_db)
) -> SpellResponse:
    """
    Create a new spell.
    
    Args:
        spell: Spell data to create
        db: Database session dependency
        
    Returns:
        Created spell object with generated ID and timestamps
        
    Example:
        POST /api/spells
        Body: {
            "title": "Fix undefined variable",
            "description": "Solution for undefined variable errors",
            "error_type": "NameError",
            "error_pattern": "name '.*' is not defined",
            "solution_code": "# Define the variable before use",
            "tags": "python,variables"
        }
        Response: {"id": 1, "title": "Fix undefined variable", ...}
    """
    db_spell = Spell(**spell.model_dump())
    db.add(db_spell)
    await db.commit()
    await db.refresh(db_spell)
    return db_spell


@router.put("/{spell_id}", response_model=SpellResponse)
async def update_spell(
    spell_id: int,
    spell: SpellUpdate,
    db: AsyncSession = Depends(get_db)
) -> SpellResponse:
    """
    Update an existing spell.
    
    Args:
        spell_id: ID of the spell to update
        spell: Updated spell data
        db: Database session dependency
        
    Returns:
        Updated spell object
        
    Raises:
        HTTPException: 404 if spell not found
        
    Example:
        PUT /api/spells/1
        Body: {
            "title": "Fix undefined variable (updated)",
            "description": "Updated solution",
            ...
        }
        Response: {"id": 1, "title": "Fix undefined variable (updated)", ...}
    """
    result = await db.execute(
        select(Spell).where(Spell.id == spell_id)
    )
    db_spell = result.scalar_one_or_none()
    
    if db_spell is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found"
        )
    
    # Update fields
    for field, value in spell.model_dump().items():
        setattr(db_spell, field, value)
    
    await db.commit()
    await db.refresh(db_spell)
    return db_spell


@router.delete("/{spell_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spell(
    spell_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a spell by ID.
    
    Args:
        spell_id: ID of the spell to delete
        db: Database session dependency
        
    Returns:
        None (204 No Content)
        
    Raises:
        HTTPException: 404 if spell not found
        
    Example:
        DELETE /api/spells/1
        Response: 204 No Content
    """
    result = await db.execute(
        select(Spell).where(Spell.id == spell_id)
    )
    db_spell = result.scalar_one_or_none()
    
    if db_spell is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found"
        )
    
    await db.delete(db_spell)
    await db.commit()


@router.post("/{spell_id}/apply", response_model=SpellApplicationResponse)
async def apply_spell(
    spell_id: int,
    request: SpellApplicationRequest,
    db: AsyncSession = Depends(get_db)
) -> SpellApplicationResponse:
    """
    Apply a spell to generate a context-aware patch.
    
    Takes a spell's canonical solution (incantation) and adapts it to the
    specific failing code context using an LLM. Returns a git unified diff
    patch that can be applied to the repository.
    
    The system constructs a prompt containing the failing context, spell incantation,
    and adaptation constraints, sends it to the configured LLM provider, validates
    the response, and stores the application record in the database.
    
    Args:
        spell_id: ID of the spell to apply
        request: Spell application request with failing context and constraints
        db: Database session dependency
        
    Returns:
        SpellApplicationResponse with generated patch, files touched, and rationale
        
    HTTP Status Codes:
        - 200 OK: Patch generated successfully
        - 404 Not Found: Spell with the given ID does not exist
        - 422 Unprocessable Entity: Invalid request format, patch validation failed,
          or constraint violations (e.g., too many files modified)
        - 500 Internal Server Error: LLM configuration error (missing or invalid API key)
        - 502 Bad Gateway: LLM API returned an error or invalid response
        - 504 Gateway Timeout: LLM request exceeded the 30-second timeout
        
    Error Response Format:
        All errors return a JSON object with a "detail" field containing
        a human-readable error message:
        {
            "detail": "Error message describing what went wrong"
        }
        
    Example Request:
        POST /api/spells/1/apply
        Content-Type: application/json
        
        {
            "failing_context": {
                "repository": "myorg/myrepo",
                "commit_sha": "abc123def456",
                "language": "python",
                "version": "3.11",
                "failing_test": "test_user_login",
                "stack_trace": "Traceback (most recent call last):\\n  File 'test.py', line 10\\n    assert user is not None\\nAssertionError"
            },
            "adaptation_constraints": {
                "max_files": 3,
                "excluded_patterns": ["package.json", "*.lock"],
                "preserve_style": true
            }
        }
        
    Example Success Response (200 OK):
        {
            "application_id": 1,
            "patch": "diff --git a/app/auth.py b/app/auth.py\\nindex 1234567..abcdefg 100644\\n--- a/app/auth.py\\n+++ b/app/auth.py\\n@@ -10,6 +10,8 @@\\n def login(user):\\n+    if user is None:\\n+        return None\\n     return user.token",
            "files_touched": ["app/auth.py"],
            "rationale": "Added null check before accessing user object to prevent AttributeError",
            "created_at": "2025-12-05T10:30:00Z"
        }
        
    Example Error Response (404 Not Found):
        {
            "detail": "Spell with id 999 not found"
        }
        
    Example Error Response (422 Unprocessable Entity):
        {
            "detail": "Patch validation failed: number of files (5) exceeds maximum allowed (3)"
        }
        
    Example Error Response (504 Gateway Timeout):
        {
            "detail": "Patch generation request timed out"
        }
    """
    # Log incoming request (with redaction)
    logger.info(
        "Received spell application request",
        extra={
            "endpoint": "apply_spell",
            "spell_id": spell_id,
            "repository": request.failing_context.repository,
            "commit_sha": request.failing_context.commit_sha,
            "language": request.failing_context.language,
            "has_stack_trace": bool(request.failing_context.stack_trace),
            "has_failing_test": bool(request.failing_context.failing_test)
        }
    )
    
    # Subtask 5.1: Fetch spell from database by ID
    result = await db.execute(
        select(Spell).where(Spell.id == spell_id)
    )
    spell = result.scalar_one_or_none()
    
    # Return 404 if spell not found
    if spell is None:
        logger.warning(
            "Spell not found",
            extra={
                "endpoint": "apply_spell",
                "spell_id": spell_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found"
        )
    
    # Set default constraints if not provided
    constraints = request.adaptation_constraints or AdaptationConstraints()
    
    logger.debug(
        "Using adaptation constraints",
        extra={
            "endpoint": "apply_spell",
            "spell_id": spell_id,
            "max_files": constraints.max_files,
            "preserve_style": constraints.preserve_style,
            "excluded_patterns": constraints.excluded_patterns
        }
    )
    
    # Subtask 5.3: Initialize PatchGeneratorService with LLM service
    llm_service = get_llm_service()
    patch_generator = PatchGeneratorService(llm_service)
    
    # Call generate_patch with spell, context, and constraints
    try:
        patch_result = await patch_generator.generate_patch(
            spell=spell,
            failing_context=request.failing_context,
            constraints=constraints
        )
    except ValueError as e:
        # Validation errors (patch format, constraints)
        logger.error(
            "Patch validation failed",
            extra={
                "endpoint": "apply_spell",
                "spell_id": spell_id,
                "error_type": "validation_error",
                "error_message": safe_log_data(str(e))
            }
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except TimeoutError as e:
        # LLM timeout
        logger.error(
            "LLM request timeout",
            extra={
                "endpoint": "apply_spell",
                "spell_id": spell_id,
                "error_type": "timeout_error",
                "error_message": safe_log_data(str(e))
            }
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Patch generation request timed out"
        )
    except Exception as e:
        # Check if it's an LLM configuration error
        error_msg = str(e).lower()
        if "api key" in error_msg or "configuration" in error_msg:
            logger.error(
                "LLM configuration error",
                exc_info=True,
                extra={
                    "endpoint": "apply_spell",
                    "spell_id": spell_id,
                    "error_type": "configuration_error",
                    "error_message": safe_log_data(str(e))
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LLM service configuration error"
            )
        else:
            # LLM API error
            logger.error(
                "LLM API error",
                exc_info=True,
                extra={
                    "endpoint": "apply_spell",
                    "spell_id": spell_id,
                    "error_type": "api_error",
                    "error_message": safe_log_data(str(e))
                }
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM API error: {str(e)}"
            )
    
    # Subtask 5.5: Store application record in database
    logger.debug(
        "Storing application record in database",
        extra={
            "endpoint": "apply_spell",
            "spell_id": spell_id,
            "files_touched_count": len(patch_result.files_touched)
        }
    )
    
    # Create SpellApplication record with all fields
    application = SpellApplication(
        spell_id=spell_id,
        repository=request.failing_context.repository,
        commit_sha=request.failing_context.commit_sha,
        language=request.failing_context.language,
        version=request.failing_context.version,
        failing_test=request.failing_context.failing_test,
        stack_trace=request.failing_context.stack_trace,
        patch=patch_result.patch,
        files_touched=json.dumps(patch_result.files_touched),  # Store as JSON string
        rationale=patch_result.rationale
    )
    
    # Add to database and commit
    db.add(application)
    await db.commit()
    await db.refresh(application)
    
    logger.info(
        "Successfully applied spell and created application record",
        extra={
            "endpoint": "apply_spell",
            "spell_id": spell_id,
            "application_id": application.id,
            "repository": request.failing_context.repository,
            "commit_sha": request.failing_context.commit_sha,
            "files_touched": patch_result.files_touched,
            "patch_size_bytes": len(patch_result.patch.encode('utf-8'))
        }
    )
    
    # Subtask 5.7: Return structured response
    # Build SpellApplicationResponse with all required fields
    return SpellApplicationResponse(
        application_id=application.id,
        patch=patch_result.patch,
        files_touched=patch_result.files_touched,
        rationale=patch_result.rationale,
        created_at=application.created_at
    )


@router.get("/{spell_id}/applications", response_model=List[SpellApplicationSummary])
async def list_spell_applications(
    spell_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> List[SpellApplicationSummary]:
    """
    List all applications of a specific spell with pagination.
    
    Returns the history of all times this spell was applied to generate patches,
    ordered by most recent first. Each summary includes the repository, commit SHA,
    files touched, and timestamp. This endpoint is useful for tracking how a spell
    has been used across different repositories and contexts.
    
    Args:
        spell_id: ID of the spell to get applications for
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 50, max: 100)
        db: Database session dependency
        
    Returns:
        List of spell application summaries ordered by created_at descending.
        Returns an empty list if the spell has no applications.
        
    HTTP Status Codes:
        - 200 OK: Applications retrieved successfully (may be empty list)
        
    Query Parameters:
        - skip (optional): Number of records to skip (default: 0)
        - limit (optional): Maximum records to return (default: 50)
        
    Example Request:
        GET /api/spells/1/applications?skip=0&limit=10
        
    Example Success Response (200 OK):
        [
            {
                "id": 5,
                "spell_id": 1,
                "repository": "myorg/myrepo",
                "commit_sha": "abc123def456",
                "files_touched": ["app/auth.py", "app/models/user.py"],
                "created_at": "2025-12-05T10:30:00Z"
            },
            {
                "id": 4,
                "spell_id": 1,
                "repository": "anotherorg/anotherrepo",
                "commit_sha": "def789ghi012",
                "files_touched": ["src/login.py"],
                "created_at": "2025-12-04T15:20:00Z"
            }
        ]
        
    Example Empty Response (200 OK):
        []
    """
    # Query database for applications by spell_id
    result = await db.execute(
        select(SpellApplication)
        .where(SpellApplication.spell_id == spell_id)
        .order_by(SpellApplication.created_at.desc())  # Order by created_at descending
        .offset(skip)
        .limit(limit)
    )
    applications = result.scalars().all()
    
    # Convert to SpellApplicationSummary objects
    # Need to parse files_touched from JSON string to list
    summaries = []
    for app in applications:
        # Parse files_touched from JSON string
        files_touched = json.loads(app.files_touched) if app.files_touched else []
        
        summaries.append(SpellApplicationSummary(
            id=app.id,
            spell_id=app.spell_id,
            repository=app.repository,
            commit_sha=app.commit_sha,
            files_touched=files_touched,
            created_at=app.created_at
        ))
    
    return summaries
