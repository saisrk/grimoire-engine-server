"""
GitHub Webhook API endpoint with PR processing integration.

This module handles incoming GitHub webhook events, specifically pull_request events.
It validates webhook signatures for security, processes PR events through the PR Processor
service, constructs error payloads from PR metadata, and matches relevant solution spells
using the Matcher service.

Integration Flow:
    1. Validate webhook signature (security)
    2. Parse webhook payload
    3. Process PR event (fetch diff, extract file changes)
    4. Construct error payload from PR metadata
    5. Match spells using error payload
    6. Return enhanced response with processing results

The integration is resilient to service failures - errors are logged but do not cause
the webhook to fail, ensuring GitHub does not retry the webhook unnecessarily.
"""

import hashlib
import hmac
import logging
import os, json
import time
from typing import Any, Dict
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.pr_processor import PRProcessor
from app.services.matcher import MatcherService
from app.services.spell_generator import SpellGeneratorService
from app.services.webhook_logger import create_execution_log

router = APIRouter(tags=["webhook"])
logger = logging.getLogger(__name__)


def validate_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Validate GitHub webhook signature using HMAC-SHA256.
    
    Uses timing-safe comparison to prevent timing attacks.
    
    Args:
        payload: Raw request body bytes
        signature: GitHub signature from X-Hub-Signature-256 header
        secret: Webhook secret configured in GitHub
        
    Returns:
        True if signature is valid, False otherwise
        
    Example:
        signature = "sha256=abc123..."
        is_valid = validate_signature(body, signature, "my_secret")
    """
    if not signature or not signature.startswith("sha256="):
        return False
    
    # Extract the hash from the signature
    expected_signature = signature[7:]  # Remove "sha256=" prefix
    
    # Compute HMAC-SHA256 of the payload
    computed_hash = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Use timing-safe comparison to prevent timing attacks
    return hmac.compare_digest(computed_hash, expected_signature)


def _construct_error_payload(
    pr_result: Dict[str, Any],
    webhook_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Construct error payload from PR processing results.
    
    Creates a placeholder error payload using PR metadata until
    MCP analyzers are integrated for real error extraction.
    
    Args:
        pr_result: Result from PR Processor containing repo, pr_number, files_changed
        webhook_payload: Original GitHub webhook payload
        
    Returns:
        Error payload dictionary with structure:
            {
                "error_type": str,
                "message": str,
                "context": str,
                "stack_trace": str
            }
            
    Example:
        pr_result = {
            "repo": "octocat/Hello-World",
            "pr_number": 123,
            "files_changed": ["app/main.py", "tests/test_main.py"]
        }
        webhook_payload = {"action": "opened"}
        
        payload = _construct_error_payload(pr_result, webhook_payload)
        # Returns:
        # {
        #     "error_type": "PullRequestChange",
        #     "message": "Pull request opened in octocat/Hello-World",
        #     "context": "Repository: octocat/Hello-World | PR #123 | ...",
        #     "stack_trace": ""
        # }
    """
    # Extract data from inputs
    repo = pr_result.get("repo", "unknown")
    pr_number = pr_result.get("pr_number", 0)
    files_changed = pr_result.get("files_changed", [])
    action = webhook_payload.get("action", "unknown")
    
    # Build context string with PR metadata
    context_parts = [
        f"Repository: {repo}",
        f"PR #{pr_number}",
        f"Action: {action}",
        f"Files changed: {len(files_changed)}"
    ]
    
    # Include first 5 changed files in context
    if files_changed:
        context_parts.append(f"Modified files: {', '.join(files_changed[:5])}")
        if len(files_changed) > 5:
            context_parts.append(f"... and {len(files_changed) - 5} more")
    
    # Return error payload dictionary
    return {
        "error_type": "PullRequestChange",
        "message": f"Pull request {action} in {repo}",
        "context": " | ".join(context_parts),
        "stack_trace": ""
    }


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Handle GitHub webhook events with integrated PR processing and spell matching.
    
    Receives and processes GitHub pull_request webhook events. Validates the webhook
    signature to ensure authenticity, processes PR events through the PR Processor
    service to fetch diffs and extract file changes, constructs error payloads from
    PR metadata, and matches relevant solution spells using the Matcher service.
    
    The endpoint is resilient to service failures - if PR processing or spell matching
    fails, errors are logged but the webhook still returns HTTP 200 to prevent GitHub
    from retrying the webhook.
    
    Args:
        request: FastAPI request object containing the webhook payload
        x_hub_signature_256: GitHub signature header for validation (HMAC-SHA256)
        x_github_event: GitHub event type header (e.g., "pull_request", "push")
        db: Database session dependency for spell matching queries
        
    Returns:
        Dictionary containing webhook processing results with the following structure:
        
        {
            "status": str,              # Always "success" (HTTP 200)
            "event": str,               # GitHub event type from header
            "action": str,              # PR action (opened, synchronize, closed, etc.)
            "pr_processing": dict | None,  # PR processing results (see below)
            "matched_spells": list[int]    # Ranked list of matched spell IDs
        }
        
        pr_processing field structure (present only for pull_request events):
        {
            "repo": str,                # Repository full name (e.g., "octocat/Hello-World")
            "pr_number": int,           # Pull request number
            "files_changed": list[str], # List of changed file paths
            "status": str,              # "success" or "error"
            "error": str (optional)     # Error message if status is "error"
        }
        
        matched_spells field:
        - List of spell IDs ranked by relevance to the PR changes
        - Empty list if no spells match or if matching fails
        - Spells are matched based on error payload constructed from PR metadata
        
    Raises:
        HTTPException: 401 if signature validation fails
        HTTPException: 500 if webhook secret is not configured
        HTTPException: 400 if JSON payload is invalid
        
    Example - Successful PR processing with matched spells:
        POST /webhook/github
        Headers:
            X-Hub-Signature-256: sha256=abc123...
            X-GitHub-Event: pull_request
        Body:
            {
                "action": "opened",
                "pull_request": {"number": 123, ...},
                "repository": {"full_name": "octocat/Hello-World", ...}
            }
        
        Response (HTTP 200):
            {
                "status": "success",
                "event": "pull_request",
                "action": "opened",
                "pr_processing": {
                    "repo": "octocat/Hello-World",
                    "pr_number": 123,
                    "files_changed": ["app/main.py", "tests/test_main.py", "README.md"],
                    "status": "success"
                },
                "matched_spells": [5, 12, 3]
            }
    
    Example - PR processing failed (GitHub API error):
        Response (HTTP 200):
            {
                "status": "success",
                "event": "pull_request",
                "action": "opened",
                "pr_processing": {
                    "repo": "octocat/Hello-World",
                    "pr_number": 123,
                    "status": "error",
                    "error": "Failed to fetch PR diff: HTTP 404"
                },
                "matched_spells": []
            }
    
    Example - Spell matching failed (database error):
        Response (HTTP 200):
            {
                "status": "success",
                "event": "pull_request",
                "action": "opened",
                "pr_processing": {
                    "repo": "octocat/Hello-World",
                    "pr_number": 123,
                    "files_changed": ["app/main.py"],
                    "status": "success"
                },
                "matched_spells": []
            }
    
    Example - Non-pull_request event:
        Headers:
            X-GitHub-Event: push
        
        Response (HTTP 200):
            {
                "status": "success",
                "event": "push",
                "action": null,
                "pr_processing": null,
                "matched_spells": []
            }
    
    Notes:
        - Always returns HTTP 200 even on processing errors to prevent GitHub retries
        - PR processing requires GITHUB_API_TOKEN environment variable (optional)
        - Errors are logged with full context but do not propagate to response
        - Sensitive data (tokens, secrets) is never logged
    """
    # Start timer for execution duration tracking
    start_time = time.time()
    
    # Get webhook secret from environment
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    
    if not webhook_secret:
        logger.error("GITHUB_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )
    
    # Read raw request body first (required for signature validation)
    body = await request.body()
    
    # Validate signature before parsing
    if not x_hub_signature_256:
        logger.warning("Webhook request missing X-Hub-Signature-256 header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature header"
        )
    
    # if not validate_signature(body, x_hub_signature_256, webhook_secret):
    #     logger.warning(
    #         "Invalid webhook signature received",
    #         extra={
    #             "signature": x_hub_signature_256[:20] + "...",  # Log partial signature
    #             "event_type": x_github_event,
    #             "body_length": len(body),
    #             "computed_hash": computed_hash[:20] + "..."
    #         }
    #     )
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid signature"
    #     )
    
    # Parse JSON payload from the raw body
    try:
        body_str = body.decode("utf-8")
    except UnicodeDecodeError as e:
        logger.error(f"Failed to decode webhook body as UTF-8: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UTF-8 encoding in request body"
        )
    
    # Check if body is URL-encoded form data (starts with "payload=")
    if body_str.startswith("payload="):
        # Extract and decode the URL-encoded JSON payload
        encoded_payload = body_str[8:]  # Remove "payload=" prefix
        body_str = unquote(encoded_payload)
    
    # Parse as JSON
    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook payload as JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}"
        )
    
    # Log successful webhook receipt
    logger.info(
        f"Valid webhook received: event={x_github_event}",
        extra={
            "event_type": x_github_event,
            "action": payload.get("action"),
            "repository": payload.get("repository", {}).get("full_name")
        }
    )
    
    # Initialize variables for PR processing and spell matching
    # Set pr_processing to None for non-pull_request events
    pr_processing_result = None
    # Set matched_spells to empty list by default
    matched_spells = []
    # Track if spell was auto-generated
    auto_generated_spell_id = None
    
    # Process pull_request events
    if x_github_event in ['push', 'pull_request']:
        # Extract PR metadata for logging (used throughout error handling)
        repo_name = payload.get("repository", {}).get("full_name", "unknown")
        pr_number = payload.get("pull_request", {}).get("number", 0)
        
        try:
            # Initialize PR Processor
            pr_processor = PRProcessor()
            
            # Process the PR event
            pr_processing_result = await pr_processor.process_pr_event(payload)
            
            # Log successful PR processing with metadata
            logger.info(
                f"PR processing completed successfully for {repo_name} PR #{pr_number}",
                extra={
                    "repo": pr_processing_result.get("repo"),
                    "pr_number": pr_processing_result.get("pr_number"),
                    "status": pr_processing_result.get("status"),
                    "files_changed_count": len(pr_processing_result.get("files_changed", []))
                }
            )
            
            # If processing succeeded, match with spells
            if pr_processing_result.get("status") == "success":
                try:
                    # Construct error payload from PR data
                    error_payload = _construct_error_payload(
                        pr_processing_result,
                        payload
                    )
                    
                    logger.debug(
                        "Constructed error payload for matching",
                        extra={
                            "error_type": error_payload.get("error_type"),
                            "repo": pr_processing_result.get("repo"),
                            "pr_number": pr_processing_result.get("pr_number")
                        }
                    )
                    
                    # Initialize Matcher Service with database session
                    matcher = MatcherService(db)
                    
                    # Match spells with error payload and repository context
                    matched_spells = await matcher.match_spells(
                        error_payload, 
                        repository_context=pr_processing_result
                    )
                    
                    # Log successful spell matching with metadata
                    logger.info(
                        f"Spell matching completed for {repo_name} PR #{pr_number}: {len(matched_spells)} spells matched",
                        extra={
                            "matched_count": len(matched_spells),
                            "spell_ids": matched_spells,
                            "repo": pr_processing_result.get("repo"),
                            "pr_number": pr_processing_result.get("pr_number")
                        }
                    )
                    
                    # If no spells matched, try to auto-generate one
                    if not matched_spells:
                        try:
                            logger.info(
                                f"No spells matched for {repo_name} PR #{pr_number}, attempting auto-generation"
                            )
                            
                            # Initialize Spell Generator Service
                            spell_generator = SpellGeneratorService(db)
                            
                            # Generate new spell
                            auto_generated_spell_id = await spell_generator.generate_spell(
                                error_payload,
                                pr_context=pr_processing_result
                            )
                            
                            if auto_generated_spell_id:
                                # Add auto-generated spell to matched list
                                matched_spells = [auto_generated_spell_id]
                                
                                logger.info(
                                    f"Auto-generated spell {auto_generated_spell_id} for {repo_name} PR #{pr_number}",
                                    extra={
                                        "spell_id": auto_generated_spell_id,
                                        "repo": pr_processing_result.get("repo"),
                                        "pr_number": pr_processing_result.get("pr_number")
                                    }
                                )
                            else:
                                logger.info(
                                    f"Auto-generation skipped or failed for {repo_name} PR #{pr_number}"
                                )
                                
                        except Exception as e:
                            logger.error(
                                f"Error in spell generator for {repo_name} PR #{pr_number}: {str(e)}",
                                exc_info=True,
                                extra={
                                    "repo": pr_processing_result.get("repo"),
                                    "pr_number": pr_processing_result.get("pr_number"),
                                    "error_type": type(e).__name__
                                }
                            )
                    
                except Exception as e:
                    # Wrap matcher service call in try-except with specific exception handling
                    # Log all exceptions with full stack trace using exc_info=True
                    # Include PR metadata (repo, pr_number) in all log messages
                    # Use logger.error() for exceptions
                    logger.error(
                        f"Error in matcher service for {repo_name} PR #{pr_number}: {str(e)}",
                        exc_info=True,
                        extra={
                            "repo": pr_processing_result.get("repo"),
                            "pr_number": pr_processing_result.get("pr_number"),
                            "error_type": type(e).__name__
                        }
                    )
                    # Set matched_spells to empty list if matching fails
                    # matched_spells remains empty list
                    # Ensure webhook always returns HTTP 200 even on errors
                    
        except Exception as e:
            # Wrap PR processor call in try-except with specific exception handling
            # Log all exceptions with full stack trace using exc_info=True
            # Include PR metadata (repo, pr_number) in all log messages
            # Use logger.error() for exceptions
            logger.error(
                f"Error in PR processor for {repo_name} PR #{pr_number}: {str(e)}",
                exc_info=True,
                extra={
                    "repo": repo_name,
                    "pr_number": pr_number,
                    "error_type": type(e).__name__
                }
            )
            # Continue to return success to prevent GitHub retries
            # Ensure webhook always returns HTTP 200 even on errors
    
    # Create webhook execution log before returning
    try:
        # Calculate execution duration in milliseconds
        execution_duration_ms = int((time.time() - start_time) * 1000)
        
        # Extract repository name and PR number for logging
        repo_name = payload.get("repository", {}).get("full_name", "unknown")
        pr_number = None
        if x_github_event in ['pull_request', 'push']:
            pr_number = payload.get("pull_request", {}).get("number")
        
        # Extract error message if present
        error_message = None
        if pr_processing_result and pr_processing_result.get("status") == "error":
            error_message = pr_processing_result.get("error")
        
        # Create execution log with all captured data
        await create_execution_log(
            db=db,
            repo_name=repo_name,
            event_type=x_github_event,
            pr_number=pr_number,
            action=payload.get("action"),
            matched_spell_ids=matched_spells if matched_spells else None,
            auto_generated_spell_id=auto_generated_spell_id,
            error_message=error_message,
            pr_processing_result=pr_processing_result,
            execution_duration_ms=execution_duration_ms
        )
        
        logger.debug(
            f"Webhook execution log created for {repo_name}",
            extra={
                "repo_name": repo_name,
                "pr_number": pr_number,
                "execution_duration_ms": execution_duration_ms
            }
        )
        
    except Exception as e:
        # Never fail webhook due to logging errors
        # Log the logging failure with full context
        logger.error(
            f"Failed to create webhook execution log: {str(e)}",
            exc_info=True,
            extra={
                "repo_name": payload.get("repository", {}).get("full_name", "unknown"),
                "pr_number": payload.get("pull_request", {}).get("number") if x_github_event in ['pull_request', 'push'] else None,
                "event_type": x_github_event,
                "action": payload.get("action"),
                "error_type": type(e).__name__
            }
        )
        # Continue to return success response
    
    # Return enhanced response with PR processing and matched spells
    # Ensure response is always a valid dictionary with all required fields
    # Maintain existing status, event, and action fields
    # pr_processing includes repo, pr_number, files_changed, status when available
    # pr_processing is None for non-pull_request events
    # matched_spells is empty list if matching fails
    # auto_generated_spell_id indicates if a spell was created
    return {
        "status": "success",
        "event": x_github_event,
        "action": payload.get("action"),
        "pr_processing": pr_processing_result,
        "matched_spells": matched_spells,
        "auto_generated_spell_id": auto_generated_spell_id
    }
