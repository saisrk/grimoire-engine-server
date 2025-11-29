"""
Spell CRUD API endpoints.

This module provides REST API endpoints for managing spells:
- GET /api/spells - List all spells with pagination
- GET /api/spells/{id} - Get a single spell by ID
- POST /api/spells - Create a new spell
- PUT /api/spells/{id} - Update an existing spell
- DELETE /api/spells/{id} - Delete a spell
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.spell import Spell, SpellCreate, SpellUpdate, SpellResponse

router = APIRouter(prefix="/api/spells", tags=["spells"])


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
) -> SpellResponse:
    """
    Get a single spell by ID.
    
    Args:
        spell_id: ID of the spell to retrieve
        db: Database session dependency
        
    Returns:
        Spell object with all fields
        
    Raises:
        HTTPException: 404 if spell not found
        
    Example:
        GET /api/spells/1
        Response: {"id": 1, "title": "Fix undefined variable", ...}
    """
    result = await db.execute(
        select(Spell).where(Spell.id == spell_id)
    )
    spell = result.scalar_one_or_none()
    
    if spell is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found"
        )
    
    return spell


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
