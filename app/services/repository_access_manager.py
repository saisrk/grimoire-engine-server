"""
Repository access control service.

This service manages repository access control and validation for the
repository-based access control feature. It provides methods to validate
user access to repositories, filter queries by access permissions, and
generate repository statistics.
"""

from typing import List, Dict, Optional
from datetime import datetime

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.models.repository_config import RepositoryConfig
from app.models.spell import Spell
from app.models.spell_application import SpellApplication
from app.models.user import User


class RepositoryStats(BaseModel):
    """Statistics for a repository."""
    repository_id: int
    repository_name: str
    total_spells: int
    auto_generated_spells: int
    manual_spells: int
    spell_applications: int
    last_spell_created: Optional[datetime]
    last_application: Optional[datetime]


class RepositoryAccessManager:
    """Manages repository access control and validation."""
    
    async def get_user_repositories(self, user_id: int, db: AsyncSession) -> List[RepositoryConfig]:
        """
        Get all repositories owned by a user.
        
        Args:
            user_id: ID of the user
            db: Database session
            
        Returns:
            List of RepositoryConfig objects owned by the user
            
        Validates: Requirements 3.3 - Users can only access repositories they own
        """
        result = await db.execute(
            select(RepositoryConfig)
            .where(RepositoryConfig.user_id == user_id)
            .order_by(RepositoryConfig.repo_name)
        )
        return result.scalars().all()
    
    async def validate_repository_access(self, user_id: int, repository_id: int, db: AsyncSession) -> bool:
        """
        Validate if user has access to a repository.
        
        Args:
            user_id: ID of the user
            repository_id: ID of the repository to check access for
            db: Database session
            
        Returns:
            True if user has access to the repository, False otherwise
            
        Validates: Requirements 2.1, 3.3 - Repository access control
        """
        result = await db.execute(
            select(RepositoryConfig)
            .where(
                and_(
                    RepositoryConfig.id == repository_id,
                    RepositoryConfig.user_id == user_id
                )
            )
        )
        repository = result.scalar_one_or_none()
        return repository is not None
    
    async def filter_spells_by_access(self, user_id: int, query: select, db: AsyncSession) -> select:
        """
        Filter spell query to only include accessible spells.
        
        This method modifies the provided SQLAlchemy select query to add
        repository access filtering based on user ownership.
        
        Args:
            user_id: ID of the user
            query: SQLAlchemy select query to filter
            db: Database session
            
        Returns:
            Modified select query with repository access filtering applied
            
        Validates: Requirements 2.1, 2.2 - Spell access control based on repository ownership
        """
        # Join with repository_configs to filter by user ownership
        # Only include spells from repositories owned by the user
        filtered_query = query.join(
            RepositoryConfig,
            Spell.repository_id == RepositoryConfig.id
        ).where(
            RepositoryConfig.user_id == user_id
        )
        
        return filtered_query
    
    async def get_repository_statistics(self, user_id: int, db: AsyncSession) -> Dict[int, RepositoryStats]:
        """
        Get spell statistics for user's repositories.
        
        Args:
            user_id: ID of the user
            db: Database session
            
        Returns:
            Dictionary mapping repository_id to RepositoryStats objects
            
        Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5 - Repository statistics
        """
        # Get user's repositories with spell counts
        result = await db.execute(
            select(
                RepositoryConfig.id,
                RepositoryConfig.repo_name,
                func.count(Spell.id).label('total_spells'),
                func.sum(
                    case((Spell.auto_generated == 1, 1), else_=0)
                ).label('auto_generated_spells'),
                func.sum(
                    case((Spell.auto_generated == 0, 1), else_=0)
                ).label('manual_spells'),
                func.max(Spell.created_at).label('last_spell_created')
            )
            .select_from(RepositoryConfig)
            .outerjoin(Spell, RepositoryConfig.id == Spell.repository_id)
            .where(RepositoryConfig.user_id == user_id)
            .group_by(RepositoryConfig.id, RepositoryConfig.repo_name)
        )
        
        repository_stats = {}
        
        for row in result:
            # Get spell application counts for this repository
            app_result = await db.execute(
                select(
                    func.count(SpellApplication.id).label('app_count'),
                    func.max(SpellApplication.created_at).label('last_application')
                )
                .select_from(SpellApplication)
                .join(Spell, SpellApplication.spell_id == Spell.id)
                .where(Spell.repository_id == row.id)
            )
            
            app_row = app_result.first()
            app_count = app_row.app_count if app_row else 0
            last_application = app_row.last_application if app_row else None
            
            repository_stats[row.id] = RepositoryStats(
                repository_id=row.id,
                repository_name=row.repo_name,
                total_spells=row.total_spells or 0,
                auto_generated_spells=row.auto_generated_spells or 0,
                manual_spells=row.manual_spells or 0,
                spell_applications=app_count,
                last_spell_created=row.last_spell_created,
                last_application=last_application
            )
        
        return repository_stats
    
    async def get_accessible_repository_ids(self, user_id: int, db: AsyncSession) -> List[int]:
        """
        Get list of repository IDs that the user has access to.
        
        This is a helper method for filtering operations that need just the IDs.
        
        Args:
            user_id: ID of the user
            db: Database session
            
        Returns:
            List of repository IDs accessible to the user
        """
        result = await db.execute(
            select(RepositoryConfig.id)
            .where(RepositoryConfig.user_id == user_id)
        )
        return [row[0] for row in result]
    
    async def validate_spell_repository_access(self, user_id: int, spell_id: int, db: AsyncSession) -> bool:
        """
        Validate if user has access to a spell through repository ownership.
        
        Args:
            user_id: ID of the user
            spell_id: ID of the spell to check access for
            db: Database session
            
        Returns:
            True if user has access to the spell, False otherwise
            
        Validates: Requirements 2.2, 2.4 - Spell access control
        """
        result = await db.execute(
            select(Spell)
            .join(RepositoryConfig, Spell.repository_id == RepositoryConfig.id)
            .where(
                and_(
                    Spell.id == spell_id,
                    RepositoryConfig.user_id == user_id
                )
            )
        )
        spell = result.scalar_one_or_none()
        return spell is not None