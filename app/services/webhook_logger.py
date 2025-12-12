"""
Webhook logging service for creating execution logs.

This service encapsulates the logic for creating webhook execution logs,
including finding associated repository configurations, determining execution
status, and handling JSON serialization for complex fields.
"""

import json
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.utils.error_handlers import (
    handle_database_constraint_error,
    log_constraint_violation_attempt
)

from app.models.webhook_execution_log import WebhookExecutionLog
from app.models.repository_config import RepositoryConfig

logger = logging.getLogger(__name__)


async def _find_repo_config_id(
    db: AsyncSession,
    repo_name: str
) -> Optional[int]:
    """
    Find repository configuration ID by repository name.
    
    Looks up the repository configuration in the database to link
    the execution log to the configured repository if it exists.
    
    Args:
        db: Database session
        repo_name: Repository full name (e.g., "octocat/Hello-World")
        
    Returns:
        Repository configuration ID if found, None otherwise
        
    Example:
        repo_config_id = await _find_repo_config_id(db, "octocat/Hello-World")
        if repo_config_id:
            print(f"Found config: {repo_config_id}")
    """
    try:
        # Query for repository config by name
        result = await db.execute(
            select(RepositoryConfig).where(RepositoryConfig.repo_name == repo_name)
        )
        repo_config = result.scalar_one_or_none()
        
        if repo_config:
            logger.debug(f"Found repository config ID {repo_config.id} for {repo_name}")
            return repo_config.id
        else:
            logger.debug(f"No repository config found for {repo_name}")
            return None
            
    except Exception as e:
        # Log error but don't fail - we can create log without repo_config_id
        logger.warning(
            f"Error finding repository config for {repo_name}: {str(e)}",
            exc_info=True
        )
        return None


def _determine_status(
    pr_processing_result: Optional[Dict[str, Any]],
    matched_spells: List[int],
    error_message: Optional[str]
) -> str:
    """
    Determine execution status from processing results.
    
    Analyzes the PR processing result, matched spells, and error message
    to determine the overall execution status.
    
    Status determination logic:
    - "error": If error_message is present or PR processing failed
    - "partial_success": If processing succeeded but no spells matched
    - "success": If processing succeeded and spells were matched
    
    Args:
        pr_processing_result: Result from PR processor (may be None)
        matched_spells: List of matched spell IDs (may be empty)
        error_message: Error message if processing failed (may be None)
        
    Returns:
        Status string: "success", "partial_success", or "error"
        
    Example:
        # Success case
        status = _determine_status(
            {"status": "success", "files_changed": ["app/main.py"]},
            [1, 2, 3],
            None
        )
        assert status == "success"
        
        # Partial success case (no spells matched)
        status = _determine_status(
            {"status": "success", "files_changed": ["app/main.py"]},
            [],
            None
        )
        assert status == "partial_success"
        
        # Error case
        status = _determine_status(
            {"status": "error", "error": "Failed to fetch PR"},
            [],
            "Failed to fetch PR"
        )
        assert status == "error"
    """
    # If there's an explicit error message, status is error
    if error_message:
        return "error"
    
    # If PR processing failed, status is error
    if pr_processing_result and pr_processing_result.get("status") == "error":
        return "error"
    
    # If processing succeeded but no spells matched, status is partial_success
    if not matched_spells:
        return "partial_success"
    
    # If processing succeeded and spells matched, status is success
    return "success"


