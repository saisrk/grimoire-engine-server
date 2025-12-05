"""
Test the spell application endpoint with Mock LLM.
Run this after starting the server to verify everything works.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_spell_apply():
    """Test applying a spell with mock LLM."""
    print("=" * 60)
    print("Testing Spell Application with Mock LLM")
    print("=" * 60)
    
    # First, get or create a spell
    print("\n1. Getting spells...")
    response = requests.get(f"{BASE_URL}/api/spells")
    
    if response.status_code != 200:
        print(f"❌ Failed to get spells: {response.status_code}")
        return
    
    spells = response.json()
    
    if not spells:
        print("No spells found. Creating a test spell...")
        
        # Create a test spell
        spell_data = {
            "title": "Fix Null Reference Error",
            "description": "Add null checks before accessing object properties",
            "error_type": "NullReferenceError",
            "error_pattern": "Cannot read property .* of null",
            "solution_code": "if (obj !== null) { return obj.property; }",
            "tags": "javascript,null-check"
        }
        
        response = requests.post(f"{BASE_URL}/api/spells", json=spell_data)
        
        if response.status_code != 201:
            print(f"❌ Failed to create spell: {response.status_code}")
            print(response.text)
            return
        
        spell = response.json()
        spell_id = spell["id"]
        print(f"✅ Created spell with ID: {spell_id}")
    else:
        spell_id = spells[0]["id"]
        print(f"✅ Using existing spell with ID: {spell_id}")
    
    # Apply the spell
    print(f"\n2. Applying spell {spell_id}...")
    
    application_request = {
        "failing_context": {
            "repository": "myorg/demo-repo",
            "commit_sha": "abc123def456",
            "language": "python",
            "version": "3.11",
            "failing_test": "test_user_authentication",
            "stack_trace": "AssertionError: Expected user object but got None"
        },
        "adaptation_constraints": {
            "max_files": 3,
            "excluded_patterns": ["*.lock", "package.json"],
            "preserve_style": True
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/spells/{spell_id}/apply",
        json=application_request
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to apply spell: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    
    print("✅ Spell applied successfully!")
    print(f"\n📋 Application Details:")
    print(f"  Application ID: {result['application_id']}")
    print(f"  Files Touched: {result['files_touched']}")
    print(f"  Rationale: {result['rationale']}")
    print(f"\n📝 Generated Patch (first 20 lines):")
    patch_lines = result['patch'].split('\n')[:20]
    for line in patch_lines:
        print(f"  {line}")
    if len(result['patch'].split('\n')) > 20:
        print("  ...")
    
    print("\n" + "=" * 60)
    print("✅ Mock LLM Integration Test Passed!")
    print("=" * 60)
    print("\nYour API is ready for the hackathon demo! 🎉")


if __name__ == "__main__":
    try:
        test_spell_apply()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server")
        print("Please start the server first:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
