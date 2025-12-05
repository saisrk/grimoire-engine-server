"""
Logging utilities with sensitive data redaction.

This module provides utilities for logging with automatic redaction of
sensitive information such as API keys, authentication tokens, and other
credentials.
"""

import re
from typing import Any, Dict, Union


# Patterns for sensitive data that should be redacted
# Order matters - more specific patterns should come first
SENSITIVE_PATTERNS = [
    # OpenAI API keys (sk- prefix with at least 6 chars for flexibility)
    (r'sk-[a-zA-Z0-9]{6,}', '[REDACTED_API_KEY]'),
    # Bearer tokens in Authorization headers
    (r'Bearer\s+[a-zA-Z0-9\-._~+/]+=*', 'Bearer [REDACTED_TOKEN]'),
    # Token parameters
    (r'token=[a-zA-Z0-9\-._~+/]+=*', 'token=[REDACTED_TOKEN]'),
    # Authorization headers (catch-all) - must come after Bearer pattern
    (r'Authorization["\']?\s*:\s*["\']?[^"\'\s]+["\']?', 'Authorization: [REDACTED_AUTH]'),
    # x-api-key headers
    (r'x-api-key["\']?\s*:\s*["\']?[a-zA-Z0-9\-._~+/]+=*["\']?', 'x-api-key: [REDACTED_API_KEY]'),
    # API key assignments (api_key=, apikey=, etc.)
    (r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9\-._~+/]{6,}["\']?', 'api_key=[REDACTED_API_KEY]'),
    (r'apikey["\']?\s*[:=]\s*["\']?[a-zA-Z0-9\-._~+/]{6,}["\']?', 'apikey=[REDACTED_API_KEY]'),
    # Anthropic API keys
    (r'anthropic[_-]?api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9\-._~+/]{6,}["\']?', 'anthropic_api_key=[REDACTED_API_KEY]'),
    # OpenAI API keys
    (r'openai[_-]?api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9\-._~+/]{6,}["\']?', 'openai_api_key=[REDACTED_API_KEY]'),
]


def redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive data from text.
    
    Replaces sensitive patterns (API keys, tokens, etc.) with redacted
    placeholders to prevent accidental logging of credentials.
    
    Args:
        text: Text that may contain sensitive data
        
    Returns:
        Text with sensitive data redacted
        
    Example:
        >>> redact_sensitive_data("Authorization: Bearer sk-abc123xyz")
        'Authorization: Bearer [REDACTED_TOKEN]'
        
        >>> redact_sensitive_data("api_key=sk-1234567890abcdefghij")
        'api_key=[REDACTED_API_KEY]'
    """
    if not isinstance(text, str):
        return text
    
    redacted = text
    
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    
    return redacted


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive data from dictionary values.
    
    Recursively processes dictionary values and redacts sensitive data
    from string values. Handles nested dictionaries and lists.
    
    Special handling for keys that commonly contain sensitive data:
    - api_key, apikey, api-key
    - token, access_token, auth_token
    - password, secret
    
    Args:
        data: Dictionary that may contain sensitive data
        
    Returns:
        Dictionary with sensitive data redacted
        
    Example:
        >>> redact_dict({"api_key": "sk-abc123", "name": "test"})
        {'api_key': '[REDACTED_API_KEY]', 'name': 'test'}
    """
    if not isinstance(data, dict):
        return data
    
    # Keys that commonly contain sensitive data
    sensitive_keys = {
        'api_key', 'apikey', 'api-key', 'api_keys',
        'token', 'access_token', 'auth_token', 'bearer_token',
        'password', 'secret', 'api_secret',
        'authorization', 'x-api-key'
    }
    
    redacted = {}
    
    for key, value in data.items():
        key_lower = key.lower().replace('_', '-')
        
        # If key is known to contain sensitive data, redact the entire value
        if key_lower in sensitive_keys or any(s in key_lower for s in ['key', 'token', 'secret', 'password']):
            if isinstance(value, str) and value:
                redacted[key] = '[REDACTED]'
            else:
                redacted[key] = value
        elif isinstance(value, str):
            redacted[key] = redact_sensitive_data(value)
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_dict(item) if isinstance(item, dict)
                else redact_sensitive_data(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            redacted[key] = value
    
    return redacted


def safe_log_data(data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
    """
    Prepare data for safe logging by redacting sensitive information.
    
    Convenience function that handles both strings and dictionaries.
    
    Args:
        data: Data to prepare for logging (string or dict)
        
    Returns:
        Data with sensitive information redacted
        
    Example:
        >>> safe_log_data("Bearer sk-abc123")
        'Bearer [REDACTED_TOKEN]'
        
        >>> safe_log_data({"headers": {"Authorization": "Bearer sk-abc123"}})
        {'headers': {'Authorization': 'Authorization: [REDACTED_AUTH]'}}
    """
    if isinstance(data, str):
        return redact_sensitive_data(data)
    elif isinstance(data, dict):
        return redact_dict(data)
    else:
        return data
