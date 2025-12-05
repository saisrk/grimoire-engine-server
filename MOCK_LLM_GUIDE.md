# Mock LLM Service Guide

## Overview

The Mock LLM Service allows you to run Grimoire Engine without making actual API calls to OpenAI or Anthropic. This is perfect for:

- **Hackathon demos** - No API costs or rate limits
- **Development** - Test without API keys
- **CI/CD** - Run tests without secrets
- **MVP presentations** - Reliable, deterministic responses

## How to Enable

Simply set the `LLM_PROVIDER` environment variable to `mock` in your `.env` file:

```bash
LLM_PROVIDER=mock
```

That's it! No API keys required.

## What It Does

The Mock LLM Service provides realistic-looking responses for:

### 1. Spell Generation
When auto-generating spells from errors, it creates:
- Descriptive titles based on error type
- Detailed descriptions with solution steps
- Example solution code
- Confidence scores (always 85 for consistency)

### 2. Patch Generation
When applying spells to generate patches, it creates:
- Valid git unified diff format
- Language-appropriate code (Python, JavaScript, TypeScript, Java)
- Realistic file paths
- Helpful rationale messages

## Example Output

### Spell Generation
```json
{
  "title": "Fix TypeError: Cannot read property 'length' of undefined",
  "description": "This spell addresses TypeError errors that occur when cannot read property 'length' of undefined...",
  "solution_code": "# Solution for TypeError\n\n# Add null check before accessing properties...",
  "confidence_score": 85
}
```

### Patch Generation
```diff
diff --git a/app/main.py b/app/main.py
index abc1234..def5678 100644
--- a/app/main.py
+++ b/app/main.py
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
```

## Switching Back to Real LLM

To use real OpenAI or Anthropic APIs, simply change the provider:

```bash
# For OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_actual_key_here

# For Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_actual_key_here
```

## Implementation Details

The mock service:
- Returns responses instantly (no network delay)
- Generates deterministic but varied output based on input
- Supports all the same methods as the real LLM service
- Logs clearly that it's using mock mode
- Requires no configuration beyond the provider setting

## Testing

The mock service is automatically used in tests when `LLM_PROVIDER=mock` is set. This ensures:
- Fast test execution
- No API costs during testing
- Consistent, reproducible results
- No need for API keys in CI/CD

## Limitations

The mock service:
- Does not use actual AI/ML models
- Generates template-based responses
- Cannot adapt to complex, nuanced scenarios
- Should not be used in production

For production deployments, always use real LLM providers (OpenAI or Anthropic).
