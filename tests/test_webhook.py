"""
Tests for GitHub webhook endpoint.

Tests webhook signature validation, payload parsing, and error handling.
"""

import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)


def generate_signature(payload: bytes, secret: str) -> str:
    """
    Generate GitHub webhook signature for testing.
    
    Args:
        payload: Request body bytes
        secret: Webhook secret
        
    Returns:
        Signature string in format "sha256=..."
    """
    signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


@pytest.fixture
def webhook_secret():
    """Fixture providing test webhook secret."""
    return "test_webhook_secret_123"


@pytest.fixture
def sample_pr_payload():
    """Fixture providing sample pull_request webhook payload."""
    return {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1,
            "number": 42,
            "title": "Test PR",
            "state": "open",
            "user": {
                "login": "testuser"
            }
        },
        "repository": {
            "id": 123,
            "name": "test-repo",
            "full_name": "testuser/test-repo"
        }
    }


def test_webhook_with_valid_signature(webhook_secret, sample_pr_payload):
    """Test webhook endpoint accepts requests with valid signatures."""
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": webhook_secret}):
        payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
        signature = generate_signature(payload_bytes, webhook_secret)
        
        response = client.post(
            "/webhook",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["event"] == "pull_request"
        assert data["action"] == "opened"


def test_webhook_with_invalid_signature(webhook_secret, sample_pr_payload):
    """Test webhook endpoint rejects requests with invalid signatures."""
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": webhook_secret}):
        payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
        invalid_signature = "sha256=invalid_signature_here"
        
        response = client.post(
            "/webhook",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": invalid_signature,
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid signature" in response.json()["detail"]


def test_webhook_with_missing_signature(webhook_secret, sample_pr_payload):
    """Test webhook endpoint rejects requests without signature header."""
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": webhook_secret}):
        payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
        
        response = client.post(
            "/webhook",
            content=payload_bytes,
            headers={
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 401
        assert "Missing signature header" in response.json()["detail"]


def test_webhook_with_malformed_signature(webhook_secret, sample_pr_payload):
    """Test webhook endpoint rejects malformed signature format."""
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": webhook_secret}):
        payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
        malformed_signature = "invalid_format_without_prefix"
        
        response = client.post(
            "/webhook",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": malformed_signature,
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid signature" in response.json()["detail"]


def test_webhook_with_invalid_json(webhook_secret):
    """Test webhook endpoint handles invalid JSON payload."""
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": webhook_secret}):
        invalid_payload = b"not valid json {"
        signature = generate_signature(invalid_payload, webhook_secret)
        
        response = client.post(
            "/webhook",
            content=invalid_payload,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid JSON payload" in response.json()["detail"]


def test_webhook_without_secret_configured(sample_pr_payload):
    """Test webhook endpoint returns 500 when secret is not configured."""
    with patch.dict("os.environ", {}, clear=True):
        payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
        
        response = client.post(
            "/webhook",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": "sha256=test",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 500
        assert "Webhook secret not configured" in response.json()["detail"]


def test_validate_signature_function():
    """Test the validate_signature function directly."""
    from app.api.webhook import validate_signature
    
    secret = "test_secret"
    payload = b"test payload"
    
    # Generate valid signature
    valid_sig = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    valid_sig_with_prefix = f"sha256={valid_sig}"
    
    # Test valid signature
    assert validate_signature(payload, valid_sig_with_prefix, secret) is True
    
    # Test invalid signature
    assert validate_signature(payload, "sha256=invalid", secret) is False
    
    # Test missing prefix
    assert validate_signature(payload, valid_sig, secret) is False
    
    # Test empty signature
    assert validate_signature(payload, "", secret) is False
    
    # Test None signature
    assert validate_signature(payload, None, secret) is False
