"""
Database configuration and session management.

This module provides async SQLAlchemy engine and session factory
for the Grimoire Engine backend. It uses SQLite with aiosqlite driver
for async database operations.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

# Get database URL from environment variable or use default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./grimoire.db")

# Create async engine
# echo=True logs SQL statements (useful for development)
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
)

# Create async session factory
# expire_on_commit=False prevents SQLAlchemy from expiring objects after commit
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    
    This function creates a new async database session for each request
    and ensures it's properly closed after the request completes.
    
    Yields:
        AsyncSession: Database session for the request
        
    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
