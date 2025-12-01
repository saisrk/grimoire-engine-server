"""
Pytest configuration and fixtures for Grimoire Engine tests.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
# Import models to register them with Base metadata
from app.models.spell import Spell
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password


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


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def test_db():
    """
    Create an in-memory SQLite database for testing.
    
    This fixture creates a fresh database for each test and tears it down
    after the test completes.
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Yield session for test
    async with test_session_maker() as session:
        yield session
    
    # Drop all tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_db):
    """
    Alias for test_db fixture for consistency with auth tests.
    """
    return test_db


@pytest_asyncio.fixture
async def client():
    """
    Create async HTTP client for testing API endpoints.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(test_db):
    """
    Create a test user in the database.
    """
    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=True
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """
    Create authentication headers with a valid token for the test user.
    """
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}
