"""
LLM Service for generating spell summaries and solutions.

This module provides integration with LLM providers (OpenAI, Anthropic) to generate
human-readable descriptions and solution suggestions for error patterns.
"""

import logging
import os
from typing import Any, Dict, Optional

from app.utils.logging import safe_log_data

logger = logging.getLogger(__name__)


def get_llm_service(*args, **kwargs):
    """
    Factory function to get the appropriate LLM service.
    
    Returns MockLLMService if LLM_PROVIDER is set to "mock",
    otherwise returns the real LLMService.
    
    Args:
        *args: Arguments to pass to the service constructor
        **kwargs: Keyword arguments to pass to the service constructor
        
    Returns:
        LLMService or MockLLMService instance
    """
    provider = kwargs.get("provider") or os.getenv("LLM_PROVIDER", "openai")
    
    if provider.lower() == "mock":
        from app.services.mock_llm_service import MockLLMService
        logger.info("Using Mock LLM Service (no API calls)")
        return MockLLMService(*args, **kwargs)
    else:
        logger.info(f"Using real LLM Service with provider: {provider}")
        return LLMService(*args, **kwargs)


class LLMService:
    """
    Service for generating spell content using LLM providers.
    
    Supports multiple LLM providers:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude 3)
    
    Attributes:
        provider: LLM provider name ("openai" or "anthropic")
        model: Model name to use
        api_key: API key for the provider
        timeout: Request timeout in seconds
        max_tokens: Maximum tokens for response
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize LLM Service.
        
        Args:
            provider: LLM provider ("openai" or "anthropic"). Defaults to env var.
            model: Model name. Defaults to env var.
            api_key: API key. Defaults to env var based on provider.
            timeout: Request timeout in seconds. Defaults to env var.
            max_tokens: Maximum tokens for response. Defaults to env var.
        """
        self.provider = provider or os.getenv("LLM_PROVIDER", "openai")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4-turbo")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "30"))
        self.max_tokens = max_tokens or int(os.getenv("LLM_MAX_TOKENS", "1000"))
        
        # Get API key based on provider
        if api_key:
            self.api_key = api_key
        elif self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
        elif self.provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
        else:
            self.api_key = None
        
        if not self.api_key:
            logger.warning(
                "No API key configured for LLM provider",
                extra={
                    "service": "llm_service",
                    "provider": self.provider
                }
            )
        
        logger.info(
            "LLM Service initialized",
            extra={
                "service": "llm_service",
                "provider": self.provider,
                "model": self.model,
                "timeout": self.timeout,
                "max_tokens": self.max_tokens,
                "has_api_key": bool(self.api_key)
            }
        )
    
    async def generate_spell_content(
        self,
        error_payload: Dict[str, Any],
        pr_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate spell content from error payload using LLM.
        
        Creates a human-readable title, description, and solution code
        based on the error information and PR context.
        
        Args:
            error_payload: Dictionary with error information:
                - error_type: Type of error
                - message: Error message
                - context: Code context
                - stack_trace: Stack trace (optional)
            pr_context: Optional PR context with:
                - repo: Repository name
                - pr_number: PR number
                - files_changed: List of changed files
                
        Returns:
            Dictionary with generated content:
                - title: Short descriptive title
                - description: Detailed explanation
                - solution_code: Suggested solution code
                - confidence_score: Confidence in generation (0-100)
                
        Example:
            llm = LLMService()
            error = {
                "error_type": "TypeError",
                "message": "Cannot read property 'length' of undefined",
                "context": "const len = myArray.length;"
            }
            content = await llm.generate_spell_content(error)
            # Returns: {
            #     "title": "Fix undefined array access",
            #     "description": "Handle cases where array might be undefined...",
            #     "solution_code": "const len = myArray?.length ?? 0;",
            #     "confidence_score": 85
            # }
        """
        if not self.api_key:
            logger.error(f"Cannot generate spell: No API key for {self.provider}")
            return self._fallback_content(error_payload)
        
        try:
            # Build prompt for LLM
            prompt = self._build_prompt(error_payload, pr_context)
            
            # Call appropriate provider
            if self.provider == "openai":
                content = await self._call_openai(prompt)
            elif self.provider == "anthropic":
                content = await self._call_anthropic(prompt)
            else:
                logger.error(f"Unsupported LLM provider: {self.provider}")
                return self._fallback_content(error_payload)
            
            logger.info(
                "Successfully generated spell content",
                extra={
                    "provider": self.provider,
                    "confidence": content.get("confidence_score")
                }
            )
            
            return content
            
        except Exception as e:
            logger.error(
                f"Error generating spell content: {e}",
                exc_info=True,
                extra={"provider": self.provider}
            )
            return self._fallback_content(error_payload)
    
    def _build_prompt(
        self,
        error_payload: Dict[str, Any],
        pr_context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for LLM based on error and context.
        
        Args:
            error_payload: Error information
            pr_context: Optional PR context
            
        Returns:
            Formatted prompt string
        """
        error_type = error_payload.get("error_type", "Unknown")
        message = error_payload.get("message", "")
        context = error_payload.get("context", "")
        
        prompt = f"""You are a code assistant helping to document error patterns and solutions.

Given the following error information, generate a spell (reusable solution pattern):

Error Type: {error_type}
Error Message: {message}
Code Context: {context}
"""
        
        if pr_context:
            repo = pr_context.get("repo", "")
            pr_number = pr_context.get("pr_number", "")
            files = pr_context.get("files_changed", [])
            
            prompt += f"""
Pull Request Context:
- Repository: {repo}
- PR Number: {pr_number}
- Files Changed: {', '.join(files[:5])}
"""
        
        prompt += """
Please provide:
1. A short, descriptive title (max 100 chars)
2. A detailed description explaining the error and solution approach
3. Example solution code or pattern
4. A confidence score (0-100) indicating how confident you are in this solution

Format your response as JSON:
{
  "title": "...",
  "description": "...",
  "solution_code": "...",
  "confidence_score": 85
}
"""
        
        return prompt
    
    async def _call_openai(self, prompt: str) -> Dict[str, str]:
        """
        Call OpenAI API to generate content.
        
        Args:
            prompt: Formatted prompt string
            
        Returns:
            Generated content dictionary
            
        Raises:
            Exception: If API call fails
        """
        try:
            import httpx
            import json
            
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful code assistant that generates structured solutions for code errors."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": 0.7,
                "response_format": {"type": "json_object"}
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                content_text = result["choices"][0]["message"]["content"]
                
                # Parse JSON response
                content = json.loads(content_text)
                
                # Ensure all required fields are present
                return {
                    "title": content.get("title", "Auto-generated spell"),
                    "description": content.get("description", ""),
                    "solution_code": content.get("solution_code", ""),
                    "confidence_score": content.get("confidence_score", 50)
                }
                
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            raise
    
    async def _call_anthropic(self, prompt: str) -> Dict[str, str]:
        """
        Call Anthropic API to generate content.
        
        Args:
            prompt: Formatted prompt string
            
        Returns:
            Generated content dictionary
            
        Raises:
            Exception: If API call fails
        """
        try:
            import httpx
            import json
            
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                content_text = result["content"][0]["text"]
                
                # Parse JSON response
                content = json.loads(content_text)
                
                # Ensure all required fields are present
                return {
                    "title": content.get("title", "Auto-generated spell"),
                    "description": content.get("description", ""),
                    "solution_code": content.get("solution_code", ""),
                    "confidence_score": content.get("confidence_score", 50)
                }
                
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}", exc_info=True)
            raise
    
    async def generate_patch(
        self,
        prompt: str,
        timeout: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        Generate patch using LLM with structured JSON output.
        
        Sends a prompt to the LLM and expects a JSON response with
        patch, files_touched, and rationale fields.
        
        Args:
            prompt: Formatted prompt for patch generation
            timeout: Request timeout in seconds (default: 30)
            
        Returns:
            Dict with keys: patch, files_touched, rationale
            Or: Dict with key: error (if generation fails)
            
        Raises:
            Exception: If API call fails or response cannot be parsed
        """
        if not self.api_key:
            logger.error(
                "Cannot generate patch: No API key configured",
                extra={
                    "service": "llm_service",
                    "provider": self.provider
                }
            )
            return {"error": "LLM API key not configured"}
        
        try:
            # Use provided timeout or default
            request_timeout = timeout or self.timeout
            
            logger.info(
                "Starting patch generation request",
                extra={
                    "service": "llm_service",
                    "provider": self.provider,
                    "model": self.model,
                    "timeout": request_timeout,
                    "prompt_length": len(prompt)
                }
            )
            
            # Call appropriate provider
            if self.provider == "openai":
                result = await self._call_openai_patch(prompt, request_timeout)
            elif self.provider == "anthropic":
                result = await self._call_anthropic_patch(prompt, request_timeout)
            else:
                logger.error(
                    "Unsupported LLM provider",
                    extra={
                        "service": "llm_service",
                        "provider": self.provider
                    }
                )
                return {"error": f"Unsupported LLM provider: {self.provider}"}
            
            logger.info(
                "Successfully generated patch",
                extra={
                    "service": "llm_service",
                    "provider": self.provider,
                    "has_error": "error" in result,
                    "result_keys": list(result.keys())
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Error generating patch",
                exc_info=True,
                extra={
                    "service": "llm_service",
                    "provider": self.provider,
                    "error_type": type(e).__name__,
                    "error_message": safe_log_data(str(e))
                }
            )
            raise
    
    async def _call_openai_patch(self, prompt: str, timeout: int) -> Dict[str, Any]:
        """
        Call OpenAI API to generate patch.
        
        Args:
            prompt: Formatted prompt string
            timeout: Request timeout in seconds
            
        Returns:
            Generated patch dictionary
            
        Raises:
            Exception: If API call fails
        """
        try:
            import httpx
            import json
            
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": 0.3,  # Lower temperature for more deterministic patches
                "response_format": {"type": "json_object"}
            }
            
            logger.debug(
                "Sending request to OpenAI API",
                extra={
                    "service": "llm_service",
                    "provider": "openai",
                    "model": self.model,
                    "url": url,
                    "timeout": timeout,
                    "max_tokens": self.max_tokens
                }
            )
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                # Log response metadata (without sensitive data)
                logger.debug(
                    "Received OpenAI API response",
                    extra={
                        "service": "llm_service",
                        "provider": "openai",
                        "status_code": response.status_code,
                        "has_choices": "choices" in result,
                        "usage": result.get("usage", {})
                    }
                )
                
                content_text = result["choices"][0]["message"]["content"]
                
                # Parse JSON response
                content = json.loads(content_text)
                
                # Check for error in response
                if "error" in content:
                    logger.warning(
                        "OpenAI returned error in content",
                        extra={
                            "service": "llm_service",
                            "provider": "openai",
                            "error": safe_log_data(content["error"])
                        }
                    )
                    return content
                
                # Ensure required fields are present
                if not all(k in content for k in ["patch", "files_touched", "rationale"]):
                    logger.error(
                        "OpenAI response missing required fields",
                        extra={
                            "service": "llm_service",
                            "provider": "openai",
                            "available_fields": list(content.keys()),
                            "required_fields": ["patch", "files_touched", "rationale"]
                        }
                    )
                    return {"error": "LLM response missing required fields"}
                
                logger.info(
                    "Successfully parsed OpenAI response",
                    extra={
                        "service": "llm_service",
                        "provider": "openai",
                        "patch_length": len(content["patch"]),
                        "files_count": len(content["files_touched"]),
                        "tokens_used": result.get("usage", {}).get("total_tokens", 0)
                    }
                )
                
                return content
                
        except Exception as e:
            logger.error(
                "OpenAI API call failed",
                exc_info=True,
                extra={
                    "service": "llm_service",
                    "provider": "openai",
                    "error_type": type(e).__name__,
                    "error_message": safe_log_data(str(e))
                }
            )
            raise
    
    async def _call_anthropic_patch(self, prompt: str, timeout: int) -> Dict[str, Any]:
        """
        Call Anthropic API to generate patch.
        
        Args:
            prompt: Formatted prompt string
            timeout: Request timeout in seconds
            
        Returns:
            Generated patch dictionary
            
        Raises:
            Exception: If API call fails
        """
        try:
            import httpx
            import json
            
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            logger.debug(
                "Sending request to Anthropic API",
                extra={
                    "service": "llm_service",
                    "provider": "anthropic",
                    "model": self.model,
                    "url": url,
                    "timeout": timeout,
                    "max_tokens": self.max_tokens
                }
            )
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                # Log response metadata (without sensitive data)
                logger.debug(
                    "Received Anthropic API response",
                    extra={
                        "service": "llm_service",
                        "provider": "anthropic",
                        "status_code": response.status_code,
                        "has_content": "content" in result,
                        "usage": result.get("usage", {})
                    }
                )
                
                content_text = result["content"][0]["text"]
                
                # Parse JSON response
                content = json.loads(content_text)
                
                # Check for error in response
                if "error" in content:
                    logger.warning(
                        "Anthropic returned error in content",
                        extra={
                            "service": "llm_service",
                            "provider": "anthropic",
                            "error": safe_log_data(content["error"])
                        }
                    )
                    return content
                
                # Ensure required fields are present
                if not all(k in content for k in ["patch", "files_touched", "rationale"]):
                    logger.error(
                        "Anthropic response missing required fields",
                        extra={
                            "service": "llm_service",
                            "provider": "anthropic",
                            "available_fields": list(content.keys()),
                            "required_fields": ["patch", "files_touched", "rationale"]
                        }
                    )
                    return {"error": "LLM response missing required fields"}
                
                logger.info(
                    "Successfully parsed Anthropic response",
                    extra={
                        "service": "llm_service",
                        "provider": "anthropic",
                        "patch_length": len(content["patch"]),
                        "files_count": len(content["files_touched"]),
                        "tokens_used": result.get("usage", {}).get("output_tokens", 0)
                    }
                )
                
                return content
                
        except Exception as e:
            logger.error(
                "Anthropic API call failed",
                exc_info=True,
                extra={
                    "service": "llm_service",
                    "provider": "anthropic",
                    "error_type": type(e).__name__,
                    "error_message": safe_log_data(str(e))
                }
            )
            raise
    
    def _fallback_content(self, error_payload: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate fallback content when LLM is unavailable.
        
        Creates basic spell content from error payload without LLM.
        
        Args:
            error_payload: Error information
            
        Returns:
            Basic content dictionary
        """
        error_type = error_payload.get("error_type", "Unknown")
        message = error_payload.get("message", "")
        
        return {
            "title": f"Fix {error_type}",
            "description": f"Error: {message}\n\nThis spell was auto-generated without LLM assistance. Please review and update with proper solution.",
            "solution_code": "# TODO: Add solution code",
            "confidence_score": 20
        }
