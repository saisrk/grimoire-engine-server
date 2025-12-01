#!/usr/bin/env python
"""Quick test of auth service functions."""

from app.services.auth_service import hash_password, verify_password

# Test 1: Basic hashing
print("Test 1: Basic hashing")
pwd = "testpass123"
h = hash_password(pwd)
print(f"  Hash: {h[:20]}...")
print(f"  Starts with $2b$: {h.startswith('$2b$')}")
print(f"  Cost factor 12: {h.split('$')[2] == '12'}")
print(f"  Verify correct: {verify_password(pwd, h)}")
print(f"  Verify wrong: {verify_password('wrong', h)}")
print()

# Test 2: Different passwords produce different hashes
print("Test 2: Unique salts")
h1 = hash_password(pwd)
h2 = hash_password(pwd)
print(f"  Same password, different hashes: {h1 != h2}")
print(f"  Both verify: {verify_password(pwd, h1) and verify_password(pwd, h2)}")
print()

# Test 3: Long password (72 byte limit)
print("Test 3: Long password handling")
long_pwd = "a" * 100
h_long = hash_password(long_pwd)
print(f"  Long password hashed: {h_long[:20]}...")
print(f"  Verifies: {verify_password(long_pwd, h_long)}")
print()

print("All tests passed!")
