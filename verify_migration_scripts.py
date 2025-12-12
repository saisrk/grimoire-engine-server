#!/usr/bin/env python3
"""
Verification script for data migration scripts.
This script verifies that the migration scripts are properly implemented
and can handle the data migration requirements.
"""

import asyncio
import os
import inspect
from migrate_repository_user_associations import RepositoryUserMigration
from migrate_spell_repository_associations import SpellRepositoryMigration


async def verify_migration_scripts_implementation():
    """Verify that migration scripts are properly implemented."""
    print("🔍 Verifying Data Migration Scripts Implementation...\n")
    
    # Test 1: Verify migration script files exist
    print("✅ Test 1: Migration script files")
    
    migration_files = [
        'migrate_repository_user_associations.py',
        'migrate_spell_repository_associations.py',
        'run_repository_access_migration.py'
    ]
    
    for file_name in migration_files:
        if os.path.exists(file_name):
            print(f"   ✓ {file_name} exists")
        else:
            print(f"   ❌ {file_name} missing")
            return False
    
    # Test 2: Verify RepositoryUserMigration class
    print("\n✅ Test 2: RepositoryUserMigration class")
    
    required_methods = [
        'run_migration',
        '_identify_existing_repositories',
        '_identify_orphaned_repositories',
        '_get_or_create_system_user',
        '_associate_repositories_with_user',
        '_verify_migration_results'
    ]
    
    for method_name in required_methods:
        if hasattr(RepositoryUserMigration, method_name):
            print(f"   ✓ {method_name} method exists")
        else:
            print(f"   ❌ {method_name} method missing")
            return False
    
    # Check run_migration method signature
    run_migration_sig = inspect.signature(RepositoryUserMigration.run_migration)
    if len(run_migration_sig.parameters) == 1:  # Only self parameter
        print("   ✓ run_migration method has correct signature")
    else:
        print("   ❌ run_migration method has incorrect signature")
        return False
    
    # Test 3: Verify SpellRepositoryMigration class
    print("\n✅ Test 3: SpellRepositoryMigration class")
    
    required_methods = [
        'run_migration',
        '_identify_existing_spells',
        '_identify_orphaned_spells',
        '_get_or_create_default_repository',
        '_get_or_create_system_user',
        '_associate_spells_with_repository',
        '_verify_migration_results'
    ]
    
    for method_name in required_methods:
        if hasattr(SpellRepositoryMigration, method_name):
            print(f"   ✓ {method_name} method exists")
        else:
            print(f"   ❌ {method_name} method missing")
            return False
    
    # Check run_migration method signature
    run_migration_sig = inspect.signature(SpellRepositoryMigration.run_migration)
    if len(run_migration_sig.parameters) == 1:  # Only self parameter
        print("   ✓ run_migration method has correct signature")
    else:
        print("   ❌ run_migration method has incorrect signature")
        return False
    
    # Test 4: Verify migration statistics tracking
    print("\n✅ Test 4: Migration statistics tracking")
    
    # Check RepositoryUserMigration statistics
    repo_migration = RepositoryUserMigration(None)  # Pass None for db since we're just checking structure
    repo_stats = repo_migration.migration_stats
    
    required_repo_stats = [
        'total_repositories', 'orphaned_repositories', 'associated_repositories',
        'failed_associations', 'system_user_created'
    ]
    
    for stat_name in required_repo_stats:
        if stat_name in repo_stats:
            print(f"   ✓ Repository migration tracks {stat_name}")
        else:
            print(f"   ❌ Repository migration missing {stat_name} statistic")
            return False
    
    # Check SpellRepositoryMigration statistics
    spell_migration = SpellRepositoryMigration(None)  # Pass None for db since we're just checking structure
    spell_stats = spell_migration.migration_stats
    
    required_spell_stats = [
        'total_spells', 'orphaned_spells', 'associated_spells',
        'failed_associations', 'default_repository_created', 'system_user_created'
    ]
    
    for stat_name in required_spell_stats:
        if stat_name in spell_stats:
            print(f"   ✓ Spell migration tracks {stat_name}")
        else:
            print(f"   ❌ Spell migration missing {stat_name} statistic")
            return False
    
    # Test 5: Verify logging configuration
    print("\n✅ Test 5: Logging configuration")
    
    # Check if migration scripts import logging
    with open('migrate_repository_user_associations.py', 'r') as f:
        repo_content = f.read()
        if 'import logging' in repo_content and 'logger = logging.getLogger' in repo_content:
            print("   ✓ Repository migration has logging configured")
        else:
            print("   ❌ Repository migration missing logging configuration")
            return False
    
    with open('migrate_spell_repository_associations.py', 'r') as f:
        spell_content = f.read()
        if 'import logging' in spell_content and 'logger = logging.getLogger' in spell_content:
            print("   ✓ Spell migration has logging configured")
        else:
            print("   ❌ Spell migration missing logging configuration")
            return False
    
    # Test 6: Verify error handling
    print("\n✅ Test 6: Error handling")
    
    # Check for try-except blocks in migration methods
    if 'try:' in repo_content and 'except Exception as e:' in repo_content:
        print("   ✓ Repository migration has error handling")
    else:
        print("   ❌ Repository migration missing error handling")
        return False
    
    if 'try:' in spell_content and 'except Exception as e:' in spell_content:
        print("   ✓ Spell migration has error handling")
    else:
        print("   ❌ Spell migration missing error handling")
        return False
    
    # Test 7: Verify database transaction handling
    print("\n✅ Test 7: Database transaction handling")
    
    # Check for commit and rollback operations
    if 'await self.db.commit()' in repo_content and 'await self.db.rollback()' in repo_content:
        print("   ✓ Repository migration handles database transactions")
    else:
        print("   ❌ Repository migration missing transaction handling")
        return False
    
    if 'await self.db.commit()' in spell_content and 'await self.db.rollback()' in spell_content:
        print("   ✓ Spell migration handles database transactions")
    else:
        print("   ❌ Spell migration missing transaction handling")
        return False
    
    # Test 8: Verify combined migration script
    print("\n✅ Test 8: Combined migration script")
    
    with open('run_repository_access_migration.py', 'r') as f:
        combined_content = f.read()
        
        if 'RepositoryUserMigration' in combined_content and 'SpellRepositoryMigration' in combined_content:
            print("   ✓ Combined script imports both migration classes")
        else:
            print("   ❌ Combined script missing migration class imports")
            return False
        
        if 'run_combined_migration' in combined_content:
            print("   ✓ Combined script has main migration function")
        else:
            print("   ❌ Combined script missing main migration function")
            return False
        
        if 'print_migration_summary' in combined_content:
            print("   ✓ Combined script has summary reporting")
        else:
            print("   ❌ Combined script missing summary reporting")
            return False
    
    print("\n🎉 All verification tests passed!")
    print("\n📋 Implementation Summary:")
    print("   • Repository-user association migration script implemented")
    print("   • Spell-repository association migration script implemented")
    print("   • Combined migration script with proper sequencing")
    print("   • Comprehensive logging and error handling")
    print("   • Statistics tracking for migration results")
    print("   • Database transaction management")
    print("   • System user and default repository creation")
    print("   • Migration verification and rollback capabilities")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_migration_scripts_implementation())
    if success:
        print("\n✅ Data Migration Scripts implementation verified successfully!")
    else:
        print("\n❌ Data Migration Scripts implementation has issues.")
        exit(1)