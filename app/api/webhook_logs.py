"""
Webhook Execution Logs API routes.

This module provides endpoints for retrieving webhook execution logs,
including listing all logs with filters, getting specific logs, and
getting logs by repository.
"""

import json
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.webhook_execution_log import (
    WebhookExecutionLog,
    WebhookExecutionLogResponse,
)
from app.models.repository_config import RepositoryConfig
from app.models.user import User
from app.services.auth_service import get_current_user


router = APIRouter(
    prefix="/api/webhook-logs",
    tags=["Webhook Logs"],
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
    "",
    response_model=List[WebhookExecutionLogResponse],
    summary="List all webhook execution logs",
    responses={
        200: {
            "description": "List of webhook execution logs",
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
        }
    }
)
async def list_webhook_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Optional[str] = Query(
        None, 
        alias="status",
        description="Filter by execution status (success, partial_success, error)"
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter logs executed on or after this date (ISO 8601 format)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter logs executed on or before this date (ISO 8601 format)"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> List[WebhookExecutionLogResponse]:
    """
    List all webhook execution logs with optional filtering and pagination.
    
    Returns logs from all repositories ordered by execution time (newest first).
    Supports filtering by status and date range.
    
    **Query Parameters:**
    - `status`: Filter by execution status (success, partial_success, error)
    - `start_date`: Filter logs executed on or after this date (ISO 8601)
    - `end_date`: Filter logs executed on or before this date (ISO 8601)
    - `skip`: Number of records to skip for pagination (default: 0)
    - `limit`: Maximum number of records to return (default: 100, max: 1000)
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    # Build query with filters
    conditions = []
    
    if status_filter:
        conditions.append(WebhookExecutionLog.status == status_filter)
    
    if start_date:
        conditions.append(WebhookExecutionLog.executed_at >= start_date)
    
    if end_date:
        conditions.append(WebhookExecutionLog.executed_at <= end_date)
    
    # Query logs with filters
    stmt = select(WebhookExecutionLog)
    
    if conditions:
        stmt = stmt.where(and_(*conditions))
    
    stmt = (
        stmt
        .order_by(WebhookExecutionLog.executed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    # Parse and return responses
    return [_parse_log_to_response(log) for log in logs]


@router.get(
    "/{log_id}",
    response_model=WebhookExecutionLogResponse,
    summary="Get a specific webhook execution log",
    responses={
        200: {
            "description": "Webhook execution log details",
            "content": {
                "application/json": {
                    "example": {
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
                }
            }
        },
        404: {
            "description": "Webhook execution log not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Webhook execution log not found"}
                }
            }
        }
    }
)
async def get_webhook_log(
    log_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> WebhookExecutionLogResponse:
    """
    Get a specific webhook execution log by ID.
    
    Returns detailed information about a single webhook execution,
    including all captured data, matched spells, errors, and metadata.
    
    **Authentication required:** Include Bearer token in Authorization header.
    """
    # Query log by ID
    stmt = select(WebhookExecutionLog).where(WebhookExecutionLog.id == log_id)
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()
    
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook execution log not found"
        )
    
    return _parse_log_to_response(log)
