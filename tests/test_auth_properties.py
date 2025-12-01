"""
Property-based tests for authentication system.

These tests verify universal properties that should hold across all inputs
using the Hypothesis library for property-based testing.
"""

import pytest
from hypothesis import given, settings, strategies as st
from app.services.auth_service import hash_password, verify_password


# Feature: user-authentication, Property 1: Registration creates hashed password
# Validates: Requirements 1.1, 4.1, 4.3
@given(
    password=st.text(
        min_size=8,
        max_size=72,  # Bcrypt has a 72-byte limit
        alphabet=st.characters(blacklist_categories=("Cs", "Cc"))
    )
)
@settings(max_examples=5, deadline=None)  # Reduced from 100 due to bcrypt's intentional slowness
def test_registration_creates_hashed_password(password):
    """
    Property: For any valid password, hashing should create a bcrypt hash
    that differs from the plain text password.
    
    This verifies:
    - Passwords are hashed (not stored in plain text)
    - The hash is different from the original password
    - The hash can be verified against the original password
    """
    # Hash the password
    hashed = hash_password(password)
    
    # Verify the hash is different from the plain text password
    assert hashed != password, "Hashed password should differ from plain text"
    
    # Verify the hash starts with bcrypt identifier
    assert hashed.startswith("$2b$"), "Hash should use bcrypt format"
    
    # Verify the cost factor is 12 (bcrypt format: $2b$12$...)
    parts = hashed.split("$")
    assert len(parts) >= 4, "Hash should have proper bcrypt structure"
    assert parts[2] == "12", "Hash should use cost factor 12"
    
    # Verify the hashed password can be verified against the original
    assert verify_password(password, hashed), "Hashed password should verify correctly"
    
    # Verify a different password doesn't verify
    if len(password) > 0:
        wrong_password = password + "x"
        assert not verify_password(wrong_password, hashed), "Wrong password should not verify"
