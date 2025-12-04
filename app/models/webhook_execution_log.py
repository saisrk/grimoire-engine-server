"""
Webhook execution log data model and schemas.

A webhook execution log represents a detailed record of a single webhook
processing run, capturing matched spells, auto-generated spells, errors,
and processing metadata.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db.database import Base


class WebhookExecutionLog(Base):
    """
    SQLAlchemy model for a webhook execution log.
    
    A webhook execution log captures detailed information about a single
    webhook processing run, including matched spells, errors, and metadata.
    """
    __tablename__ = "webhook_execution_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_config_id = Column(
        Integer, 
        ForeignKey("repository_configs.id", ondelete="CASCADE"), 
        nullable=True, 
        index=True
    )
    repo_name = Column(String(255), nullable=False, index=True)
    pr_number = Column(Integer, nullable=True)
    event_type = Column(String(50), nullable=False)
    action = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, index=True)  # success, partial_success, error
    matched_spell_ids = Column(Text, nullable=True)  # JSON array as string
    auto_generated_spell_id = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    pr_processing_result = Column(Text, nullable=True)  # JSON object as string
    execution_duration_ms = Column(Integer, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# Pydantic Schemas

class WebhookExecutionLogResponse(BaseModel):
    """
    Schema for webhook execution log responses.
    
    This schema represents a complete webhook execution log with all captured
    data, including matched spells, errors, processing results, and metadata.
    
    **Status Values:**
    - `success`: Webhook processed successfully, spells matched
    - `partial_success`: Webhook processed but with warnings (e.g., no spells matched)
    - `error`: Webhook processing failed
    
    **Computed Fields:**
    - `files_changed_count`: Number of files changed in the PR
    - `spell_match_attempted`: Whether spell matching was attempted
    - `spell_generation_attempted`: Whether spell auto-generation was attempted
    
    **Example:**
    ```json
    {
        "id": 42,
        "repo_config_id": 1,
        "repo_name": "octocat/Hello-World",
        "pr_number": 123,
        "event_type": "pull_request",
        "action": "opened",
        "status": "success",
        "matched_spell_ids": [5, 12, 3],
        "auto_generated_spell_id": null,
        "error_message": null,
        "pr_processing_result": {
            "repo": "octocat/Hello-World",
            "pr_number": 123,
            "files_changed": ["app/main.py", "tests/test_main.py"],
            "status": "success"
        },
        "execution_duration_ms": 1850,
        "executed_at": "2025-12-05T11:45:23Z",
        "files_changed_count": 2,
        "spell_match_attempted": true,
        "spell_generation_attempted": false
    }
    ```
    """
    id: int = Field(
        ...,
        description="Unique identifier for this webhook execution log"
    )
    repo_config_id: Optional[int] = Field(
        None,
        description="ID of the associated repository configuration (null if no config exists)"
    )
    repo_name: str = Field(
        ...,
        description="GitHub repository name in 'owner/repo' format",
        examples=["octocat/Hello-World"]
    )
    pr_number: Optional[int] = Field(
        None,
        description="Pull request number (null for non-PR events)"
    )
    event_type: str = Field(
        ...,
        description="GitHub webhook event type",
        examples=["pull_request", "push", "issues"]
    )
    action: Optional[str] = Field(
        None,
        description="GitHub webhook action (e.g., 'opened', 'closed', 'synchronize')"
    )
    status: str = Field(
        ...,
        description="Execution status: 'success', 'partial_success', or 'error'",
        examples=["success", "partial_success", "error"]
    )
    matched_spell_ids: List[int] = Field(
        default_factory=list,
        description="List of spell IDs that matched this webhook event"
    )
    auto_generated_spell_id: Optional[int] = Field(
        None,
        description="ID of the auto-generated spell (null if no spell was generated)"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if webhook processing failed (null on success)"
    )
    pr_processing_result: Optional[Dict[str, Any]] = Field(
        None,
        description="Detailed PR processing result including files changed and status"
    )
    execution_duration_ms: Optional[int] = Field(
        None,
        description="Webhook execution duration in milliseconds"
    )
    executed_at: datetime = Field(
        ...,
        description="Timestamp when the webhook was executed"
    )
    
    # Computed fields
    files_changed_count: int = Field(
        default=0,
        description="Number of files changed in the PR (computed from pr_processing_result)"
    )
    spell_match_attempted: bool = Field(
        default=False,
        description="Whether spell matching was attempted (computed from pr_processing_result)"
    )
    spell_generation_attempted: bool = Field(
        default=False,
        description="Whether spell auto-generation was attempted (computed from pr_processing_result)"
    )
    
    model_config = {"from_attributes": True}  # SQLAlchemy 2.0 compatibility
