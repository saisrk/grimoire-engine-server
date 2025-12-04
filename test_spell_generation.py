#!/usr/bin/env python3
"""
Test script for spell auto-generation feature.

This script tests the LLM service and spell generator without requiring
a full webhook setup. Useful for validating configuration and API keys.

Usage:
    python test_spell_generation.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from app.services.llm_service import LLMService
from app.services.spell_generator import SpellGeneratorService
from app.db.database import get_db


async def test_llm_service():
    """Test LLM service with a sample error payload."""
    print("=" * 60)
    print("Testing LLM Service")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Check configuration
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-4-turbo")
    auto_create = os.getenv("AUTO_CREATE_SPELLS", "false")
    
    print(f"\nConfiguration:")
    print(f"  Provider: {provider}")
    print(f"  Model: {model}")
    print(f"  Auto-create enabled: {auto_create}")
    
    # Check API key
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        key_name = "OPENAI_API_KEY"
    else:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        key_name = "ANTHROPIC_API_KEY"
    
    if not api_key or api_key == "your_openai_key_here" or api_key == "your_anthropic_key_here":
        print(f"\n❌ ERROR: {key_name} not configured!")
        print(f"   Please set {key_name} in your .env file")
        return False
    
    print(f"  API Key: {api_key[:10]}...{api_key[-4:]} ✓")
    
    # Initialize LLM service
    print("\n" + "-" * 60)
    print("Initializing LLM Service...")
    llm = LLMService()
    
    # Test error payload
    error_payload = {
        "error_type": "TypeError",
        "message": "Cannot read property 'length' of undefined",
        "context": "const len = myArray.length;"
    }
    
    pr_context = {
        "repo": "test/repo",
        "pr_number": 123,
        "files_changed": ["app/main.js", "tests/test.js"]
    }
    
    print("\nTest Error Payload:")
    print(f"  Type: {error_payload['error_type']}")
    print(f"  Message: {error_payload['message']}")
    print(f"  Context: {error_payload['context']}")
    
    # Generate content
    print("\n" + "-" * 60)
    print("Calling LLM API...")
    print("(This may take 10-30 seconds)")
    
    try:
        content = await llm.generate_spell_content(error_payload, pr_context)
        
        print("\n✅ SUCCESS! Generated content:")
        print(f"\nTitle: {content['title']}")
        print(f"\nDescription:\n{content['description']}")
        print(f"\nSolution Code:\n{content['solution_code']}")
        print(f"\nConfidence Score: {content['confidence_score']}/100")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your API key is valid")
        print("  2. Verify you have API credits/quota")
        print("  3. Check your internet connection")
        print("  4. Review logs for detailed error")
        return False


async def test_spell_generator():
    """Test spell generator with database integration."""
    print("\n" + "=" * 60)
    print("Testing Spell Generator Service")
    print("=" * 60)
    
    # Check if auto-create is enabled
    auto_create = os.getenv("AUTO_CREATE_SPELLS", "false").lower()
    
    if auto_create not in ("true", "1", "yes"):
        print("\n⚠️  AUTO_CREATE_SPELLS is disabled")
        print("   Set AUTO_CREATE_SPELLS=true in .env to test spell creation")
        print("   Skipping database test...")
        return True
    
    print("\nAuto-creation is enabled, testing full flow...")
    
    # Get database session
    async for db in get_db():
        try:
            # Initialize generator
            generator = SpellGeneratorService(db, auto_create_enabled=True)
            
            # Test error payload
            error_payload = {
                "error_type": "TypeError",
                "message": "Cannot read property 'length' of undefined",
                "context": "const len = myArray.length;"
            }
            
            pr_context = {
                "repo": "test/repo",
                "pr_number": 999,
                "files_changed": ["app/main.js"]
            }
            
            print("\nGenerating and creating spell in database...")
            spell_id = await generator.generate_spell(error_payload, pr_context)
            
            if spell_id:
                print(f"\n✅ SUCCESS! Created spell with ID: {spell_id}")
                print("\nYou can view it with:")
                print(f"  curl http://localhost:8000/api/spells/{spell_id}")
                return True
            else:
                print("\n⚠️  Spell generation returned None")
                print("   Check logs for details")
                return False
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Spell Auto-Generation Test Suite")
    print("=" * 60)
    
    # Test 1: LLM Service
    llm_success = await test_llm_service()
    
    # Test 2: Spell Generator (only if LLM works)
    if llm_success:
        generator_success = await test_spell_generator()
    else:
        print("\n⚠️  Skipping spell generator test due to LLM failure")
        generator_success = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"LLM Service: {'✅ PASS' if llm_success else '❌ FAIL'}")
    print(f"Spell Generator: {'✅ PASS' if generator_success else '⚠️  SKIPPED' if not llm_success else '❌ FAIL'}")
    print("=" * 60)
    
    if llm_success and generator_success:
        print("\n🎉 All tests passed! Auto-generation is ready to use.")
        return 0
    elif llm_success:
        print("\n✅ LLM service works! Enable AUTO_CREATE_SPELLS to test full flow.")
        return 0
    else:
        print("\n❌ Tests failed. Please fix configuration and try again.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
