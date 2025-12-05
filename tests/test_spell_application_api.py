"""
Tests for Spell Application API endpoint.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import get_db
from app.models.spell import Base
from app.models.spell_application import PatchResult


# Create in-memory test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Override database dependency for testing."""
    async with test_session_maker() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def async_client():
    """Create async test client."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_apply_spell_success(async_client):
    """Test successfully applying a spell to generate a patch."""
    # Create a spell first
    spell_data = {
        "title": "Fix undefined variable",
        "description": "Solution for undefined variable errors",
        "error_type": "NameError",
        "error_pattern": "name '.*' is not defined",
        "solution_code": "diff --git a/app/main.py b/app/main.py\n--- a/app/main.py\n+++ b/app/main.py\n@@ -1,1 +1,2 @@\n+x = 10\n print(x)",
        "tags": "python,variables"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # Mock the patch generator to return a valid patch
    mock_patch_result = PatchResult(
        patch="diff --git a/app/main.py b/app/main.py\n--- a/app/main.py\n+++ b/app/main.py\n@@ -1,1 +1,2 @@\n+x = 10\n print(x)",
        files_touched=["app/main.py"],
        rationale="Added variable definition before use"
    )
    
    with patch('app.services.patch_generator.PatchGeneratorService.generate_patch', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_patch_result
        
        # Apply the spell
        application_request = {
            "failing_context": {
                "repository": "myorg/myrepo",
                "commit_sha": "abc123def",
                "language": "python",
                "version": "3.11",
                "failing_test": "test_main",
                "stack_trace": "NameError: name 'x' is not defined"
            },
            "adaptation_constraints": {
                "max_files": 3,
                "excluded_patterns": ["package.json"],
                "preserve_style": True
            }
        }
        
        response = await async_client.post(f"/api/spells/{spell_id}/apply", json=application_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "application_id" in data
        assert data["patch"] == mock_patch_result.patch
        assert data["files_touched"] == mock_patch_result.files_touched
        assert data["rationale"] == mock_patch_result.rationale
        assert "created_at" in data


@pytest.mark.asyncio
async def test_apply_spell_not_found(async_client):
    """Test applying a non-existent spell returns 404."""
    application_request = {
        "failing_context": {
            "repository": "myorg/myrepo",
            "commit_sha": "abc123def"
        }
    }
    
    response = await async_client.post("/api/spells/99999/apply", json=application_request)
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_apply_spell_validation_error(async_client):
    """Test applying a spell with validation error returns 422."""
    # Create a spell first
    spell_data = {
        "title": "Test Spell",
        "description": "Test description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "# test code",
        "tags": "test"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # Mock the patch generator to raise a ValueError
    with patch('app.services.patch_generator.PatchGeneratorService.generate_patch', new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = ValueError("Patch validation failed: invalid format")
        
        application_request = {
            "failing_context": {
                "repository": "myorg/myrepo",
                "commit_sha": "abc123def"
            }
        }
        
        response = await async_client.post(f"/api/spells/{spell_id}/apply", json=application_request)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation failed" in data["detail"].lower()


@pytest.mark.asyncio
async def test_apply_spell_default_constraints(async_client):
    """Test applying a spell without constraints uses defaults."""
    # Create a spell first
    spell_data = {
        "title": "Test Spell",
        "description": "Test description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "diff --git a/test.py b/test.py\n--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-# old\n+# new",
        "tags": "test"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # Mock the patch generator
    mock_patch_result = PatchResult(
        patch="diff --git a/test.py b/test.py\n--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-# old\n+# new",
        files_touched=["test.py"],
        rationale="Updated comment"
    )
    
    with patch('app.services.patch_generator.PatchGeneratorService.generate_patch', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_patch_result
        
        # Apply without constraints
        application_request = {
            "failing_context": {
                "repository": "myorg/myrepo",
                "commit_sha": "abc123def"
            }
        }
        
        response = await async_client.post(f"/api/spells/{spell_id}/apply", json=application_request)
        
        assert response.status_code == 200
        # Verify default constraints were used
        call_args = mock_generate.call_args
        constraints = call_args.kwargs['constraints']
        assert constraints.max_files == 3  # Default value
        assert constraints.preserve_style is True  # Default value


@pytest.mark.asyncio
async def test_list_spell_applications_empty(async_client):
    """Test listing applications for a spell with no applications returns empty list."""
    # Create a spell
    spell_data = {
        "title": "Test Spell",
        "description": "Test description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "# test code",
        "tags": "test"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # List applications
    response = await async_client.get(f"/api/spells/{spell_id}/applications")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_spell_applications_with_data(async_client):
    """Test listing applications returns all applications for a spell."""
    # Create a spell
    spell_data = {
        "title": "Test Spell",
        "description": "Test description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "diff --git a/test.py b/test.py\n--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-# old\n+# new",
        "tags": "test"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # Mock the patch generator
    mock_patch_result = PatchResult(
        patch="diff --git a/test.py b/test.py\n--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-# old\n+# new",
        files_touched=["test.py", "test2.py"],
        rationale="Updated files"
    )
    
    with patch('app.services.patch_generator.PatchGeneratorService.generate_patch', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_patch_result
        
        # Apply the spell multiple times
        for i in range(3):
            application_request = {
                "failing_context": {
                    "repository": f"myorg/repo{i}",
                    "commit_sha": f"abc{i}23def"
                }
            }
            await async_client.post(f"/api/spells/{spell_id}/apply", json=application_request)
    
    # List applications
    response = await async_client.get(f"/api/spells/{spell_id}/applications")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    
    # Verify structure of each application summary
    for app in data:
        assert "id" in app
        assert "spell_id" in app
        assert app["spell_id"] == spell_id
        assert "repository" in app
        assert "commit_sha" in app
        assert "files_touched" in app
        assert isinstance(app["files_touched"], list)
        assert len(app["files_touched"]) == 2
        assert "created_at" in app
    
    # Verify all repositories are present (order may vary due to same timestamps)
    repositories = [app["repository"] for app in data]
    assert set(repositories) == {"myorg/repo0", "myorg/repo1", "myorg/repo2"}


@pytest.mark.asyncio
async def test_list_spell_applications_pagination(async_client):
    """Test pagination works correctly for spell applications."""
    # Create a spell
    spell_data = {
        "title": "Test Spell",
        "description": "Test description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "diff --git a/test.py b/test.py\n--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-# old\n+# new",
        "tags": "test"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # Mock the patch generator
    mock_patch_result = PatchResult(
        patch="diff --git a/test.py b/test.py\n--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-# old\n+# new",
        files_touched=["test.py"],
        rationale="Updated file"
    )
    
    with patch('app.services.patch_generator.PatchGeneratorService.generate_patch', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_patch_result
        
        # Apply the spell 5 times
        for i in range(5):
            application_request = {
                "failing_context": {
                    "repository": f"myorg/repo{i}",
                    "commit_sha": f"abc{i}23def"
                }
            }
            await async_client.post(f"/api/spells/{spell_id}/apply", json=application_request)
    
    # Test pagination - get first 2
    response = await async_client.get(f"/api/spells/{spell_id}/applications?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Verify they are from our set of repositories
    repos_page1 = {app["repository"] for app in data}
    assert repos_page1.issubset({"myorg/repo0", "myorg/repo1", "myorg/repo2", "myorg/repo3", "myorg/repo4"})
    
    # Test pagination - get next 2
    response = await async_client.get(f"/api/spells/{spell_id}/applications?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    repos_page2 = {app["repository"] for app in data}
    assert repos_page2.issubset({"myorg/repo0", "myorg/repo1", "myorg/repo2", "myorg/repo3", "myorg/repo4"})
    
    # Test pagination - get last 1
    response = await async_client.get(f"/api/spells/{spell_id}/applications?skip=4&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    repos_page3 = {app["repository"] for app in data}
    assert repos_page3.issubset({"myorg/repo0", "myorg/repo1", "myorg/repo2", "myorg/repo3", "myorg/repo4"})
    
    # Verify no overlap between pages (pagination is working)
    assert len(repos_page1 & repos_page2) == 0  # No overlap between page 1 and 2
    assert len(repos_page1 & repos_page3) == 0  # No overlap between page 1 and 3
    assert len(repos_page2 & repos_page3) == 0  # No overlap between page 2 and 3
    
    # Verify all repositories are covered
    all_repos = repos_page1 | repos_page2 | repos_page3
    assert all_repos == {"myorg/repo0", "myorg/repo1", "myorg/repo2", "myorg/repo3", "myorg/repo4"}
