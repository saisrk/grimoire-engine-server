"""
Spell data model and schemas.

A spell represents a reusable code solution or pattern that can fix specific errors.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.db.database import Base


class Spell(Base):
    """
    SQLAlchemy model for a reusable code solution or pattern.
    
    A spell captures a specific error pattern and its solution,
    including code snippets, explanations, and metadata for matching.
    """
    __tablename__ = "spells"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    error_type = Column(String(100), nullable=False, index=True)
    error_pattern = Column(Text, nullable=False)
    solution_code = Column(Text, nullable=False)
    tags = Column(String(500))  # Comma-separated tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Extension point: Add vector embedding column when integrating vector DB
    # embedding = Column(Vector(1536))  # For OpenAI ada-002 embeddings


# Pydantic Schemas

class SpellBase(BaseModel):
    """Base schema with common spell fields."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    error_type: str = Field(..., min_length=1, max_length=100)
    error_pattern: str = Field(..., min_length=1)
    solution_code: str = Field(..., min_length=1)
    tags: Optional[str] = None


class SpellCreate(SpellBase):
    """Schema for creating a new spell."""
    pass


class SpellUpdate(SpellBase):
    """Schema for updating an existing spell."""
    pass


class SpellResponse(SpellBase):
    """Schema for spell responses (includes DB fields)."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}  # SQLAlchemy 2.0 compatibility
