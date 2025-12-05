"""
Quick test script to verify Mock LLM Service works correctly.
"""

import asyncio
import os

# Set mock provider before importing
os.environ["LLM_PROVIDER"] = "mock"

from app.services.llm_service import get_llm_service


async def test_spell_generation():
    """Test mock spell content generation."""
    print("=" * 60)
    print("Testing Mock LLM - Spell Generation")
    print("=" * 60)
    
    llm = get_llm_service()
    
    error_payload = {
        "error_type": "TypeError",
        "message": "Cannot read property 'length' of undefined",
        "context": "const len = myArray.length;",
        "stack_trace": "TypeError: Cannot read property 'length' of undefined\n  at processData (app.js:42)"
    }
    
    pr_context = {
        "repo": "myorg/myrepo",
        "pr_number": 123,
        "files_changed": ["app.js", "test.js"]
    }
    
    result = await llm.generate_spell_content(error_payload, pr_context)
    
    print("\n✅ Spell Content Generated:")
    print(f"  Title: {result['title']}")
    print(f"  Description: {result['description'][:100]}...")
    print(f"  Solution Code: {result['solution_code'][:100]}...")
    print(f"  Confidence: {result['confidence_score']}")
    print()


async def test_patch_generation():
    """Test mock patch generation."""
    print("=" * 60)
    print("Testing Mock LLM - Patch Generation")
    print("=" * 60)
    
    llm = get_llm_service()
    
    prompt = """You are Kiro — an automated code patch generator.

Context:
- repository: myorg/myrepo
- commit_sha: abc123def456
- language: python
- failing_test: test_user_login

Spell (incantation):
Add null check before accessing user properties

Constraints:
- Limit changes to at most 3 files
- Keep coding style intact

Return:
{"patch": "...git diff...", "files_touched": ["..."], "rationale": "..."}"""
    
    result = await llm.generate_patch(prompt)
    
    print("\n✅ Patch Generated:")
    print(f"  Files Touched: {result['files_touched']}")
    print(f"  Rationale: {result['rationale']}")
    print(f"\n  Patch Preview:")
    print("  " + "\n  ".join(result['patch'].split('\n')[:15]))
    print("  ...")
    print()


async def main():
    """Run all tests."""
    print("\n🚀 Starting Mock LLM Service Tests\n")
    
    await test_spell_generation()
    await test_patch_generation()
    
    print("=" * 60)
    print("✅ All Mock LLM Tests Passed!")
    print("=" * 60)
    print("\nYou can now use the mock LLM for your hackathon demo!")
    print("Just ensure LLM_PROVIDER=mock in your .env file.\n")


if __name__ == "__main__":
    asyncio.run(main())
