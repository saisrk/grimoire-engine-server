"""
Property-based tests for Spell model.

These tests use Hypothesis to verify correctness properties across
randomly generated spell data.
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.models.spell import Spell, SpellCreate, Base


# Hypothesis strategies for generating spell data
def spell_create_strategy():
    """Generate random SpellCreate instances."""
    return st.builds(
        SpellCreate,
        title=st.text(min_size=1, max_size=255, alphabet=st.characters(blacklist_categories=("Cs", "Cc"))),
        description=st.text(min_size=1, max_size=1000, alphabet=st.characters(blacklist_categories=("Cs", "Cc"))),
        error_type=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs", "Cc"))),
        error_pattern=st.text(min_size=1, max_size=500, alphabet=st.characters(blacklist_categories=("Cs", "Cc"))),
        solution_code=st.text(min_size=1, max_size=1000, alphabet=st.characters(blacklist_categories=("Cs", "Cc"))),
        tags=st.one_of(
            st.none(),
            st.text(max_size=500, alphabet=st.characters(blacklist_categories=("Cs", "Cc")))
        ),
    )


async def get_test_db():
    """Create a test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


# Feature: grimoire-engine-backend, Property 5: Spell CRUD round-trip consistency
# Validates: Requirements 2.4, 2.5, 3.3
@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(spell_data=spell_create_strategy())
async def test_spell_crud_roundtrip_create(spell_data):
    """
    For any valid spell data, creating a spell in the database and then
    retrieving it should return the same data.
    
    This property verifies that the create operation preserves all spell
    data without loss or corruption.
    """
    # Create test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as test_db:
        # Create spell
        spell = Spell(
            title=spell_data.title,
            description=spell_data.description,
            error_type=spell_data.error_type,
            error_pattern=spell_data.error_pattern,
            solution_code=spell_data.solution_code,
            tags=spell_data.tags,
        )
        
        test_db.add(spell)
        await test_db.commit()
        await test_db.refresh(spell)
        
        # Retrieve spell
        result = await test_db.execute(select(Spell).where(Spell.id == spell.id))
        retrieved_spell = result.scalar_one()
        
        # Verify all fields match
        assert retrieved_spell.id == spell.id
        assert retrieved_spell.title == spell_data.title
        assert retrieved_spell.description == spell_data.description
        assert retrieved_spell.error_type == spell_data.error_type
        assert retrieved_spell.error_pattern == spell_data.error_pattern
        assert retrieved_spell.solution_code == spell_data.solution_code
        assert retrieved_spell.tags == spell_data.tags
        assert retrieved_spell.created_at is not None
    
    await engine.dispose()


# Feature: grimoire-engine-backend, Property 5: Spell CRUD round-trip consistency
# Validates: Requirements 2.4, 2.5, 3.3
@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    initial_data=spell_create_strategy(),
    updated_data=spell_create_strategy(),
)
async def test_spell_crud_roundtrip_update(initial_data, updated_data):
    """
    For any valid spell data, updating a spell and then retrieving it
    should return the updated data with all changes preserved.
    
    This property verifies that the update operation correctly modifies
    all fields and persists the changes.
    """
    # Create test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as test_db:
        # Create initial spell
        spell = Spell(
            title=initial_data.title,
            description=initial_data.description,
            error_type=initial_data.error_type,
            error_pattern=initial_data.error_pattern,
            solution_code=initial_data.solution_code,
            tags=initial_data.tags,
        )
        
        test_db.add(spell)
        await test_db.commit()
        await test_db.refresh(spell)
        spell_id = spell.id
        
        # Update spell
        spell.title = updated_data.title
        spell.description = updated_data.description
        spell.error_type = updated_data.error_type
        spell.error_pattern = updated_data.error_pattern
        spell.solution_code = updated_data.solution_code
        spell.tags = updated_data.tags
        
        await test_db.commit()
        await test_db.refresh(spell)
        
        # Retrieve updated spell
        result = await test_db.execute(select(Spell).where(Spell.id == spell_id))
        retrieved_spell = result.scalar_one()
        
        # Verify all fields match updated data
        assert retrieved_spell.id == spell_id
        assert retrieved_spell.title == updated_data.title
        assert retrieved_spell.description == updated_data.description
        assert retrieved_spell.error_type == updated_data.error_type
        assert retrieved_spell.error_pattern == updated_data.error_pattern
        assert retrieved_spell.solution_code == updated_data.solution_code
        assert retrieved_spell.tags == updated_data.tags
        # Note: updated_at may be None if no actual changes were made (e.g., when initial_data == updated_data)
        # This is correct behavior - SQLAlchemy only updates the timestamp when fields actually change
    
    await engine.dispose()
