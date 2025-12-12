#!/usr/bin/env python3
"""
Migration script to associate existing repository configurations with users.

This script handles the migration of existing repository configurations to the new
repository-based access control system by associating orphaned repositories with users.
"""

import asyncio
import logging
import sys
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.repository_config import RepositoryConfig
from app.models.user import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('repository_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class RepositoryUserMigration:
    """
    Migration service for associating existing repositories with users.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.migration_stats = {
            'total_repositories': 0,
            'orphaned_repositories': 0,
            'associated_repositories': 0,
            'failed_associations': 0,
            'system_user_created': False
        }
    
    async def run_migration(self) -> Dict[str, Any]:
        """
        Run the complete repository-user association migration.
        
        Returns:
            Dictionary with migration statistics and results
        """
        logger.info("Starting repository-user association migration")
        
        try:
            # Step 1: Identify existing repository configurations
            repositories = await self._identify_existing_repositories()
            self.migration_stats['total_repositories'] = len(repositories)
            
            if not repositories:
                logger.info("No repository configurations found - migration not needed")
                return self.migration_stats
            
            # Step 2: Identify orphaned repositories (without user_id)
            orphaned_repos = await self._identify_orphaned_repositories(repositories)
            self.migration_stats['orphaned_repositories'] = len(orphaned_repos)
            
            if not orphaned_repos:
                logger.info("No orphaned repositories found - migration not needed")
                return self.migration_stats
            
            # Step 3: Get or create system user for orphaned repositories
            system_user = await self._get_or_create_system_user()
            if not system_user:
                logger.error("Failed to create system user - migration aborted")
                return self.migration_stats
            
            # Step 4: Associate orphaned repositories with system user
            await self._associate_repositories_with_user(orphaned_repos, system_user.id)
            
            # Step 5: Verify migration results
            await self._verify_migration_results()
            
            logger.info("Repository-user association migration completed successfully")
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"Migration failed with error: {e}", exc_info=True)
            self.migration_stats['error'] = str(e)
            return self.migration_stats
    
    async def _identify_existing_repositories(self) -> List[RepositoryConfig]:
        """
        Identify all existing repository configurations.
        
        Returns:
            List of all repository configurations
        """
        logger.info("Identifying existing repository configurations")
        
        result = await self.db.execute(select(RepositoryConfig))
        repositories = result.scalars().all()
        
        logger.info(f"Found {len(repositories)} repository configurations")
        return list(repositories)
    
    async def _identify_orphaned_repositories(self, repositories: List[RepositoryConfig]) -> List[RepositoryConfig]:
        """
        Identify repositories without user associations.
        
        Args:
            repositories: List of all repository configurations
            
        Returns:
            List of orphaned repository configurations
        """
        logger.info("Identifying orphaned repositories")
        
        orphaned = []
        for repo in repositories:
            if repo.user_id is None:
                orphaned.append(repo)
                logger.info(f"Found orphaned repository: {repo.repo_name} (ID: {repo.id})")
        
        logger.info(f"Found {len(orphaned)} orphaned repositories")
        return orphaned
    
    async def _get_or_create_system_user(self) -> User:
        """
        Get or create a system user for orphaned repositories.
        
        Returns:
            System user instance
        """
        system_username = "system-migration"
        system_email = "system-migration@grimoire.local"
        
        logger.info("Getting or creating system user for orphaned repositories")
        
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
            raise
    
    async def _associate_repositories_with_user(self, repositories: List[RepositoryConfig], user_id: int):
        """
        Associate orphaned repositories with the system user.
        
        Args:
            repositories: List of orphaned repositories
            user_id: ID of the system user
        """
        logger.info(f"Associating {len(repositories)} repositories with user {user_id}")
        
        for repo in repositories:
            try:
                # Update repository to associate with user
                stmt = (
                    update(RepositoryConfig)
                    .where(RepositoryConfig.id == repo.id)
                    .values(user_id=user_id)
                )
                
                await self.db.execute(stmt)
                self.migration_stats['associated_repositories'] += 1
                
                logger.info(f"Associated repository {repo.repo_name} (ID: {repo.id}) with user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to associate repository {repo.repo_name} (ID: {repo.id}): {e}")
                self.migration_stats['failed_associations'] += 1
        
        # Commit all associations
        try:
            await self.db.commit()
            logger.info("Successfully committed repository-user associations")
        except Exception as e:
            logger.error(f"Failed to commit associations: {e}")
            await self.db.rollback()
            raise
    
    async def _verify_migration_results(self):
        """
        Verify that the migration was successful.
        """
        logger.info("Verifying migration results")
        
        # Check for remaining orphaned repositories
        result = await self.db.execute(
            select(RepositoryConfig).where(RepositoryConfig.user_id.is_(None))
        )
        remaining_orphaned = result.scalars().all()
        
        if remaining_orphaned:
            logger.warning(f"Found {len(remaining_orphaned)} repositories still without user associations")
            for repo in remaining_orphaned:
                logger.warning(f"Orphaned repository: {repo.repo_name} (ID: {repo.id})")
        else:
            logger.info("All repositories now have user associations")
        
        # Log final statistics
        logger.info("Migration Statistics:")
        logger.info(f"  Total repositories: {self.migration_stats['total_repositories']}")
        logger.info(f"  Orphaned repositories: {self.migration_stats['orphaned_repositories']}")
        logger.info(f"  Successfully associated: {self.migration_stats['associated_repositories']}")
        logger.info(f"  Failed associations: {self.migration_stats['failed_associations']}")
        logger.info(f"  System user created: {self.migration_stats['system_user_created']}")


async def main():
    """
    Main function to run the repository-user association migration.
    """
    logger.info("Repository-User Association Migration Script")
    logger.info("=" * 50)
    
    # Get database session
    async for db in get_db():
        try:
            # Run migration
            migration = RepositoryUserMigration(db)
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