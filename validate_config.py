#!/usr/bin/env python3
"""
Configuration validation script for Grimoire Engine.

Checks that all required environment variables are set correctly
and provides helpful feedback for any issues.

Usage:
    python validate_config.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def check_env_file():
    """Check if .env file exists."""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Run: cp .env.example .env")
        return False
    print("✅ .env file exists")
    return True


def check_required_vars():
    """Check required environment variables."""
    required = {
        "DATABASE_URL": "Database connection string",
        "GITHUB_WEBHOOK_SECRET": "GitHub webhook secret for signature validation",
        "SECRET_KEY": "JWT secret key for authentication",
    }
    
    all_good = True
    for var, description in required.items():
        value = os.getenv(var)
        if not value:
            print(f"❌ {var} not set")
            print(f"   {description}")
            all_good = False
        elif value.endswith("_here") or value == "my-webhook-secret":
            print(f"⚠️  {var} has placeholder value")
            print(f"   {description}")
            all_good = False
        else:
            print(f"✅ {var} is set")
    
    return all_good


def check_optional_vars():
    """Check optional environment variables."""
    optional = {
        "GITHUB_API_TOKEN": "GitHub API token (optional, for fetching PR diffs)",
        "CORS_ORIGINS": "CORS allowed origins",
    }
    
    for var, description in optional.items():
        value = os.getenv(var)
        if not value:
            print(f"ℹ️  {var} not set (optional)")
            print(f"   {description}")
        else:
            print(f"✅ {var} is set")


def check_auto_generation_config():
    """Check auto-generation configuration."""
    print("\n" + "=" * 60)
    print("Auto-Generation Configuration")
    print("=" * 60)
    
    auto_create = os.getenv("AUTO_CREATE_SPELLS", "false").lower()
    
    if auto_create in ("true", "1", "yes"):
        print("✅ Auto-generation is ENABLED")
        
        # Check provider
        provider = os.getenv("LLM_PROVIDER", "openai")
        print(f"   Provider: {provider}")
        
        # Check model
        model = os.getenv("LLM_MODEL", "gpt-4-turbo")
        print(f"   Model: {model}")
        
        # Check API key
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            key_name = "OPENAI_API_KEY"
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            key_name = "ANTHROPIC_API_KEY"
        
        if not api_key or api_key.endswith("_here"):
            print(f"   ❌ {key_name} not configured!")
            print(f"      Get your key from:")
            if provider == "openai":
                print(f"      https://platform.openai.com/api-keys")
            else:
                print(f"      https://console.anthropic.com/")
            return False
        else:
            print(f"   ✅ {key_name}: {api_key[:10]}...{api_key[-4:]}")
        
        # Check timeout and max tokens
        timeout = os.getenv("LLM_TIMEOUT", "30")
        max_tokens = os.getenv("LLM_MAX_TOKENS", "1000")
        print(f"   Timeout: {timeout}s")
        print(f"   Max tokens: {max_tokens}")
        
        return True
    else:
        print("ℹ️  Auto-generation is DISABLED")
        print("   Set AUTO_CREATE_SPELLS=true to enable")
        print("   See SETUP_AUTO_GENERATION.md for setup guide")
        return True


def check_database():
    """Check database configuration."""
    print("\n" + "=" * 60)
    print("Database Configuration")
    print("=" * 60)
    
    db_url = os.getenv("DATABASE_URL", "")
    
    if "sqlite" in db_url:
        # Extract path from SQLite URL
        if ":///" in db_url:
            db_path = db_url.split("///")[1]
            db_file = Path(db_path)
            
            if db_file.exists():
                print(f"✅ Database file exists: {db_path}")
                print(f"   Size: {db_file.stat().st_size / 1024:.2f} KB")
            else:
                print(f"⚠️  Database file not found: {db_path}")
                print(f"   Run: alembic upgrade head")
        else:
            print(f"✅ Database URL: {db_url}")
    else:
        print(f"✅ Database URL: {db_url}")
    
    return True


def check_ports():
    """Check port configuration."""
    print("\n" + "=" * 60)
    print("Server Configuration")
    print("=" * 60)
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = os.getenv("API_PORT", "8000")
    
    print(f"✅ Host: {host}")
    print(f"✅ Port: {port}")
    print(f"   API will be available at: http://localhost:{port}")
    print(f"   Docs will be available at: http://localhost:{port}/docs")
    
    return True


def main():
    """Run all configuration checks."""
    print("=" * 60)
    print("Grimoire Engine Configuration Validator")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Run checks
    checks = [
        ("Environment File", check_env_file),
        ("Required Variables", check_required_vars),
        ("Optional Variables", check_optional_vars),
        ("Database", check_database),
        ("Server", check_ports),
        ("Auto-Generation", check_auto_generation_config),
    ]
    
    results = []
    for name, check_func in checks:
        if name in ["Environment File", "Required Variables", "Optional Variables"]:
            print(f"\n{'=' * 60}")
            print(name)
            print("=" * 60)
        
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error checking {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 Configuration looks good!")
        print("\nNext steps:")
        print("  1. Run migrations: alembic upgrade head")
        print("  2. Start server: uvicorn app.main:app --reload")
        print("  3. Test auto-generation: python test_spell_generation.py")
        return 0
    else:
        print("\n⚠️  Some configuration issues found.")
        print("Please fix the issues above and run this script again.")
        print("\nFor help, see:")
        print("  - README.md")
        print("  - SETUP_AUTO_GENERATION.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
