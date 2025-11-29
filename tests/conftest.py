"""
Pytest configuration and fixtures for Grimoire Engine tests.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.spell import Base


@pytest_asyncio.fixture
async def test_db():
    """
    Create an in-memory SQLite database for testing.
    
    This fixture creates a fresh database for each test and tears it down
    after the test completes.
    """
    # Create in-memory database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Yield session for test
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()
