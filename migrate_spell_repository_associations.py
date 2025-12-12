#!/usr/bin/env python3
"""
Migration script to associate existing spells with repositories.

This script handles the migration of existing spells to the new repository-based
access control system by associating orphaned spells with repositories.
"""

import asyncio
import logging
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.spell import Spell
from app.models.repository_config import RepositoryConfig
from app.models.user import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spell_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SpellRepositoryMigration:
    """
    Migration service for associating existing spells with repositories.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.migration_stats = {
            'total_spells': 0,
            'orphaned_spells': 0,
            'associated_spells': 0,
            'failed_associations': 0,
            'default_repository_created': False,
            'system_user_created': False
        }
    
    async def run_migration(self) -> Dict[str, Any]:
        """
        Run the complete spell-repository association migration.
        
        Returns:
            Dictionary with migration statistics and results
        """
        logger.info("Starting spell-repository association migration")
        
        try:
            # Step 1: Identify existing spells
            spells = await self._identify_existing_spells()
            self.migration_stats['total_spells'] = len(spells)
            
            if not spells:
                logger.info("No spells found - migration not needed")
                return self.migration_stats
            
            # Step 2: Identify orphaned spells (without repository_id)
            orphaned_spells = await self._identify_orphaned_spells(spells)
            self.migration_stats['orphaned_spells'] = len(orphaned_spells)
            
            if not orphaned_spells:
                logger.info("No orphaned spells found - migration not needed")
                return self.migration_stats
            
            # Step 3: Get or create default repository for orphaned spells
            default_repository = await self._get_or_create_default_repository()
            if not default_repository:
                logger.error("Failed to create default repository - migration aborted")
                return self.migration_stats
            
            # Step 4: Associate orphaned spells with default repository
            await self._associate_spells_with_repository(orphaned_spells, default_repository.id)
            
            # Step 5: Verify migration results
            await self._verify_migration_results()
            
            logger.info("Spell-repository association migration completed successfully")
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"Migration failed with error: {e}", exc_info=True)
            self.migration_stats['error'] = str(e)
            return self.migration_stats
    
    async def _identify_existing_spells(self) -> List[Spell]:
        """
        Identify all existing spells.
        
        Returns:
            List of all spells
        """
        logger.info("Identifying existing spells")
        
        result = await self.db.execute(select(Spell))
        spells = result.scalars().all()
        
        logger.info(f"Found {len(spells)} spells")
        return list(spells)
    
    async def _identify_orphaned_spells(self, spells: List[Spell]) -> List[Spell]:
        """
        Identify spells without repository associations.
        
        Args:
            spells: List of all spells
            
        Returns:
            List of orphaned spells
        """
        logger.info("Identifying orphaned spells")
        
        orphaned = []
        for spell in spells:
            if spell.repository_id is None:
                orphaned.append(spell)
                logger.info(f"Found orphaned spell: {spell.title} (ID: {spell.id})")
        
        logger.info(f"Found {len(orphaned)} orphaned spells")
        return orphaned
    
    async def _get_or_create_default_repository(self) -> Optional[RepositoryConfig]:
        """
        Get or create a default repository for orphaned spells.
        
        Returns:
            Default repository configuration
        """
        default_repo_name = "system/unassigned-spells"
        
        logger.info("Getting or creating default repository for orphaned spells")
        
        # Try to find existing default repository
        result = await self.db.execute(
            select(RepositoryConfig).where(RepositoryConfig.repo_name == default_repo_name)
        )
        default_repo = result.scalar_one_or_none()
        
        if default_repo:
            logger.info(f"Found existing default repository: {default_repo.id}")
            return default_repo
        
        # Get or create system user first
        system_user = await self._get_or_create_system_user()
        if not system_user:
            logger.error("Failed to get system user for default repository")
            return None
        
        # Create default repository
        try:
            default_repo = RepositoryConfig(
                repo_name=default_repo_name,
                webhook_url="https://grimoire.local/system/unassigned",
                enabled=False,  # Disabled since it's not a real repository
                user_id=system_user.id
            )
            
            self.db.add(default_repo)
            await self.db.commit()
            await self.db.refresh(default_repo)
            
            self.migration_stats['default_repository_created'] = True
            logger.info(f"Created default repository: {default_repo.id}")
            return default_repo
            
        except Exception as e:
            logger.error(f"Failed to create default repository: {e}")
            await self.db.rollback()
            return None
    
    async def _get_or_create_system_user(self) -> Optional[User]:
        """
        Get or create a system user for the default repository.
        
        Returns:
            System user instance
        """
        system_username = "system-migration"
        system_email = "system-migration@grimoire.local"
        
        logger.info("Getting or creating system user for default repository")
        
        # Try to find existing system user
        result = await self.db.execute(
            select(User).where(User.username == system_username)
        )
        system_user = result.scalar_one_or_none()
        
        if system_user:
            logger.info(f"Found existing system user: {system_user.id}")
            return system_user
        
        # Create system user
        try:
            system_user = User(
                username=system_username,
                email=system_email,
                hashed_password="system-migration-no-login"  # System user cannot login
            )
            
            self.db.add(system_user)
            await self.db.commit()
            await self.db.refresh(system_user)
            
            self.migration_stats['system_user_created'] = True
            logger.info(f"Created system user: {system_user.id}")
            return system_user
            
        except Exception as e:
            logger.error(f"Failed to create system user: {e}")
            await self.db.rollback()
            return None
    
    async def _associate_spells_with_repository(self, spells: List[Spell], repository_id: int):
        """
        Associate orphaned spells with the default repository.
        
        Args:
            spells: List of orphaned spells
            repository_id: ID of the default repository
        """
        logger.info(f"Associating {len(spells)} spells with repository {repository_id}")
        
        for spell in spells:
            try:
                # Update spell to associate with repository
                stmt = (
                    update(Spell)
                    .where(Spell.id == spell.id)
                    .values(repository_id=repository_id)
                )
                
                await self.db.execute(stmt)
                self.migration_stats['associated_spells'] += 1
                
                logger.info(f"Associated spell {spell.title} (ID: {spell.id}) with repository {repository_id}")
                
            except Exception as e:
                logger.error(f"Failed to associate spell {spell.title} (ID: {spell.id}): {e}")
                self.migration_stats['failed_associations'] += 1
        
        # Commit all associations
        try:
            await self.db.commit()
            logger.info("Successfully committed spell-repository associations")
        except Exception as e:
            logger.error(f"Failed to commit associations: {e}")
            await self.db.rollback()
            raise
    
    async def _verify_migration_results(self):
        """
        Verify that the migration was successful.
        """
        logger.info("Verifying migration results")
        
        # Check for remaining orphaned spells
        result = await self.db.execute(
            select(Spell).where(Spell.repository_id.is_(None))
        )
        remaining_orphaned = result.scalars().all()
        
        if remaining_orphaned:
            logger.warning(f"Found {len(remaining_orphaned)} spells still without repository associations")
            for spell in remaining_orphaned:
                logger.warning(f"Orphaned spell: {spell.title} (ID: {spell.id})")
        else:
            logger.info("All spells now have repository associations")
        
        # Log final statistics
        logger.info("Migration Statistics:")
        logger.info(f"  Total spells: {self.migration_stats['total_spells']}")
        logger.info(f"  Orphaned spells: {self.migration_stats['orphaned_spells']}")
        logger.info(f"  Successfully associated: {self.migration_stats['associated_spells']}")
        logger.info(f"  Failed associations: {self.migration_stats['failed_associations']}")
        logger.info(f"  Default repository created: {self.migration_stats['default_repository_created']}")
        logger.info(f"  System user created: {self.migration_stats['system_user_created']}")


async def main():
    """
    Main function to run the spell-repository association migration.
    """
    logger.info("Spell-Repository Association Migration Script")
    logger.info("=" * 50)
    
    # Get database session
    async for db in get_db():
        try:
            # Run migration
            migration = SpellRepositoryMigration(db)
            results = await migration.run_migration()
            
            # Print results
            print("\n" + "=" * 50)
            print("MIGRATION RESULTS")
            print("=" * 50)
            
            for key, value in results.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
            
            if results.get('error'):
                print("\n❌ Migration completed with errors")
                sys.exit(1)
            else:
                print("\n✅ Migration completed successfully")
                sys.exit(0)
                
        except Exception as e:
            logger.error(f"Migration script failed: {e}", exc_info=True)
            print(f"\n❌ Migration failed: {e}")
            sys.exit(1)
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())