#!/usr/bin/env python3
"""Quick test to verify migration was successful."""

import asyncio
import sys
from app.db.database import get_db
from app.models.spell import Spell
from sqlalchemy import select


async def test_schema():
    """Test that new columns exist and work."""
    print("Testing spell schema with new auto-generation fields...")
    
    async for db in get_db():
        try:
            # Try to query with new fields
            result = await db.execute(
                select(
                    Spell.id,
                    Spell.title,
                    Spell.auto_generated,
                    Spell.confidence_score,
                    Spell.human_reviewed
                ).limit(1)
            )
            
            print("✅ Schema query successful!")
            print("   New fields are accessible:")
            print("   - auto_generated")
            print("   - confidence_score")
            print("   - human_reviewed")
            
            # Try to create a test spell with new fields
            test_spell = Spell(
                title="Test Auto-Generated Spell",
                description="Test description",
                error_type="TestError",
                error_pattern="test.*pattern",
                solution_code="# test solution",
                tags="test,auto-generated",
                auto_generated=1,
                confidence_score=85,
                human_reviewed=0
            )
            
            db.add(test_spell)
            await db.commit()
            await db.refresh(test_spell)
            
            print(f"\n✅ Test spell created successfully!")
            print(f"   ID: {test_spell.id}")
            print(f"   Auto-generated: {test_spell.auto_generated}")
            print(f"   Confidence: {test_spell.confidence_score}")
            print(f"   Reviewed: {test_spell.human_reviewed}")
            
            # Clean up test spell
            await db.delete(test_spell)
            await db.commit()
            print("\n✅ Test spell cleaned up")
            
            print("\n🎉 Migration successful! Schema is ready for auto-generation.")
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            break
    
    return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_schema())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        sys.exit(0)
