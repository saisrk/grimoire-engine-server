"""
Tests for PR Processor service.

This module contains tests for the PRProcessor class that handles
GitHub pull request webhook processing and diff fetching.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.pr_processor import PRProcessor


class TestPRProcessor:
    """Test suite for PRProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create a PRProcessor instance for testing."""
        return PRProcessor(github_token="test_token_123")
    
    @pytest.fixture
    def sample_webhook_payload(self):
        """Sample GitHub webhook payload for testing."""
        return {
            "action": "opened",
            "number": 123,
            "pull_request": {
                "number": 123,
                "title": "Fix bug in main.py",
                "state": "open"
            },
            "repository": {
                "full_name": "octocat/Hello-World",
                "name": "Hello-World",
                "owner": {
                    "login": "octocat"
                }
            }
        }
    
    @pytest.fixture
    def sample_diff(self):
        """Sample GitHub diff for testing."""
        return """diff --git a/app/main.py b/app/main.py
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
 def test_main():
+    # New test
     pass
"""
    
    def test_processor_initialization(self):
        """Test PRProcessor initialization with token."""
        processor = PRProcessor(github_token="my_token")
        assert processor.github_token == "my_token"
        assert processor.timeout == 30
    
    def test_processor_initialization_from_env(self, monkeypatch):
        """Test PRProcessor reads token from environment."""
        monkeypatch.setenv("GITHUB_API_TOKEN", "env_token")
        processor = PRProcessor()
        assert processor.github_token == "env_token"
    
    def test_parse_diff(self, processor, sample_diff):
        """Test diff parsing extracts correct file paths."""
        files = processor._parse_diff(sample_diff)
        assert len(files) == 2
        assert "app/main.py" in files
        assert "tests/test_main.py" in files
    
    def test_parse_diff_empty(self, processor):
        """Test parsing empty diff returns empty list."""
        files = processor._parse_diff("")
        assert files == []
    
    def test_parse_diff_no_changes(self, processor):
        """Test parsing diff with no file changes."""
        diff = "Some random text\nNo diff headers here\n"
        files = processor._parse_diff(diff)
        assert files == []
    
    @pytest.mark.asyncio
    async def test_process_pr_event_success(self, processor, sample_webhook_payload, sample_diff):
        """Test successful PR event processing."""
        # Mock fetch_pr_diff to return sample diff
        with patch.object(processor, 'fetch_pr_diff', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_diff
            
            result = await processor.process_pr_event(sample_webhook_payload)
            
            assert result["status"] == "success"
            assert result["repo"] == "octocat/Hello-World"
            assert result["pr_number"] == 123
            assert len(result["files_changed"]) == 2
            assert "app/main.py" in result["files_changed"]
            
            # Verify fetch_pr_diff was called with correct arguments
            mock_fetch.assert_called_once_with("octocat/Hello-World", 123)
    
    @pytest.mark.asyncio
    async def test_process_pr_event_missing_repo(self, processor):
        """Test PR event processing with missing repository."""
        payload = {"pull_request": {"number": 123}}
        result = await processor.process_pr_event(payload)
        
        assert result["status"] == "error"
        assert "Missing repository or PR number" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_pr_event_missing_pr_number(self, processor):
        """Test PR event processing with missing PR number."""
        payload = {"repository": {"full_name": "octocat/Hello-World"}}
        result = await processor.process_pr_event(payload)
        
        assert result["status"] == "error"
        assert "Missing repository or PR number" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_pr_event_fetch_fails(self, processor, sample_webhook_payload):
        """Test PR event processing when diff fetch fails."""
        with patch.object(processor, 'fetch_pr_diff', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            
            result = await processor.process_pr_event(sample_webhook_payload)
            
            assert result["status"] == "error"
            assert result["error"] == "Failed to fetch PR diff"
            assert result["repo"] == "octocat/Hello-World"
            assert result["pr_number"] == 123
    
    @pytest.mark.asyncio
    async def test_fetch_pr_diff_success(self, processor):
        """Test successful PR diff fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "diff --git a/file.py b/file.py"
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            diff = await processor.fetch_pr_diff("octocat/Hello-World", 123)
            
            assert diff == "diff --git a/file.py b/file.py"
    
    @pytest.mark.asyncio
    async def test_fetch_pr_diff_http_error(self, processor):
        """Test PR diff fetching with HTTP error."""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response
            ))
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            diff = await processor.fetch_pr_diff("octocat/Hello-World", 999)
            
            assert diff is None
    
    @pytest.mark.asyncio
    async def test_fetch_pr_diff_network_error(self, processor):
        """Test PR diff fetching with network error."""
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            diff = await processor.fetch_pr_diff("octocat/Hello-World", 123)
            
            assert diff is None
    
    @pytest.mark.asyncio
    async def test_fetch_pr_diff_rate_limit(self, processor):
        """Test PR diff fetching when rate limited."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1234567890"
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            diff = await processor.fetch_pr_diff("octocat/Hello-World", 123)
            
            assert diff is None
