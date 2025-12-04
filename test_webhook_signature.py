#!/usr/bin/env python3
"""
Test script to verify GitHub webhook signature validation.

This script helps debug signature validation issues by:
1. Creating a test payload
2. Computing the signature the same way GitHub does
3. Testing the validation function
"""

import hashlib
import hmac
import json

# Your webhook secret (same as in .env and GitHub)
WEBHOOK_SECRET = "your_secret_here"  # Replace with your actual secret

# Sample payload (similar to what GitHub sends)
payload = {
    "action": "opened",
    "number": 1,
    "pull_request": {
        "id": 1,
        "title": "Test PR"
    },
    "repository": {
        "full_name": "user/repo"
    }
}

# Convert to JSON bytes (no extra whitespace)
payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

# Compute signature the way GitHub does
signature_hash = hmac.new(
    WEBHOOK_SECRET.encode('utf-8'),
    payload_bytes,
    hashlib.sha256
).hexdigest()

signature_header = f"sha256={signature_hash}"

print("=" * 60)
print("GitHub Webhook Signature Test")
print("=" * 60)
print(f"\nPayload: {payload_bytes.decode('utf-8')}")
print(f"\nPayload length: {len(payload_bytes)} bytes")
print(f"\nComputed signature: {signature_header}")
print(f"\nSignature hash only: {signature_hash}")
print("\n" + "=" * 60)
print("\nTo test with curl:")
print("=" * 60)
print(f"""
curl -X POST http://localhost:8000/webhook/github \\
  -H "Content-Type: application/json" \\
  -H "X-Hub-Signature-256: {signature_header}" \\
  -H "X-GitHub-Event: pull_request" \\
  -d '{payload_bytes.decode('utf-8')}'
""")

# Test the validation function
print("\n" + "=" * 60)
print("Testing validation function:")
print("=" * 60)

from app.api.webhook import validate_signature

result = validate_signature(payload_bytes, signature_header, WEBHOOK_SECRET)
print(f"\nValidation result: {result}")

if result:
    print("✓ Signature validation PASSED")
else:
    print("✗ Signature validation FAILED")
