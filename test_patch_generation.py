"""
Test script for patch generation feature.

This script tests the LLM service's generate_patch method.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import LLMService


async def test_generate_patch():
    """Test LLM service patch generation."""
    print("\n" + "=" * 60)
    print("Testing LLM Service - Patch Generation")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Initialize LLM service
    llm = LLMService()
    
    print(f"\nProvider: {llm.provider}")
    print(f"Model: {llm.model}")
    print(f"API Key configured: {'Yes' if llm.api_key else 'No'}")
    
    if not llm.api_key:
        print("\n❌ No API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return False
    
    # Create a test prompt
    prompt = """You are Kiro — an automated code patch generator. You will be given:
(1) failing context (stack trace, failing test name, repo language & version)
(2) a canonical spell incantation (git diff)
(3) adaptation constraints

Produce a git unified diff that applies to the repository at commit SHA: abc123.

Do not output anything other than: a JSON object with keys "patch" (string with unified git diff), "files_touched" (list of paths), and "rationale" (short, 1-2 lines).

Do NOT include explanations outside the JSON. If unable, return {"error": "..."}.

Context:
- language: python
- version: 3.9
- failing_test: test_user_creation
- stack: TypeError: 'NoneType' object is not subscriptable at line 42
- repo_commit: abc123

Spell (incantation):
diff --git a/app/models/user.py b/app/models/user.py
--- a/app/models/user.py
+++ b/app/models/user.py
@@ -10,7 +10,7 @@ class User:
     def create(self, data):
-        return data['name']
+        return data.get('name', 'Anonymous')

Constraints:
- Limit changes to at most 3 files
- Keep coding style intact
- Do not change package.json, *.lock

Return:
{"patch": "...git diff...", "files_touched": ["..."], "rationale": "..."}
"""
    
    try:
        print("\n📤 Sending patch generation request...")
        result = await llm.generate_patch(prompt, timeout=30)
        
        if "error" in result:
            print(f"\n❌ Patch generation returned error: {result['error']}")
            return False
        
        print("\n✅ Patch generated successfully!")
        print(f"\nFiles touched: {result.get('files_touched', [])}")
        print(f"Rationale: {result.get('rationale', 'N/A')}")
        print(f"\nPatch preview (first 200 chars):")
        patch = result.get('patch', '')
        print(patch[:200] + "..." if len(patch) > 200 else patch)
        
        # Validate response structure
        required_fields = ['patch', 'files_touched', 'rationale']
        missing_fields = [f for f in required_fields if f not in result]
        
        if missing_fields:
            print(f"\n⚠️  Warning: Missing fields in response: {missing_fields}")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during patch generation: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PATCH GENERATION TEST SUITE")
    print("=" * 60)
    
    # Test patch generation
    success = await test_generate_patch()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
