"""
GitHub Webhook API endpoint.

This module handles incoming GitHub webhook events, specifically pull_request events.
It validates webhook signatures for security and processes PR events.
"""

import hashlib
import hmac
import logging
import os, json
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

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


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Handle GitHub webhook events.
    
    Receives and processes GitHub pull_request webhook events.
    Validates the webhook signature to ensure authenticity.
    
    Args:
        request: FastAPI request object containing the webhook payload
        x_hub_signature_256: GitHub signature header for validation
        x_github_event: GitHub event type header
        db: Database session dependency
        
    Returns:
        Success message with event details
        
    Raises:
        HTTPException: 401 if signature validation fails
        
    Example:
        POST /webhook
        Headers:
            X-Hub-Signature-256: sha256=abc123...
            X-GitHub-Event: pull_request
        Body: {GitHub webhook payload}
        Response: {"status": "success", "event": "pull_request"}
    """
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
    
    if not validate_signature(body, x_hub_signature_256, webhook_secret):
        logger.warning(
            "Invalid webhook signature received",
            extra={
                "signature": x_hub_signature_256[:20] + "...",  # Log partial signature
                "event_type": x_github_event
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Parse JSON payload from the raw body
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
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
    
    # TODO: Process pull_request events
    # - Extract PR metadata (repo, PR number, action)
    # - Trigger PR processor service
    # - Handle errors and return appropriate responses
    
    # Return success response
    return {
        "status": "success",
        "event": x_github_event,
        "action": payload.get("action")
    }
