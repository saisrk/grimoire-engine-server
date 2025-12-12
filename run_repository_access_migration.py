#!/usr/bin/env python3
"""
Combined migration script for repository-based access control.

This script runs both repository-user and spell-repository association migrations
in the correct order to ensure data integrity.
"""

import asyncio
import logging
import sys
from typing import Dict, Any

from app.db.database import get_db
from migrate_repository_user_associations import RepositoryUserMigration
from migrate_spell_repository_associations import SpellRepositoryMigration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('combined_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def run_combined_migration() -> Dict[str, Any]:
    """
    Run both repository-user and spell-repository migrations.
    
    Returns:
        Combined migration results
    """
    logger.info("Starting combined repository access control migration")
    logger.info("=" * 60)
    
    combined_results = {
        'repository_user_migration': {},
        'spell_repository_migration': {},
        'overall_success': False
    }
    
    # Get database session
    async for db in get_db():
        try:
            # Step 1: Run repository-user association migration
            logger.info("Phase 1: Repository-User Association Migration")
            logger.info("-" * 40)
            
            repo_migration = RepositoryUserMigration(db)
            repo_results = await repo_migration.run_migration()
            combined_results['repository_user_migration'] = repo_results
            
            if repo_results.get('error'):
                logger.error("Repository-user migration failed, aborting spell migration")
                return combined_results
            
            logger.info("Phase 1 completed successfully")
            logger.info("")
            
            # Step 2: Run spell-repository association migration
            logger.info("Phase 2: Spell-Repository Association Migration")
            logger.info("-" * 40)
            
            spell_migration = SpellRepositoryMigration(db)
            spell_results = await spell_migration.run_migration()
            combined_results['spell_repository_migration'] = spell_results
            
            if spell_results.get('error'):
                logger.error("Spell-repository migration failed")
                return combined_results
            
            logger.info("Phase 2 completed successfully")
            logger.info("")
            
            # Mark overall success
            combined_results['overall_success'] = True
            logger.info("Combined migration completed successfully")
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Combined migration failed: {e}", exc_info=True)
            combined_results['error'] = str(e)
            return combined_results
        finally:
            await db.close()


def print_migration_summary(results: Dict[str, Any]):
    """
    Print a comprehensive summary of migration results.
    
    Args:
        results: Combined migration results
    """
    print("\n" + "=" * 60)
    print("REPOSITORY ACCESS CONTROL MIGRATION SUMMARY")
    print("=" * 60)
    
    # Repository-User Migration Results
    print("\n📁 REPOSITORY-USER ASSOCIATION MIGRATION")
    print("-" * 40)
    repo_results = results.get('repository_user_migration', {})
    
    if repo_results:
        print(f"Total Repositories: {repo_results.get('total_repositories', 0)}")
        print(f"Orphaned Repositories: {repo_results.get('orphaned_repositories', 0)}")
        print(f"Successfully Associated: {repo_results.get('associated_repositories', 0)}")
        print(f"Failed Associations: {repo_results.get('failed_associations', 0)}")
        print(f"System User Created: {repo_results.get('system_user_created', False)}")
        
        if repo_results.get('error'):
            print(f"❌ Error: {repo_results['error']}")
        else:
            print("✅ Status: Completed successfully")
    else:
        print("❌ No results available")
    
    # Spell-Repository Migration Results
    print("\n🔮 SPELL-REPOSITORY ASSOCIATION MIGRATION")
    print("-" * 40)
    spell_results = results.get('spell_repository_migration', {})
    
    if spell_results:
        print(f"Total Spells: {spell_results.get('total_spells', 0)}")
        print(f"Orphaned Spells: {spell_results.get('orphaned_spells', 0)}")
        print(f"Successfully Associated: {spell_results.get('associated_spells', 0)}")
        print(f"Failed Associations: {spell_results.get('failed_associations', 0)}")
        print(f"Default Repository Created: {spell_results.get('default_repository_created', False)}")
        print(f"System User Created: {spell_results.get('system_user_created', False)}")
        
        if spell_results.get('error'):
            print(f"❌ Error: {spell_results['error']}")
        else:
            print("✅ Status: Completed successfully")
    else:
        print("❌ No results available")
    
    # Overall Status
    print("\n🎯 OVERALL MIGRATION STATUS")
    print("-" * 40)
    
    if results.get('overall_success'):
        print("✅ Migration completed successfully!")
        print("\n📋 Next Steps:")
        print("   • Verify that all repositories have user associations")
        print("   • Verify that all spells have repository associations")
        print("   • Test repository-based access control functionality")
        print("   • Review migration logs for any warnings")
    else:
        print("❌ Migration completed with errors")
        print("\n🔧 Troubleshooting:")
        print("   • Check migration logs for detailed error information")
        print("   • Verify database connectivity and permissions")
        print("   • Ensure all required models and relationships exist")
        print("   • Consider running individual migration scripts for debugging")
    
    print("\n📄 Log Files:")
    print("   • combined_migration.log - Overall migration log")
    print("   • repository_migration.log - Repository-user migration details")
    print("   • spell_migration.log - Spell-repository migration details")


async def main():
    """
    Main function to run the combined migration.
    """
    print("Repository-Based Access Control Migration")
    print("=" * 60)
    print("This script will migrate existing data to support repository-based access control.")
    print("It will:")
    print("  1. Associate existing repositories with users")
    print("  2. Associate existing spells with repositories")
    print("")
    
    # Confirm before proceeding
    response = input("Do you want to proceed with the migration? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("Migration cancelled by user")
        sys.exit(0)
    
    # Run migration
    results = await run_combined_migration()
    
    # Print summary
    print_migration_summary(results)
    
    # Exit with appropriate code
    if results.get('overall_success'):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())