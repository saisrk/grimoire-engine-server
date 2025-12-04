"""
Repository configuration data model and schemas.

A repository configuration represents a GitHub repository that has webhook
integration enabled, including repository metadata and webhook settings.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from app.db.database import Base


class RepositoryConfig(Base):
    """
    SQLAlchemy model for a repository configuration.
    
    A repository configuration stores settings for a GitHub repository
    that has webhook integration enabled with the Grimoire Engine Backend.
    """
    __tablename__ = "repository_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(255), nullable=False, unique=True, index=True)
    webhook_url = Column(String(500), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Pydantic Schemas

class RepositoryConfigBase(BaseModel):
    """
    Base schema with common repository config fields.
    
    This schema contains the core fields that are used for both
    creating and representing repository configurations.
    """
    repo_name: str = Field(
        ...,
        pattern=r"^[\w\-\.]+/[\w\-\.]+$",
        min_length=1,
        max_length=255,
        description="GitHub repository name in 'owner/repo' format (e.g., 'octocat/Hello-World')",
        examples=["octocat/Hello-World", "facebook/react", "microsoft/vscode"]
    )
    webhook_url: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="URL where GitHub should send webhook events",
        examples=["https://grimoire.example.com/webhook/github"]
    )
    enabled: bool = Field(
        default=True,
        description="Whether webhook integration is enabled for this repository"
    )


class RepositoryConfigCreate(RepositoryConfigBase):
    """
    Schema for creating a new repository configuration.
    
    Use this schema when registering a new GitHub repository for webhook integration.
    The repository name must be unique and follow the 'owner/repo' format.
    
    **Example:**
    ```json
    {
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": true
    }
    ```
    """
    pass


class RepositoryConfigUpdate(BaseModel):
    """
    Schema for updating an existing repository configuration.
    
    All fields are optional. Only provided fields will be updated.
    The repository name cannot be changed after creation.
    
    **Example:**
    ```json
    {
        "webhook_url": "https://new-url.example.com/webhook/github",
        "enabled": false
    }
    ```
    """
    webhook_url: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="New webhook URL (optional)"
    )
    enabled: Optional[bool] = Field(
        None,
        description="New enabled status (optional)"
    )


class RepositoryConfigResponse(RepositoryConfigBase):
    """
    Schema for repository config responses.
    
    This schema includes all database fields plus computed fields
    for webhook statistics. Returned by all repository config endpoints.
    
    **Computed Fields:**
    - `webhook_count`: Total number of webhook executions for this repository
    - `last_webhook_at`: Timestamp of the most recent webhook execution
    
    **Example:**
    ```json
    {
        "id": 1,
        "repo_name": "octocat/Hello-World",
        "webhook_url": "https://grimoire.example.com/webhook/github",
        "enabled": true,
        "created_at": "2025-12-05T10:00:00Z",
        "updated_at": "2025-12-05T12:00:00Z",
        "webhook_count": 15,
        "last_webhook_at": "2025-12-05T11:45:00Z"
    }
    ```
    """
    id: int = Field(
        ...,
        description="Unique identifier for this repository configuration"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when this configuration was created"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp when this configuration was last updated"
    )
    webhook_count: int = Field(
        default=0,
        description="Total number of webhook executions for this repository (computed field)"
    )
    last_webhook_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the most recent webhook execution (computed field)"
    )
    
    model_config = {"from_attributes": True}  # SQLAlchemy 2.0 compatibility
