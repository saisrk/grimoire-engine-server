"""
Tests for logging utilities with sensitive data redaction.

This module tests the redaction functionality to ensure sensitive data
like API keys and tokens are properly redacted from logs.
"""

import pytest
from app.utils.logging import redact_sensitive_data, redact_dict, safe_log_data


class TestRedactSensitiveData:
    """Tests for redact_sensitive_data function."""
    
    def test_redact_openai_api_key(self):
        """Test redaction of OpenAI API keys (sk- prefix)."""
        text = "Using API key: sk-1234567890abcdefghij"
        result = redact_sensitive_data(text)
        assert "sk-1234567890abcdefghij" not in result
        assert "[REDACTED_API_KEY]" in result
    
    def test_redact_bearer_token(self):
        """Test redaction of Bearer tokens."""
        text = "Authorization: Bearer abc123xyz456"
        result = redact_sensitive_data(text)
        assert "abc123xyz456" not in result
        assert "[REDACTED" in result  # Either Bearer or Authorization pattern will match
    
    def test_redact_token_parameter(self):
        """Test redaction of token= parameters."""
        text = "?token=abc123xyz456&user=test"
        result = redact_sensitive_data(text)
        assert "abc123xyz456" not in result
        assert "token=[REDACTED_TOKEN]" in result
    
    def test_redact_api_key_assignment(self):
        """Test redaction of api_key assignments."""
        text = 'api_key="sk-1234567890abcdefghij"'
        result = redact_sensitive_data(text)
        assert "sk-1234567890abcdefghij" not in result
        assert "[REDACTED_API_KEY]" in result
    
    def test_redact_authorization_header(self):
        """Test redaction of Authorization headers."""
        text = '"Authorization": "Bearer sk-abc123xyz"'
        result = redact_sensitive_data(text)
        assert "sk-abc123xyz" not in result
        assert "[REDACTED_AUTH]" in result
    
    def test_redact_x_api_key_header(self):
        """Test redaction of x-api-key headers."""
        text = '"x-api-key": "abc123xyz456789"'
        result = redact_sensitive_data(text)
        assert "abc123xyz456789" not in result
        assert "[REDACTED_API_KEY]" in result
    
    def test_redact_anthropic_api_key(self):
        """Test redaction of Anthropic API keys."""
        text = "anthropic_api_key=sk-ant-1234567890abcdefghij"
        result = redact_sensitive_data(text)
        assert "sk-ant-1234567890abcdefghij" not in result
        assert "[REDACTED_API_KEY]" in result
    
    def test_redact_openai_api_key_assignment(self):
        """Test redaction of OpenAI API key assignments."""
        text = "openai_api_key=sk-1234567890abcdefghij"
        result = redact_sensitive_data(text)
        assert "sk-1234567890abcdefghij" not in result
        assert "[REDACTED_API_KEY]" in result
    
    def test_preserve_non_sensitive_data(self):
        """Test that non-sensitive data is preserved."""
        text = "User: john, Email: john@example.com, Status: active"
        result = redact_sensitive_data(text)
        assert result == text
    
    def test_multiple_sensitive_patterns(self):
        """Test redaction of multiple sensitive patterns in one string."""
        text = "api_key=sk-abc123 and Bearer token123 and token=xyz789"
        result = redact_sensitive_data(text)
        assert "sk-abc123" not in result
        assert "token123" not in result
        assert "xyz789" not in result
        assert "[REDACTED" in result
    
    def test_case_insensitive_redaction(self):
        """Test that redaction is case-insensitive."""
        text = "API_KEY=sk-1234567890abcdefghij"
        result = redact_sensitive_data(text)
        assert "sk-1234567890abcdefghij" not in result
        assert "[REDACTED_API_KEY]" in result
    
    def test_non_string_input(self):
        """Test that non-string inputs are returned unchanged."""
        assert redact_sensitive_data(123) == 123
        assert redact_sensitive_data(None) is None
        assert redact_sensitive_data([]) == []


