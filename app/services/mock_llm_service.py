"""
Mock LLM Service for testing and demos.

This module provides a mock implementation of the LLM service that returns
realistic-looking patches without making actual API calls. Perfect for:
- Hackathon demos
- Testing without API costs
- Development without API keys
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MockLLMService:
    """
    Mock LLM service that generates realistic patches without API calls.
    
    Returns deterministic, realistic-looking patches based on the input context.
    Useful for demos, testing, and development without incurring API costs.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize Mock LLM Service (accepts any args for compatibility)."""
        # Set attributes to match real LLMService interface
        self.provider = "mock"
        self.model = "mock-model"
        self.api_key = None
        self.timeout = 30
        self.max_tokens = 1000
        
        logger.info("Mock LLM Service initialized (no API calls will be made)")
    
    async def generate_spell_content(
        self,
        error_payload: Dict[str, Any],
        pr_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate mock spell content from error payload.
        
        Returns realistic spell content without calling an actual LLM.
        
        Args:
            error_payload: Dictionary with error information
            pr_context: Optional PR context
            
        Returns:
            Dictionary with generated content
        """
        error_type = error_payload.get("error_type", "Unknown")
        message = error_payload.get("message", "")
        
        logger.info(
            "Generating mock spell content",
            extra={
                "service": "mock_llm_service",
                "error_type": error_type
            }
        )
        
        # Generate realistic mock content
        title = f"Fix {error_type}: {message[:50]}"
        if len(message) > 50:
            title += "..."
        
        description = f"""This spell addresses {error_type} errors that occur when {message.lower()}.

The solution involves:
1. Adding proper null/undefined checks
2. Implementing defensive programming patterns
3. Ensuring proper error handling

This pattern is commonly seen in production codebases and has been validated across multiple repositories."""
        
        solution_code = f"""# Solution for {error_type}

# Add null check before accessing properties
if variable is not None:
    result = variable.property
else:
    result = default_value

# Alternative: Use optional chaining (if supported)
result = variable?.property ?? default_value
"""
        
        return {
            "title": title[:255],  # Respect max length
            "description": description,
            "solution_code": solution_code,
            "confidence_score": 85
        }
    
    async def generate_patch(
        self,
        prompt: str,
        timeout: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        Generate mock patch without calling actual LLM.
        
        Returns a realistic git unified diff patch based on the prompt context.
        
        Args:
            prompt: Formatted prompt for patch generation
            timeout: Request timeout (ignored in mock)
            
        Returns:
            Dict with keys: patch, files_touched, rationale
        """
        logger.info(
            "Generating mock patch",
            extra={
                "service": "mock_llm_service",
                "prompt_length": len(prompt)
            }
        )
        
        # Extract context from prompt to make patch more realistic
        language = "python"
        if "javascript" in prompt.lower() or ".js" in prompt.lower():
            language = "javascript"
        elif "typescript" in prompt.lower() or ".ts" in prompt.lower():
            language = "typescript"
        elif "java" in prompt.lower() and "javascript" not in prompt.lower():
            language = "java"
        
        # Extract repository and file info if present
        repo = "example/repo"
        file_path = "app/main.py" if language == "python" else "src/index.js"
        
        if "repository:" in prompt.lower():
            lines = prompt.split("\n")
            for line in lines:
                if "repository:" in line.lower():
                    repo = line.split(":", 1)[1].strip()
                    break
        
        # Generate realistic patch based on language
        if language == "python":
            patch = f"""diff --git a/{file_path} b/{file_path}
index abc1234..def5678 100644
--- a/{file_path}
+++ b/{file_path}
@@ -15,6 +15,10 @@ def process_user_data(user):
     Process user data and return result.
     '''
+    # Add null check to prevent AttributeError
+    if user is None:
+        logger.warning("Received None user object")
+        return None
+    
     # Extract user information
     user_id = user.id
     user_name = user.name
"""
        elif language in ["javascript", "typescript"]:
            ext = "ts" if language == "typescript" else "js"
            file_path = f"src/index.{ext}"
            patch = f"""diff --git a/{file_path} b/{file_path}
index abc1234..def5678 100644
--- a/{file_path}
+++ b/{file_path}
@@ -10,6 +10,11 @@ export function processUserData(user) {{
   // Process user data and return result
+  
+  // Add null/undefined check to prevent runtime errors
+  if (!user) {{
+    console.warn('Received null or undefined user object');
+    return null;
+  }}
   
   const userId = user.id;
   const userName = user.name;
"""
        else:
            patch = f"""diff --git a/{file_path} b/{file_path}
index abc1234..def5678 100644
--- a/{file_path}
+++ b/{file_path}
@@ -10,6 +10,9 @@ public class Main {{
     public static void processUserData(User user) {{
+        // Add null check to prevent NullPointerException
+        if (user == null) {{
+            return null;
+        }}
         String userId = user.getId();
         String userName = user.getName();
"""
        
        return {
            "patch": patch,
            "files_touched": [file_path],
            "rationale": "Added null/undefined check before accessing object properties to prevent runtime errors. This defensive programming pattern ensures the code handles edge cases gracefully."
        }
