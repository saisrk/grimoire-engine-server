"""
Tests for Spell CRUD API endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import get_db
from app.models.spell import Base


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
async def test_create_spell(async_client):
    """Test creating a new spell."""
    spell_data = {
        "title": "Fix undefined variable",
        "description": "Solution for undefined variable errors",
        "error_type": "NameError",
        "error_pattern": "name '.*' is not defined",
        "solution_code": "# Define the variable before use",
        "tags": "python,variables"
    }
    
    response = await async_client.post("/api/spells", json=spell_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == spell_data["title"]
    assert data["description"] == spell_data["description"]
    assert data["error_type"] == spell_data["error_type"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_spells(async_client):
    """Test listing spells with pagination."""
    # Create a spell first
    spell_data = {
        "title": "Test Spell",
        "description": "Test description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "# test code",
        "tags": "test"
    }
    await async_client.post("/api/spells", json=spell_data)
    
    # List spells
    response = await async_client.get("/api/spells")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == spell_data["title"]


@pytest.mark.asyncio
async def test_get_spell(async_client):
    """Test getting a single spell by ID."""
    # Create a spell first
    spell_data = {
        "title": "Get Test Spell",
        "description": "Test description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "# test code",
        "tags": "test"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # Get the spell
    response = await async_client.get(f"/api/spells/{spell_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == spell_id
    assert data["title"] == spell_data["title"]


@pytest.mark.asyncio
async def test_get_spell_not_found(async_client):
    """Test getting a non-existent spell returns 404."""
    response = await async_client.get("/api/spells/99999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_update_spell(async_client):
    """Test updating an existing spell."""
    # Create a spell first
    spell_data = {
        "title": "Original Title",
        "description": "Original description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "# test code",
        "tags": "test"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # Update the spell
    updated_data = {
        "title": "Updated Title",
        "description": "Updated description",
        "error_type": "UpdatedError",
        "error_pattern": "updated pattern",
        "solution_code": "# updated code",
        "tags": "updated"
    }
    response = await async_client.put(f"/api/spells/{spell_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == spell_id
    assert data["title"] == updated_data["title"]
    assert data["description"] == updated_data["description"]


@pytest.mark.asyncio
async def test_update_spell_not_found(async_client):
    """Test updating a non-existent spell returns 404."""
    updated_data = {
        "title": "Updated Title",
        "description": "Updated description",
        "error_type": "UpdatedError",
        "error_pattern": "updated pattern",
        "solution_code": "# updated code",
        "tags": "updated"
    }
    response = await async_client.put("/api/spells/99999", json=updated_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_spell(async_client):
    """Test deleting a spell."""
    # Create a spell first
    spell_data = {
        "title": "Delete Test Spell",
        "description": "Test description",
        "error_type": "TestError",
        "error_pattern": "test pattern",
        "solution_code": "# test code",
        "tags": "test"
    }
    create_response = await async_client.post("/api/spells", json=spell_data)
    spell_id = create_response.json()["id"]
    
    # Delete the spell
    response = await async_client.delete(f"/api/spells/{spell_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = await async_client.get(f"/api/spells/{spell_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_spell_not_found(async_client):
    """Test deleting a non-existent spell returns 404."""
    response = await async_client.delete("/api/spells/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pagination(async_client):
    """Test pagination parameters work correctly."""
    # Create multiple spells
    for i in range(5):
        spell_data = {
            "title": f"Spell {i}",
            "description": f"Description {i}",
            "error_type": "TestError",
            "error_pattern": "test pattern",
            "solution_code": "# test code",
            "tags": "test"
        }
        await async_client.post("/api/spells", json=spell_data)
    
    # Test skip and limit
    response = await async_client.get("/api/spells?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
