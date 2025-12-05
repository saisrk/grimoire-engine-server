"""
Spell Application data model and schemas.

A spell application represents an instance where a spell was applied to generate
a context-aware patch for a specific failing code scenario.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class SpellApplication(Base):
    """
    SQLAlchemy model for spell application history.
    
    Tracks each time a spell is applied to generate a patch,
    storing the context, generated patch, and metadata.
    """
    __tablename__ = "spell_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    spell_id = Column(Integer, ForeignKey("spells.id"), nullable=False, index=True)
    
    # Failing context
    repository = Column(String(500), nullable=False)
    commit_sha = Column(String(40), nullable=False)
    language = Column(String(50))
    version = Column(String(50))
    failing_test = Column(String(500))
    stack_trace = Column(Text)
    
    # Generated patch
    patch = Column(Text, nullable=False)
    files_touched = Column(Text, nullable=False)  # JSON array as string
    rationale = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    spell = relationship("Spell", back_populates="applications")


# Pydantic Schemas

class FailingContext(BaseModel):
    """
    Context about the failing code.
    
    Provides information about the repository, error, and environment
    where the spell should be applied.
    """
    repository: str = Field(
        ..., 
        min_length=1, 
        max_length=500,
        description="Repository name in format 'owner/repo' (e.g., 'myorg/myrepo')",
        examples=["myorg/myrepo"]
    )
    commit_sha: str = Field(
        ..., 
        min_length=7, 
        max_length=40,
        description="Git commit SHA where the patch should be applied (7-40 characters)",
        examples=["abc123def456"]
    )
    language: Optional[str] = Field(
        None, 
        max_length=50,
        description="Programming language of the codebase (e.g., 'python', 'javascript')",
        examples=["python"]
    )
    version: Optional[str] = Field(
        None, 
        max_length=50,
        description="Language or framework version (e.g., '3.11', '18.0')",
        examples=["3.11"]
    )
    failing_test: Optional[str] = Field(
        None, 
        max_length=500,
        description="Name of the failing test case",
        examples=["test_user_login"]
    )
    stack_trace: Optional[str] = Field(
        None,
        description="Full stack trace or error message from the failing test",
        examples=["Traceback (most recent call last):\n  File 'test.py', line 10, in test_user_login\n    assert user is not None\nAssertionError"]
    )


class AdaptationConstraints(BaseModel):
    """
    Constraints for patch generation.
    
    Defines rules and limits for how the spell can be adapted to the codebase.
    """
    max_files: int = Field(
        default=3, 
        ge=1, 
        le=10,
        description="Maximum number of files that can be modified in the patch (1-10)",
        examples=[3]
    )
    excluded_patterns: List[str] = Field(
        default_factory=lambda: ["package.json", "*.lock"],
        description="List of file patterns that should not be modified (glob patterns)",
        examples=[["package.json", "*.lock", "node_modules/*"]]
    )
    preserve_style: bool = Field(
        default=True,
        description="Whether to preserve the existing coding style and conventions",
        examples=[True]
    )


class PatchResult(BaseModel):
    """
    Result of patch generation (internal use).
    
    Contains the generated patch and metadata from the LLM.
    """
    patch: str = Field(
        ...,
        description="Git unified diff patch that can be applied to the repository",
        examples=["diff --git a/app/auth.py b/app/auth.py\nindex 1234567..abcdefg 100644\n--- a/app/auth.py\n+++ b/app/auth.py\n@@ -10,6 +10,8 @@\n def login(user):\n+    if user is None:\n+        return None\n     return user.token"]
    )
    files_touched: List[str] = Field(
        ...,
        description="List of file paths that were modified in the patch",
        examples=[["app/auth.py", "app/models/user.py"]]
    )
    rationale: str = Field(
        ...,
        description="Brief explanation of the changes made (1-2 sentences)",
        examples=["Added null check before accessing user object to prevent AttributeError"]
    )


class SpellApplicationRequest(BaseModel):
    """
    Request to apply a spell.
    
    Contains the failing code context and optional constraints for patch generation.
    """
    failing_context: FailingContext = Field(
        ...,
        description="Information about the failing code and repository context"
    )
    adaptation_constraints: Optional[AdaptationConstraints] = Field(
        None,
        description="Optional constraints for how the patch should be generated (defaults applied if not provided)"
    )


class SpellApplicationResponse(BaseModel):
    """
    Response from spell application.
    
    Contains the generated patch, metadata, and application record ID.
    """
    application_id: int = Field(
        ...,
        description="Unique ID of the created spell application record",
        examples=[1]
    )
    patch: str = Field(
        ...,
        description="Git unified diff patch that can be applied to the repository",
        examples=["diff --git a/app/auth.py b/app/auth.py\nindex 1234567..abcdefg 100644\n--- a/app/auth.py\n+++ b/app/auth.py\n@@ -10,6 +10,8 @@\n def login(user):\n+    if user is None:\n+        return None\n     return user.token"]
    )
    files_touched: List[str] = Field(
        ...,
        description="List of file paths that were modified in the patch",
        examples=[["app/auth.py"]]
    )
    rationale: str = Field(
        ...,
        description="Brief explanation of the changes made (1-2 sentences)",
        examples=["Added null check before accessing user object to prevent AttributeError"]
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the application was created",
        examples=["2025-12-05T10:30:00Z"]
    )
    
    model_config = {"from_attributes": True}


class SpellApplicationSummary(BaseModel):
    """
    Summary of a spell application for history.
    
    Lightweight representation of a spell application used in history listings.
    """
    id: int = Field(
        ...,
        description="Unique ID of the spell application record",
        examples=[1]
    )
    spell_id: int = Field(
        ...,
        description="ID of the spell that was applied",
        examples=[1]
    )
    repository: str = Field(
        ...,
        description="Repository name where the spell was applied",
        examples=["myorg/myrepo"]
    )
    commit_sha: str = Field(
        ...,
        description="Git commit SHA where the patch was applied",
        examples=["abc123def456"]
    )
    files_touched: List[str] = Field(
        ...,
        description="List of file paths that were modified",
        examples=[["app/auth.py", "app/models/user.py"]]
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the application was created",
        examples=["2025-12-05T10:30:00Z"]
    )
    
    model_config = {"from_attributes": True}
    
    @classmethod
    def from_orm_with_json_parse(cls, obj):
        """Create instance from ORM object, parsing JSON fields."""
        import json
        data = {
            "id": obj.id,
            "spell_id": obj.spell_id,
            "repository": obj.repository,
            "commit_sha": obj.commit_sha,
            "files_touched": json.loads(obj.files_touched) if isinstance(obj.files_touched, str) else obj.files_touched,
            "created_at": obj.created_at
        }
        return cls(**data)