async def create_execution_log(
    db: AsyncSession,
    repo_name: str,
    event_type: str,
    status: Optional[str] = None,
    pr_number: Optional[int] = None,
    action: Optional[str] = None,
    matched_spell_ids: Optional[List[int]] = None,
    auto_generated_spell_id: Optional[int] = None,
    error_message: Optional[str] = None,
    pr_processing_result: Optional[Dict[str, Any]] = None,
    execution_duration_ms: Optional[int] = None
) -> Optional[WebhookExecutionLog]:
    """
    Create a webhook execution log entry.
    
    Creates a detailed log record of a webhook processing run, capturing
    all relevant data including matched spells, errors, and metadata.
    Links the log to a repository configuration if one exists.
    
    This function handles all aspects of log creation:
    - Finding associated repository configuration
    - Determining execution status if not provided
    - Serializing complex fields to JSON
    - Comprehensive error handling
    
    Args:
        db: Database session
        repo_name: Repository full name (e.g., "octocat/Hello-World")
        event_type: GitHub event type (e.g., "pull_request", "push")
        status: Execution status (success, partial_success, error).
                If None, will be determined automatically.
        pr_number: Pull request number (optional)
        action: GitHub event action (e.g., "opened", "synchronize")
        matched_spell_ids: List of matched spell IDs (optional)
        auto_generated_spell_id: ID of auto-generated spell (optional)
        error_message: Error message if processing failed (optional)
        pr_processing_result: Full PR processing result dictionary (optional)
        execution_duration_ms: Execution time in milliseconds (optional)
        
    Returns:
        Created WebhookExecutionLog instance if successful, None if failed
        
    Raises:
        Does not raise exceptions - logs errors and returns None on failure
        
    Example:
        log = await create_execution_log(
            db=db,
            repo_name="octocat/Hello-World",
            event_type="pull_request",
            pr_number=123,
            action="opened",
            matched_spell_ids=[1, 2, 3],
            pr_processing_result={
                "repo": "octocat/Hello-World",
                "pr_number": 123,
                "files_changed": ["app/main.py"],
                "status": "success"
            },
            execution_duration_ms=1850
        )
        
        if log:
            print(f"Created log {log.id} with status {log.status}")
    """
    try:
        # Find associated repo config if exists
        repo_config_id = await _find_repo_config_id(db, repo_name)
        
        # Determine status if not provided
        if status is None:
            status = _determine_status(
                pr_processing_result,
                matched_spell_ids or [],
                error_message
            )
        
        # Serialize matched_spell_ids to JSON string
        matched_spell_ids_json = None
        if matched_spell_ids is not None:
            try:
                matched_spell_ids_json = json.dumps(matched_spell_ids)
            except (TypeError, ValueError) as e:
                logger.warning(
                    f"Failed to serialize matched_spell_ids: {str(e)}",
                    extra={"matched_spell_ids": matched_spell_ids}
                )
                # Use empty array as fallback
                matched_spell_ids_json = json.dumps([])
        
        # Serialize pr_processing_result to JSON string
        pr_processing_result_json = None
        if pr_processing_result is not None:
            try:
                pr_processing_result_json = json.dumps(pr_processing_result)
            except (TypeError, ValueError) as e:
                logger.warning(
                    f"Failed to serialize pr_processing_result: {str(e)}",
                    extra={"pr_processing_result": pr_processing_result}
                )
                # Don't store invalid JSON
                pr_processing_result_json = None
        
        # Create log entry
        log_entry = WebhookExecutionLog(
            repo_config_id=repo_config_id,
            repo_name=repo_name,
            pr_number=pr_number,
            event_type=event_type,
            action=action,
            status=status,
            matched_spell_ids=matched_spell_ids_json,
            auto_generated_spell_id=auto_generated_spell_id,
            error_message=error_message,
            pr_processing_result=pr_processing_result_json,
            execution_duration_ms=execution_duration_ms
        )
        
        # Add to database with constraint handling
        try:
            db.add(log_entry)
            await db.commit()
            await db.refresh(log_entry)
        except IntegrityError as e:
            await db.rollback()
            log_constraint_violation_attempt(
                "webhook_log_creation",
                repository_id=repo_config_id,
                error_details=str(e)
            )
            # Re-raise as this is a critical error in webhook processing
            raise
        
        logger.info(
            f"Created webhook execution log {log_entry.id} for {repo_name}",
            extra={
                "log_id": log_entry.id,
                "repo_name": repo_name,
                "pr_number": pr_number,
                "status": status,
                "matched_spells_count": len(matched_spell_ids) if matched_spell_ids else 0,
                "execution_duration_ms": execution_duration_ms
            }
        )
        
        return log_entry
        
    except Exception as e:
        # Log error with full context
        logger.error(
            f"Failed to create webhook execution log for {repo_name}: {str(e)}",
            exc_info=True,
            extra={
                "repo_name": repo_name,
                "pr_number": pr_number,
                "event_type": event_type,
                "error_type": type(e).__name__
            }
        )
        
        # Rollback transaction on error
        try:
            await db.rollback()
        except Exception as rollback_error:
            logger.error(
                f"Failed to rollback transaction: {str(rollback_error)}",
                exc_info=True
            )
        
        # Return None to indicate failure
        return None
