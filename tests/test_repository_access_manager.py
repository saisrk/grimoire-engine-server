"""
Tests for Repository Access Manager Service.

Tests the repository access control functionality including user repository
access validation, spell filtering, and repository statistics.
"""

import pytest
from sqlalchemy import select

from app.models.user import User
from app.models.repository_config import RepositoryConfig
from app.models.spell import Spell
from app.services.repository_access_manager import RepositoryAccessManager


@pytest.mark.asyncio
class TestRepositoryAccessManager:
    """Test suite for RepositoryAccessManager."""
    
    async def test_get_user_repositories(self, test_db):
        """Test getting repositories owned by a user."""
        # Create test users
        user1 = User(email="user1@example.com", hashed_password="hash1", is_active=True)
        user2 = User(email="user2@example.com", hashed_password="hash2", is_active=True)
        test_db.add_all([user1, user2])
        await test_db.commit()
        await test_db.refresh(user1)
        await test_db.refresh(user2)
        
        # Create repositories for different users
        repo1 = RepositoryConfig(
            repo_name="user1/repo1",
            webhook_url="https://example.com/webhook1",
            enabled=True,
            user_id=user1.id
        )
        repo2 = RepositoryConfig(
            repo_name="user1/repo2",
            webhook_url="https://example.com/webhook2",
            enabled=True,
            user_id=user1.id
        )
        repo3 = RepositoryConfig(
            repo_name="user2/repo1",
            webhook_url="https://example.com/webhook3",
            enabled=True,
            user_id=user2.id
        )
        test_db.add_all([repo1, repo2, repo3])
        await test_db.commit()
        
        # Test getting repositories for user1
        manager = RepositoryAccessManager()
        user1_repos = await manager.get_user_repositories(user1.id, test_db)
        
        assert len(user1_repos) == 2
        repo_names = [repo.repo_name for repo in user1_repos]
        assert "user1/repo1" in repo_names
        assert "user1/repo2" in repo_names
        assert "user2/repo1" not in repo_names
        
        # Test getting repositories for user2
        user2_repos = await manager.get_user_repositories(user2.id, test_db)
        
        assert len(user2_repos) == 1
        assert user2_repos[0].repo_name == "user2/repo1"
    
    async def test_validate_repository_access(self, test_db):
        """Test validating user access to repositories."""
        # Create test user
        user = User(email="user@example.com", hashed_password="hash", is_active=True)
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Create repository owned by user
        repo = RepositoryConfig(
            repo_name="user/repo",
            webhook_url="https://example.com/webhook",
            enabled=True,
            user_id=user.id
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        manager = RepositoryAccessManager()
        
        # Test valid access
        has_access = await manager.validate_repository_access(user.id, repo.id, test_db)
        assert has_access is True
        
        # Test invalid access (non-existent repository)
        has_access = await manager.validate_repository_access(user.id, 999, test_db)
        assert has_access is False
        
        # Test invalid access (different user)
        other_user = User(email="other@example.com", hashed_password="hash2", is_active=True)
        test_db.add(other_user)
        await test_db.commit()
        await test_db.refresh(other_user)
        
        has_access = await manager.validate_repository_access(other_user.id, repo.id, test_db)
        assert has_access is False
    
    async def test_filter_spells_by_access(self, test_db):
        """Test filtering spell queries by repository access."""
        # Create test users
        user1 = User(email="user1@example.com", hashed_password="hash1", is_active=True)
        user2 = User(email="user2@example.com", hashed_password="hash2", is_active=True)
        test_db.add_all([user1, user2])
        await test_db.commit()
        await test_db.refresh(user1)
        await test_db.refresh(user2)
        
        # Create repositories
        repo1 = RepositoryConfig(
            repo_name="user1/repo1",
            webhook_url="https://example.com/webhook1",
            enabled=True,
            user_id=user1.id
        )
        repo2 = RepositoryConfig(
            repo_name="user2/repo1",
            webhook_url="https://example.com/webhook2",
            enabled=True,
            user_id=user2.id
        )
        test_db.add_all([repo1, repo2])
        await test_db.commit()
        await test_db.refresh(repo1)
        await test_db.refresh(repo2)
        
        # Create spells in different repositories
        spell1 = Spell(
            title="Spell 1",
            description="Description 1",
            error_type="TypeError",
            error_pattern="error1",
            solution_code="fix1",
            repository_id=repo1.id
        )
        spell2 = Spell(
            title="Spell 2",
            description="Description 2",
            error_type="SyntaxError",
            error_pattern="error2",
            solution_code="fix2",
            repository_id=repo2.id
        )
        test_db.add_all([spell1, spell2])
        await test_db.commit()
        
        manager = RepositoryAccessManager()
        
        # Test filtering for user1 - should only see spell1
        base_query = select(Spell)
        filtered_query = await manager.filter_spells_by_access(user1.id, base_query, test_db)
        result = await test_db.execute(filtered_query)
        user1_spells = result.scalars().all()
        
        assert len(user1_spells) == 1
        assert user1_spells[0].id == spell1.id
        
        # Test filtering for user2 - should only see spell2
        filtered_query = await manager.filter_spells_by_access(user2.id, base_query, test_db)
        result = await test_db.execute(filtered_query)
        user2_spells = result.scalars().all()
        
        assert len(user2_spells) == 1
        assert user2_spells[0].id == spell2.id
    
    async def test_get_accessible_repository_ids(self, test_db):
        """Test getting list of accessible repository IDs."""
        # Create test user
        user = User(email="user@example.com", hashed_password="hash", is_active=True)
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Create repositories
        repo1 = RepositoryConfig(
            repo_name="user/repo1",
            webhook_url="https://example.com/webhook1",
            enabled=True,
            user_id=user.id
        )
        repo2 = RepositoryConfig(
            repo_name="user/repo2",
            webhook_url="https://example.com/webhook2",
            enabled=True,
            user_id=user.id
        )
        test_db.add_all([repo1, repo2])
        await test_db.commit()
        await test_db.refresh(repo1)
        await test_db.refresh(repo2)
        
        manager = RepositoryAccessManager()
        repo_ids = await manager.get_accessible_repository_ids(user.id, test_db)
        
        assert len(repo_ids) == 2
        assert repo1.id in repo_ids
        assert repo2.id in repo_ids
    
    async def test_validate_spell_repository_access(self, test_db):
        """Test validating user access to spells through repository ownership."""
        # Create test users
        user1 = User(email="user1@example.com", hashed_password="hash1", is_active=True)
        user2 = User(email="user2@example.com", hashed_password="hash2", is_active=True)
        test_db.add_all([user1, user2])
        await test_db.commit()
        await test_db.refresh(user1)
        await test_db.refresh(user2)
        
        # Create repository owned by user1
        repo = RepositoryConfig(
            repo_name="user1/repo",
            webhook_url="https://example.com/webhook",
            enabled=True,
            user_id=user1.id
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        # Create spell in user1's repository
        spell = Spell(
            title="Test Spell",
            description="Test Description",
            error_type="TypeError",
            error_pattern="error",
            solution_code="fix",
            repository_id=repo.id
        )
        test_db.add(spell)
        await test_db.commit()
        await test_db.refresh(spell)
        
        manager = RepositoryAccessManager()
        
        # Test valid access (user1 owns the repository)
        has_access = await manager.validate_spell_repository_access(user1.id, spell.id, test_db)
        assert has_access is True
        
        # Test invalid access (user2 doesn't own the repository)
        has_access = await manager.validate_spell_repository_access(user2.id, spell.id, test_db)
        assert has_access is False
        
        # Test invalid access (non-existent spell)
        has_access = await manager.validate_spell_repository_access(user1.id, 999, test_db)
        assert has_access is False
    
    async def test_get_repository_statistics(self, test_db):
        """Test getting repository statistics."""
        # Create test user
        user = User(email="user@example.com", hashed_password="hash", is_active=True)
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Create repository
        repo = RepositoryConfig(
            repo_name="user/repo",
            webhook_url="https://example.com/webhook",
            enabled=True,
            user_id=user.id
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        # Create spells with different types
        spell1 = Spell(
            title="Auto Spell",
            description="Auto generated",
            error_type="TypeError",
            error_pattern="error1",
            solution_code="fix1",
            repository_id=repo.id,
            auto_generated=1
        )
        spell2 = Spell(
            title="Manual Spell",
            description="Manually created",
            error_type="SyntaxError",
            error_pattern="error2",
            solution_code="fix2",
            repository_id=repo.id,
            auto_generated=0
        )
        test_db.add_all([spell1, spell2])
        await test_db.commit()
        
        manager = RepositoryAccessManager()
        stats = await manager.get_repository_statistics(user.id, test_db)
        
        assert repo.id in stats
        repo_stats = stats[repo.id]
        
        assert repo_stats.repository_id == repo.id
        assert repo_stats.repository_name == "user/repo"
        assert repo_stats.total_spells == 2
        assert repo_stats.auto_generated_spells == 1
        assert repo_stats.manual_spells == 1
        assert repo_stats.spell_applications == 0  # No applications yet
        assert repo_stats.last_spell_created is not None
    
    async def test_get_repository_statistics_empty_repository(self, test_db):
        """Test repository statistics for repository with no spells."""
        # Create test user
        user = User(email="user@example.com", hashed_password="hash", is_active=True)
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        # Create empty repository
        repo = RepositoryConfig(
            repo_name="user/empty-repo",
            webhook_url="https://example.com/webhook",
            enabled=True,
            user_id=user.id
        )
        test_db.add(repo)
        await test_db.commit()
        await test_db.refresh(repo)
        
        manager = RepositoryAccessManager()
        stats = await manager.get_repository_statistics(user.id, test_db)
        
        assert repo.id in stats
        repo_stats = stats[repo.id]
        
        assert repo_stats.repository_id == repo.id
        assert repo_stats.repository_name == "user/empty-repo"
        assert repo_stats.total_spells == 0
        assert repo_stats.auto_generated_spells == 0
        assert repo_stats.manual_spells == 0
        assert repo_stats.spell_applications == 0
        assert repo_stats.last_spell_created is None