class TestRedactDict:
    """Tests for redact_dict function."""
    
    def test_redact_dict_string_values(self):
        """Test redaction of string values in dictionary."""
        data = {
            "api_key": "sk-1234567890abcdefghij",
            "name": "test"
        }
        result = redact_dict(data)
        assert "sk-1234567890abcdefghij" not in str(result)
        assert "[REDACTED]" in result["api_key"]
        assert result["name"] == "test"
    
    def test_redact_nested_dict(self):
        """Test redaction of nested dictionaries."""
        data = {
            "config": {
                "api_key": "sk-abc123",
                "timeout": 30
            },
            "user": "test"
        }
        result = redact_dict(data)
        assert "sk-abc123" not in str(result)
        assert "[REDACTED]" in result["config"]["api_key"]
        assert result["config"]["timeout"] == 30
        assert result["user"] == "test"
    
    def test_redact_dict_with_lists(self):
        """Test redaction of dictionaries containing lists."""
        data = {
            "headers": [
                "Authorization: Bearer sk-abc123",
                "Content-Type: application/json"
            ]
        }
        result = redact_dict(data)
        assert "sk-abc123" not in str(result)
        assert "[REDACTED" in result["headers"][0]
        assert result["headers"][1] == "Content-Type: application/json"
    
    def test_redact_dict_with_dict_in_list(self):
        """Test redaction of dictionaries within lists."""
        data = {
            "requests": [
                {"api_key": "sk-abc123", "method": "POST"},
                {"api_key": "sk-xyz789", "method": "GET"}
            ]
        }
        result = redact_dict(data)
        assert "sk-abc123" not in str(result)
        assert "sk-xyz789" not in str(result)
        assert "[REDACTED]" in result["requests"][0]["api_key"]
        assert "[REDACTED]" in result["requests"][1]["api_key"]
    
    def test_redact_dict_preserves_non_sensitive(self):
        """Test that non-sensitive data is preserved in dictionaries."""
        data = {
            "user": "john",
            "email": "john@example.com",
            "status": "active"
        }
        result = redact_dict(data)
        assert result == data
    
    def test_non_dict_input(self):
        """Test that non-dict inputs are returned unchanged."""
        assert redact_dict("string") == "string"
        assert redact_dict(123) == 123
        assert redact_dict(None) is None


class TestSafeLogData:
    """Tests for safe_log_data convenience function."""
    
    def test_safe_log_string(self):
        """Test safe logging of strings."""
        text = "api_key=sk-1234567890abcdefghij"
        result = safe_log_data(text)
        assert "sk-1234567890abcdefghij" not in result
        assert "[REDACTED_API_KEY]" in result
    
    def test_safe_log_dict(self):
        """Test safe logging of dictionaries."""
        data = {"api_key": "sk-abc123", "name": "test"}
        result = safe_log_data(data)
        assert "sk-abc123" not in str(result)
        assert "[REDACTED]" in result["api_key"]
        assert result["name"] == "test"
    
    def test_safe_log_other_types(self):
        """Test safe logging of other types."""
        assert safe_log_data(123) == 123
        assert safe_log_data(None) is None
        assert safe_log_data([1, 2, 3]) == [1, 2, 3]


class TestRealWorldScenarios:
    """Tests for real-world logging scenarios."""
    
    def test_llm_request_log(self):
        """Test redaction in LLM request logs."""
        log_data = {
            "url": "https://api.openai.com/v1/chat/completions",
            "headers": {
                "Authorization": "Bearer sk-1234567890abcdefghij",
                "Content-Type": "application/json"
            },
            "timeout": 30
        }
        result = redact_dict(log_data)
        assert "sk-1234567890abcdefghij" not in str(result)
        assert "[REDACTED" in result["headers"]["Authorization"]
        assert result["timeout"] == 30
    
    def test_error_message_with_api_key(self):
        """Test redaction in error messages containing API keys."""
        error_msg = "Failed to authenticate with API key sk-abc123xyz: Invalid credentials"
        result = redact_sensitive_data(error_msg)
        assert "sk-abc123xyz" not in result
        assert "[REDACTED_API_KEY]" in result
        assert "Invalid credentials" in result
    
    def test_patch_generation_context(self):
        """Test redaction in patch generation context logs."""
        context = {
            "spell_id": 123,
            "repository": "user/repo",
            "commit_sha": "abc123",
            "prompt": "Generate patch with api_key=sk-secret123",
            "response": {
                "patch": "diff --git a/file.py",
                "rationale": "Fixed issue"
            }
        }
        result = redact_dict(context)
        assert "sk-secret123" not in str(result)
        assert "[REDACTED_API_KEY]" in result["prompt"]
        assert result["spell_id"] == 123
        assert result["response"]["rationale"] == "Fixed issue"
