"""
Repository Configuration API routes.

This module provides endpoints for managing repository configurations,
including creating, listing, updating, and deleting repository configs.
"""

import json
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.repository_config import (
    RepositoryConfig,
    RepositoryConfigCreate,
    RepositoryConfigUpdate,
    RepositoryConfigResponse,
)
from app.models.webhook_execution_log import (
    WebhookExecutionLog,
    WebhookExecutionLogResponse,
)
from app.models.user import User
from app.services.auth_service import get_current_user


router = APIRouter(
    prefix="/api/repo-configs",
    tags=["Repository Configuration"],
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
    "",
    response_model=RepositoryConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new repository configuration",
    responses={
        201: {
            "description": "Repository configuration successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "repo_name": "octocat/Hello-World",
                        "webhook_url": "https://grimoire.example.com/webhook/github",
                        "enabled": True,
                        "created_at": "2025-12-05T10:00:00Z",
                        "updated_at": None,
                        "webhook_count": 0,
                        "last_webhook_at": None
                    }
                }
            }
        },
        409: {
            "description": "Repository already configured",
            "content": {
                "application/json": {
                    "example": {"detail": "Repository already configured"}
                }
            }
        },
        422: {
            "description": "Validation error - invalid repository name format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "repo_name"],
                                "msg": "string does not match regex pattern",
                                "type": "value_error.str.regex"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_repository_config(
    config_data: RepositoryConfigCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> RepositoryConfigResponse:
    """
    Create a new repository configuration.
    
    Registers a GitHub repository for webhook integration. The repository name
    must follow the format "owner/repo" (e.g., "octocat/Hello-World").
    
    **Requirements:**
    - Repository name must match format: owner/repo
    - Webhook URL must be a valid URL
    - Repository name must be unique (not already configured)
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    try:
        # Create new repository config
        repo_config = RepositoryConfig(
            repo_name=config_data.repo_name,
            webhook_url=config_data.webhook_url,
            enabled=config_data.enabled
        )
        
        db.add(repo_config)
        await db.commit()
        await db.refresh(repo_config)
        
        # Build response with computed fields
        response = RepositoryConfigResponse.model_validate(repo_config)
        response.webhook_count = 0
        response.last_webhook_at = None
        
        return response
        
    except IntegrityError:
        # Repository name already exists
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository already configured"
        )


@router.get(
    "",
    response_model=List[RepositoryConfigResponse],
    summary="List all repository configurations",
    responses={
        200: {
            "description": "List of repository configurations",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "repo_name": "octocat/Hello-World",
                            "webhook_url": "https://grimoire.example.com/webhook/github",
                            "enabled": True,
                            "created_at": "2025-12-05T10:00:00Z",
                            "updated_at": "2025-12-05T12:00:00Z",
                            "webhook_count": 15,
                            "last_webhook_at": "2025-12-05T11:45:00Z"
                        }
                    ]
                }
            }
        }
    }
)
async def list_repository_configs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> List[RepositoryConfigResponse]:
    """
    List all repository configurations with pagination.
    
    Returns all configured repositories ordered by creation date (newest first).
    Includes computed fields for webhook count and last webhook execution time.
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    # Query repository configs ordered by created_at descending
    stmt = (
        select(RepositoryConfig)
        .order_by(RepositoryConfig.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    repo_configs = result.scalars().all()
    
    # Build responses with computed fields
    responses = []
    for config in repo_configs:
        # Count webhooks for this repo
        count_stmt = (
            select(func.count(WebhookExecutionLog.id))
            .where(WebhookExecutionLog.repo_config_id == config.id)
        )
        count_result = await db.execute(count_stmt)
        webhook_count = count_result.scalar() or 0
        
        # Get last webhook execution time
        last_webhook_stmt = (
            select(func.max(WebhookExecutionLog.executed_at))
            .where(WebhookExecutionLog.repo_config_id == config.id)
        )
        last_webhook_result = await db.execute(last_webhook_stmt)
        last_webhook_at = last_webhook_result.scalar()
        
        # Build response
        response = RepositoryConfigResponse.model_validate(config)
        response.webhook_count = webhook_count
        response.last_webhook_at = last_webhook_at
        
        responses.append(response)
    
    return responses


@router.get(
    "/{config_id}",
    response_model=RepositoryConfigResponse,
    summary="Get a specific repository configuration",
    responses={
        200: {
            "description": "Repository configuration details",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "repo_name": "octocat/Hello-World",
                        "webhook_url": "https://grimoire.example.com/webhook/github",
                        "enabled": True,
                        "created_at": "2025-12-05T10:00:00Z",
                        "updated_at": "2025-12-05T12:00:00Z",
                        "webhook_count": 15,
                        "last_webhook_at": "2025-12-05T11:45:00Z"
                    }
                }
            }
        },
        404: {
            "description": "Repository configuration not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Repository configuration not found"}
                }
            }
        }
    }
)
async def get_repository_config(
    config_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> RepositoryConfigResponse:
    """
    Get a specific repository configuration by ID.
    
    Returns detailed information about a repository configuration,
    including webhook count and last execution time.
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    # Query repository config by ID
    stmt = select(RepositoryConfig).where(RepositoryConfig.id == config_id)
    result = await db.execute(stmt)
    repo_config = result.scalar_one_or_none()
    
    if repo_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository configuration not found"
        )
    
    # Count webhooks for this repo
    count_stmt = (
        select(func.count(WebhookExecutionLog.id))
        .where(WebhookExecutionLog.repo_config_id == repo_config.id)
    )
    count_result = await db.execute(count_stmt)
    webhook_count = count_result.scalar() or 0
    
    # Get last webhook execution time
    last_webhook_stmt = (
        select(func.max(WebhookExecutionLog.executed_at))
        .where(WebhookExecutionLog.repo_config_id == repo_config.id)
    )
    last_webhook_result = await db.execute(last_webhook_stmt)
    last_webhook_at = last_webhook_result.scalar()
    
    # Build response
    response = RepositoryConfigResponse.model_validate(repo_config)
    response.webhook_count = webhook_count
    response.last_webhook_at = last_webhook_at
    
    return response


@router.put(
    "/{config_id}",
    response_model=RepositoryConfigResponse,
    summary="Update a repository configuration",
    responses={
        200: {
            "description": "Repository configuration successfully updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "repo_name": "octocat/Hello-World",
                        "webhook_url": "https://grimoire.example.com/webhook/github",
                        "enabled": False,
                        "created_at": "2025-12-05T10:00:00Z",
                        "updated_at": "2025-12-05T14:00:00Z",
                        "webhook_count": 15,
                        "last_webhook_at": "2025-12-05T11:45:00Z"
                    }
                }
            }
        },
        404: {
            "description": "Repository configuration not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Repository configuration not found"}
                }
            }
        }
    }
)
async def update_repository_config(
    config_id: int,
    update_data: RepositoryConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> RepositoryConfigResponse:
    """
    Update a repository configuration.
    
    Allows updating the webhook URL and enabled status. The repository name
    cannot be changed. The updated_at timestamp is automatically updated.
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    # Query repository config by ID
    stmt = select(RepositoryConfig).where(RepositoryConfig.id == config_id)
    result = await db.execute(stmt)
    repo_config = result.scalar_one_or_none()
    
    if repo_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository configuration not found"
        )
    
    # Update fields if provided
    if update_data.webhook_url is not None:
        repo_config.webhook_url = update_data.webhook_url
    if update_data.enabled is not None:
        repo_config.enabled = update_data.enabled
    
    await db.commit()
    await db.refresh(repo_config)
    
    # Count webhooks for this repo
    count_stmt = (
        select(func.count(WebhookExecutionLog.id))
        .where(WebhookExecutionLog.repo_config_id == repo_config.id)
    )
    count_result = await db.execute(count_stmt)
    webhook_count = count_result.scalar() or 0
    
    # Get last webhook execution time
    last_webhook_stmt = (
        select(func.max(WebhookExecutionLog.executed_at))
        .where(WebhookExecutionLog.repo_config_id == repo_config.id)
    )
    last_webhook_result = await db.execute(last_webhook_stmt)
    last_webhook_at = last_webhook_result.scalar()
    
    # Build response
    response = RepositoryConfigResponse.model_validate(repo_config)
    response.webhook_count = webhook_count
    response.last_webhook_at = last_webhook_at
    
    return response


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a repository configuration",
    responses={
        200: {
            "description": "Repository configuration successfully deleted",
            "content": {
                "application/json": {
                    "example": {"message": "Repository configuration deleted successfully"}
                }
            }
        },
        404: {
            "description": "Repository configuration not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Repository configuration not found"}
                }
            }
        }
    }
)
async def delete_repository_config(
    config_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """
    Delete a repository configuration.
    
    Removes the repository configuration and all associated webhook execution logs
    (cascade delete). This operation cannot be undone.
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    # Query repository config by ID
    stmt = select(RepositoryConfig).where(RepositoryConfig.id == config_id)
    result = await db.execute(stmt)
    repo_config = result.scalar_one_or_none()
    
    if repo_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository configuration not found"
        )
    
    # Delete the repository config (cascade will delete associated logs)
    await db.delete(repo_config)
    await db.commit()
    
    return {"message": "Repository configuration deleted successfully"}



def _parse_log_to_response(log: WebhookExecutionLog) -> WebhookExecutionLogResponse:
    """
    Parse a WebhookExecutionLog database model to a response schema.
    
    Handles JSON parsing for matched_spell_ids and pr_processing_result,
    and computes derived fields.
    
    Args:
        log: WebhookExecutionLog database model
        
    Returns:
        WebhookExecutionLogResponse with parsed JSON and computed fields
    """
    # Parse JSON fields
    matched_spell_ids = []
    if log.matched_spell_ids:
        try:
            matched_spell_ids = json.loads(log.matched_spell_ids)
        except (json.JSONDecodeError, TypeError):
            matched_spell_ids = []
    
    pr_processing_result = None
    if log.pr_processing_result:
        try:
            pr_processing_result = json.loads(log.pr_processing_result)
        except (json.JSONDecodeError, TypeError):
            pr_processing_result = None
    
    # Compute derived fields
    files_changed_count = 0
    spell_match_attempted = False
    spell_generation_attempted = False
    
    if pr_processing_result:
        # Count files changed
        files_changed = pr_processing_result.get("files_changed", [])
        if isinstance(files_changed, list):
            files_changed_count = len(files_changed)
        
        # Check if spell matching was attempted
        spell_match_attempted = pr_processing_result.get("spell_match_attempted", False)
        
        # Check if spell generation was attempted
        spell_generation_attempted = pr_processing_result.get("spell_generation_attempted", False)
    
    # Build response
    return WebhookExecutionLogResponse(
        id=log.id,
        repo_config_id=log.repo_config_id,
        repo_name=log.repo_name,
        pr_number=log.pr_number,
        event_type=log.event_type,
        action=log.action,
        status=log.status,
        matched_spell_ids=matched_spell_ids,
        auto_generated_spell_id=log.auto_generated_spell_id,
        error_message=log.error_message,
        pr_processing_result=pr_processing_result,
        execution_duration_ms=log.execution_duration_ms,
        executed_at=log.executed_at,
        files_changed_count=files_changed_count,
        spell_match_attempted=spell_match_attempted,
        spell_generation_attempted=spell_generation_attempted,
    )


@router.get(
    "/{config_id}/logs",
    response_model=List[WebhookExecutionLogResponse],
    summary="Get webhook logs for a specific repository",
    responses={
        200: {
            "description": "List of webhook execution logs for the repository",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 42,
                            "repo_config_id": 1,
                            "repo_name": "octocat/Hello-World",
                            "pr_number": 123,
                            "event_type": "pull_request",
                            "action": "opened",
                            "status": "success",
                            "matched_spell_ids": [5, 12, 3],
                            "auto_generated_spell_id": None,
                            "error_message": None,
                            "pr_processing_result": {
                                "repo": "octocat/Hello-World",
                                "pr_number": 123,
                                "files_changed": ["app/main.py", "tests/test_main.py"],
                                "status": "success"
                            },
                            "execution_duration_ms": 1850,
                            "executed_at": "2025-12-05T11:45:23Z",
                            "files_changed_count": 2,
                            "spell_match_attempted": True,
                            "spell_generation_attempted": False
                        }
                    ]
                }
            }
        },
        404: {
            "description": "Repository configuration not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Repository configuration not found"}
                }
            }
        }
    }
)
async def get_repository_logs(
    config_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> List[WebhookExecutionLogResponse]:
    """
    Get all webhook execution logs for a specific repository.
    
    Returns logs for the specified repository ordered by execution time (newest first).
    Returns an empty list if the repository has no logs.
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    # Verify repository config exists
    config_stmt = select(RepositoryConfig).where(RepositoryConfig.id == config_id)
    config_result = await db.execute(config_stmt)
    repo_config = config_result.scalar_one_or_none()
    
    if repo_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository configuration not found"
        )
    
    # Query logs for this repository
    logs_stmt = (
        select(WebhookExecutionLog)
        .where(WebhookExecutionLog.repo_config_id == config_id)
        .order_by(WebhookExecutionLog.executed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs_result = await db.execute(logs_stmt)
    logs = logs_result.scalars().all()
    
    # Parse and return responses
    return [_parse_log_to_response(log) for log in logs]
