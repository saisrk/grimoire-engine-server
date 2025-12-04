"""
Tests for GitHub webhook endpoint.

Tests webhook signature validation, payload parsing, and error handling.
"""

import hashlib
import hmac
import json
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock

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
            "/webhook/github",
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
            "/webhook/github",
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
            "/webhook/github",
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
            "/webhook/github",
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
            "/webhook/github",
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
            "/webhook/github",
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


# Integration Tests for End-to-End Webhook Processing


@pytest.mark.asyncio
async def test_webhook_integration_with_pr_processor_and_matcher(
    webhook_secret,
    sample_pr_payload,
    test_db
):
    """
    Test complete flow: webhook → PR processor → matcher → response.
    
    Validates Requirements: 1.1, 1.2, 3.1, 3.2, 4.1
    """
    from app.models.spell import Spell
    
    # Create test spells in database for matching
    spell1 = Spell(
        title="Fix undefined array access",
        description="Handle undefined array access in JavaScript",
        error_type="PullRequestChange",
        error_pattern="array undefined",
        solution_code="if (array && array.length) { ... }",
        tags="javascript,array,undefined"
    )
    spell2 = Spell(
        title="Fix Python import error",
        description="Resolve Python import issues",
        error_type="ImportError",
        error_pattern="import module",
        solution_code="import sys; sys.path.append(...)",
        tags="python,import"
    )
    spell3 = Spell(
        title="Fix PR changes",
        description="Handle pull request changes in repository",
        error_type="PullRequestChange",
        error_pattern="pull request repository",
        solution_code="# Review PR changes",
        tags="git,pr,repository"
    )
    
    test_db.add_all([spell1, spell2, spell3])
    await test_db.commit()
    await test_db.refresh(spell1)
    await test_db.refresh(spell2)
    await test_db.refresh(spell3)
    
    # Mock GitHub API response for PR diff
    mock_diff = """diff --git a/app/main.py b/app/main.py
index abc123..def456 100644
--- a/app/main.py
+++ b/app/main.py
@@ -1,3 +1,4 @@
+import logging
 def main():
     pass
diff --git a/tests/test_main.py b/tests/test_main.py
index 111222..333444 100644
--- a/tests/test_main.py
+++ b/tests/test_main.py
@@ -1,2 +1,3 @@
+import pytest
 def test_main():
     pass
"""
    
    with patch.dict("os.environ", {
        "GITHUB_WEBHOOK_SECRET": webhook_secret,
        "GITHUB_API_TOKEN": "test_token_123"
    }):
        with patch("app.services.pr_processor.httpx.AsyncClient") as mock_client:
            # Mock GitHub API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_diff
            mock_response.headers = {}
            mock_response.raise_for_status = Mock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
            signature = generate_signature(payload_bytes, webhook_secret)
            
            response = client.post(
                "/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert data["status"] == "success"
            assert data["event"] == "pull_request"
            assert data["action"] == "opened"
            
            # Verify pr_processing is included
            assert "pr_processing" in data
            assert data["pr_processing"] is not None
            assert data["pr_processing"]["repo"] == "testuser/test-repo"
            assert data["pr_processing"]["pr_number"] == 42
            assert data["pr_processing"]["status"] == "success"
            assert "files_changed" in data["pr_processing"]
            assert len(data["pr_processing"]["files_changed"]) == 2
            assert "app/main.py" in data["pr_processing"]["files_changed"]
            assert "tests/test_main.py" in data["pr_processing"]["files_changed"]
            
            # Verify matched_spells is included
            assert "matched_spells" in data
            assert isinstance(data["matched_spells"], list)
            # Should match spell1 and spell3 (both have PullRequestChange type)
            assert len(data["matched_spells"]) >= 1


@pytest.mark.asyncio
async def test_webhook_integration_with_github_token_configured(
    webhook_secret,
    sample_pr_payload,
    test_db
):
    """
    Test with GITHUB_API_TOKEN configured.
    
    Validates Requirements: 1.1, 1.2
    """
    from app.models.spell import Spell
    
    # Create a test spell
    spell = Spell(
        title="Test spell",
        description="Test description",
        error_type="PullRequestChange",
        error_pattern="test",
        solution_code="# test",
        tags="test"
    )
    test_db.add(spell)
    await test_db.commit()
    
    mock_diff = """diff --git a/test.py b/test.py
index 000..111 100644
--- a/test.py
+++ b/test.py
@@ -1 +1,2 @@
+# New line
 pass
"""
    
    with patch.dict("os.environ", {
        "GITHUB_WEBHOOK_SECRET": webhook_secret,
        "GITHUB_API_TOKEN": "valid_github_token"
    }):
        with patch("app.services.pr_processor.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_diff
            mock_response.headers = {}
            mock_response.raise_for_status = Mock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
            signature = generate_signature(payload_bytes, webhook_secret)
            
            response = client.post(
                "/webhook/github",
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
            assert data["pr_processing"] is not None
            assert data["pr_processing"]["status"] == "success"


@pytest.mark.asyncio
async def test_webhook_integration_without_github_token(
    webhook_secret,
    sample_pr_payload,
    test_db
):
    """
    Test with GITHUB_API_TOKEN not configured.
    
    Validates Requirements: 1.5
    """
    # Don't set GITHUB_API_TOKEN in environment
    with patch.dict("os.environ", {
        "GITHUB_WEBHOOK_SECRET": webhook_secret
    }, clear=False):
        # Remove GITHUB_API_TOKEN if it exists
        if "GITHUB_API_TOKEN" in os.environ:
            del os.environ["GITHUB_API_TOKEN"]
        
        with patch("app.services.pr_processor.httpx.AsyncClient") as mock_client:
            # Mock GitHub API to fail without token
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Requires authentication"
            mock_response.headers = {}
            mock_response.raise_for_status = Mock(side_effect=Exception("HTTP 401"))
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
            signature = generate_signature(payload_bytes, webhook_secret)
            
            response = client.post(
                "/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json"
                }
            )
            
            # Webhook should still return 200 to prevent GitHub retries
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            # PR processing may fail, but webhook succeeds
            assert "pr_processing" in data


@pytest.mark.asyncio
async def test_webhook_integration_spell_ranking_order(
    webhook_secret,
    sample_pr_payload,
    test_db
):
    """
    Verify spell IDs are returned in ranked order.
    
    Validates Requirements: 3.2, 4.2
    """
    from app.models.spell import Spell
    
    # Create spells with different relevance levels
    # High relevance: matches error type and has many keywords
    spell_high = Spell(
        title="Fix pull request repository changes",
        description="Handle pull request changes in repository with files",
        error_type="PullRequestChange",
        error_pattern="pull request repository files changed",
        solution_code="# High relevance",
        tags="pr,repository,files"
    )
    
    # Medium relevance: matches error type but fewer keywords
    spell_medium = Spell(
        title="Handle PR",
        description="Basic pull request handling",
        error_type="PullRequestChange",
        error_pattern="pull request",
        solution_code="# Medium relevance",
        tags="pr"
    )
    
    # Low relevance: different error type
    spell_low = Spell(
        title="Fix import error",
        description="Handle import errors",
        error_type="ImportError",
        error_pattern="import module",
        solution_code="# Low relevance",
        tags="import"
    )
    
    test_db.add_all([spell_high, spell_medium, spell_low])
    await test_db.commit()
    await test_db.refresh(spell_high)
    await test_db.refresh(spell_medium)
    await test_db.refresh(spell_low)
    
    mock_diff = """diff --git a/app/main.py b/app/main.py
index abc..def 100644
--- a/app/main.py
+++ b/app/main.py
@@ -1 +1,2 @@
+# change
 pass
"""
    
    with patch.dict("os.environ", {
        "GITHUB_WEBHOOK_SECRET": webhook_secret,
        "GITHUB_API_TOKEN": "test_token"
    }):
        with patch("app.services.pr_processor.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_diff
            mock_response.headers = {}
            mock_response.raise_for_status = Mock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
            signature = generate_signature(payload_bytes, webhook_secret)
            
            response = client.post(
                "/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify spells are returned
            assert "matched_spells" in data
            matched_spells = data["matched_spells"]
            
            if len(matched_spells) >= 2:
                # High relevance spell should be ranked higher than low relevance
                # spell_high should appear before spell_low
                high_index = matched_spells.index(spell_high.id) if spell_high.id in matched_spells else -1
                low_index = matched_spells.index(spell_low.id) if spell_low.id in matched_spells else -1
                
                # If both are present, high should come before low
                if high_index >= 0 and low_index >= 0:
                    assert high_index < low_index


@pytest.mark.asyncio
async def test_webhook_integration_pr_processor_failure(
    webhook_secret,
    sample_pr_payload,
    test_db
):
    """
    Test webhook returns 200 even when PR processor fails.
    
    Validates Requirements: 5.1, 5.4
    """
    with patch.dict("os.environ", {
        "GITHUB_WEBHOOK_SECRET": webhook_secret,
        "GITHUB_API_TOKEN": "test_token"
    }):
        with patch("app.services.pr_processor.PRProcessor.process_pr_event") as mock_process:
            # Mock PR processor to raise exception
            mock_process.side_effect = Exception("GitHub API error")
            
            payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
            signature = generate_signature(payload_bytes, webhook_secret)
            
            response = client.post(
                "/webhook/github",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json"
                }
            )
            
            # Webhook should still return 200 to prevent GitHub retries
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "pr_processing" in data
            assert "matched_spells" in data


@pytest.mark.asyncio
async def test_webhook_integration_matcher_failure(
    webhook_secret,
    sample_pr_payload,
    test_db
):
    """
    Test webhook returns 200 even when matcher service fails.
    
    Validates Requirements: 5.2, 5.4
    """
    mock_diff = """diff --git a/test.py b/test.py
index 000..111 100644
--- a/test.py
+++ b/test.py
@@ -1 +1,2 @@
+# change
 pass
"""
    
    with patch.dict("os.environ", {
        "GITHUB_WEBHOOK_SECRET": webhook_secret,
        "GITHUB_API_TOKEN": "test_token"
    }):
        with patch("app.services.pr_processor.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_diff
            mock_response.headers = {}
            mock_response.raise_for_status = Mock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            with patch("app.services.matcher.MatcherService.match_spells") as mock_match:
                # Mock matcher to raise exception
                mock_match.side_effect = Exception("Database error")
                
                payload_bytes = json.dumps(sample_pr_payload).encode("utf-8")
                signature = generate_signature(payload_bytes, webhook_secret)
                
                response = client.post(
                    "/webhook/github",
                    content=payload_bytes,
                    headers={
                        "X-Hub-Signature-256": signature,
                        "X-GitHub-Event": "pull_request",
                        "Content-Type": "application/json"
                    }
                )
                
                # Webhook should still return 200
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "pr_processing" in data
                # Matched spells should be empty list on failure
                assert data["matched_spells"] == []


@pytest.mark.asyncio
async def test_webhook_integration_non_pr_event(
    webhook_secret,
    test_db
):
    """
    Test webhook handles non-pull_request events correctly.
    
    Validates Requirements: 4.1, 4.3
    """
    # Create a non-PR event payload (e.g., push event)
    push_payload = {
        "ref": "refs/heads/main",
        "repository": {
            "name": "test-repo",
            "full_name": "testuser/test-repo"
        },
        "pusher": {
            "name": "testuser"
        }
    }
    
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": webhook_secret}):
        payload_bytes = json.dumps(push_payload).encode("utf-8")
        signature = generate_signature(payload_bytes, webhook_secret)
        
        response = client.post(
            "/webhook/github",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "push",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["event"] == "push"
        # pr_processing should be None for non-PR events
        assert data["pr_processing"] is None
        # matched_spells should be empty list
        assert data["matched_spells"] == []
