#!/usr/bin/env python
"""Simple test of auth service functions."""

from app.services.auth_service import hash_password, verify_password

def test_basic_hashing():
    """Test basic password hashing."""
    pwd = "testpass123"
    h = hash_password(pwd)
    
    # Check hash format
    assert h.startswith("$2b$"), "Hash should use bcrypt format"
    assert h.split("$")[2] == "12", "Hash should use cost factor 12"
    assert h != pwd, "Hash should differ from plain text"
    
    # Check verification
    assert verify_password(pwd, h), "Correct password should verify"
    assert not verify_password("wrong", h), "Wrong password should not verify"
    
    print("✓ Basic hashing test passed")

def test_unique_salts():
    """Test that same password produces different hashes."""
    pwd = "testpass123"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)
    
    assert h1 != h2, "Same password should produce different hashes"
    assert verify_password(pwd, h1), "First hash should verify"
    assert verify_password(pwd, h2), "Second hash should verify"
    
    print("✓ Unique salts test passed")

if __name__ == "__main__":
    test_basic_hashing()
    test_unique_salts()
    print("\nAll tests passed!")
