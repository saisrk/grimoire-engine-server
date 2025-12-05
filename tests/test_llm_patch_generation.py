"""
Unit tests for LLM Service patch generation.

Tests the generate_patch method with mocked API responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm_service import LLMService


@pytest.mark.asyncio
async def test_generate_patch_success_openai():
    """Test successful patch generation with OpenAI."""
    llm = LLMService(provider="openai", api_key="test-key")
    
    # Mock the OpenAI API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"patch": "diff --git a/test.py\\n--- a/test.py\\n+++ b/test.py", "files_touched": ["test.py"], "rationale": "Fixed the issue"}'
            }
        }]
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        result = await llm.generate_patch("test prompt", timeout=30)
        
        assert "patch" in result
        assert "files_touched" in result
        assert "rationale" in result
        assert result["files_touched"] == ["test.py"]
        assert result["rationale"] == "Fixed the issue"


@pytest.mark.asyncio
async def test_generate_patch_success_anthropic():
    """Test successful patch generation with Anthropic."""
    llm = LLMService(provider="anthropic", api_key="test-key")
    
    # Mock the Anthropic API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "content": [{
            "text": '{"patch": "diff --git a/test.py\\n--- a/test.py\\n+++ b/test.py", "files_touched": ["test.py"], "rationale": "Fixed the issue"}'
        }]
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        result = await llm.generate_patch("test prompt", timeout=30)
        
        assert "patch" in result
        assert "files_touched" in result
        assert "rationale" in result
        assert result["files_touched"] == ["test.py"]
        assert result["rationale"] == "Fixed the issue"


@pytest.mark.asyncio
async def test_generate_patch_no_api_key():
    """Test patch generation without API key."""
    # Mock environment to ensure no API key is loaded
    with patch.dict("os.environ", {}, clear=True):
        llm = LLMService(provider="openai", api_key=None)
        
        result = await llm.generate_patch("test prompt", timeout=30)
        
        assert "error" in result
        assert result["error"] == "LLM API key not configured"


@pytest.mark.asyncio
async def test_generate_patch_unsupported_provider():
    """Test patch generation with unsupported provider."""
    llm = LLMService(provider="unsupported", api_key="test-key")
    
    result = await llm.generate_patch("test prompt", timeout=30)
    
    assert "error" in result
    assert "Unsupported LLM provider" in result["error"]


@pytest.mark.asyncio
async def test_generate_patch_missing_fields():
    """Test patch generation with incomplete LLM response."""
    llm = LLMService(provider="openai", api_key="test-key")
    
    # Mock response missing required fields
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"patch": "diff --git a/test.py"}'
            }
        }]
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        result = await llm.generate_patch("test prompt", timeout=30)
        
        assert "error" in result
        assert result["error"] == "LLM response missing required fields"


@pytest.mark.asyncio
async def test_generate_patch_llm_error_response():
    """Test patch generation when LLM returns error."""
    llm = LLMService(provider="openai", api_key="test-key")
    
    # Mock LLM returning error
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"error": "Unable to generate patch"}'
            }
        }]
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        result = await llm.generate_patch("test prompt", timeout=30)
        
        assert "error" in result
        assert result["error"] == "Unable to generate patch"


@pytest.mark.asyncio
async def test_generate_patch_timeout():
    """Test patch generation with timeout."""
    llm = LLMService(provider="openai", api_key="test-key")
    
    # Mock timeout exception
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=Exception("Timeout")
        )
        
        with pytest.raises(Exception) as exc_info:
            await llm.generate_patch("test prompt", timeout=30)
        
        assert "Timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_patch_api_error():
    """Test patch generation with API error."""
    llm = LLMService(provider="openai", api_key="test-key")
    
    # Mock API error
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API Error")
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(Exception) as exc_info:
            await llm.generate_patch("test prompt", timeout=30)
        
        assert "API Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_patch_invalid_json():
    """Test patch generation with invalid JSON response."""
    llm = LLMService(provider="openai", api_key="test-key")
    
    # Mock invalid JSON response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": 'invalid json {'
            }
        }]
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(Exception):
            await llm.generate_patch("test prompt", timeout=30)


@pytest.mark.asyncio
async def test_generate_patch_custom_timeout():
    """Test patch generation with custom timeout."""
    llm = LLMService(provider="openai", api_key="test-key", timeout=10)
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"patch": "diff", "files_touched": ["test.py"], "rationale": "Fixed"}'
            }
        }]
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post
        
        # Use custom timeout
        result = await llm.generate_patch("test prompt", timeout=45)
        
        # Verify the timeout was passed correctly
        assert "patch" in result
        
        # Check that AsyncClient was called with the custom timeout
        mock_client.assert_called_with(timeout=45)
