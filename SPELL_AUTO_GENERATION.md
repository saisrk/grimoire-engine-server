# Spell Auto-Generation Feature

## Overview

The Grimoire Engine now supports automatic spell generation using LLM providers (OpenAI, Anthropic) when no matching spells are found for a given error pattern. This feature enables the system to learn from new error patterns and continuously improve its spell library.

## How It Works

### Flow Diagram

```
GitHub Webhook → PR Processor → Matcher Service
                                      ↓
                                 No matches?
                                      ↓
                            Spell Generator Service
                                      ↓
                        ┌─────────────┴─────────────┐
                        ↓                           ↓
                LLM Service                  Create Spell
            (OpenAI/Anthropic)              in Database
                        ↓                           ↓
            Generate human-readable         Auto-generated
            title, description,             spell record
            and solution code
```

### Process

1. **Webhook receives PR event** - GitHub sends pull request webhook
2. **PR processing** - Fetch diff and extract changed files
3. **Error payload construction** - Build error context from PR metadata
4. **Spell matching** - Search for existing matching spells
5. **Auto-generation trigger** - If no matches found and `AUTO_CREATE_SPELLS=true`
6. **LLM content generation** - Generate human-readable spell content
7. **Database creation** - Save new spell with auto-generation metadata
8. **Response** - Return the auto-generated spell ID

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Enable/disable auto-generation
AUTO_CREATE_SPELLS=false

# LLM provider: "openai" or "anthropic"
LLM_PROVIDER=openai

# Model to use
# OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
# Anthropic: claude-3-5-sonnet-20241022, claude-3-opus-20240229
LLM_MODEL=gpt-4-turbo

# API keys (only one required based on provider)
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Request timeout in seconds
LLM_TIMEOUT=30

# Maximum tokens for LLM response
LLM_MAX_TOKENS=1000
```

### Setup Steps

1. **Choose your LLM provider**:
   - OpenAI: Get API key from https://platform.openai.com/api-keys
   - Anthropic: Get API key from https://console.anthropic.com/

2. **Update `.env` file**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

3. **Run database migration**:
   ```bash
   alembic upgrade head
   ```

4. **Enable auto-generation**:
   ```bash
   # In .env file
   AUTO_CREATE_SPELLS=true
   ```

5. **Restart the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Database Schema Changes

New fields added to `spells` table:

| Field | Type | Description |
|-------|------|-------------|
| `auto_generated` | Integer | 0=manual, 1=auto-generated |
| `confidence_score` | Integer | 0-100, LLM confidence in solution |
| `human_reviewed` | Integer | 0=not reviewed, 1=reviewed by human |

## API Response Changes

Webhook response now includes `auto_generated_spell_id`:

```json
{
  "status": "success",
  "event": "pull_request",
  "action": "opened",
  "pr_processing": {
    "repo": "owner/repo",
    "pr_number": 123,
    "files_changed": ["app/main.py"],
    "status": "success"
  },
  "matched_spells": [42],
  "auto_generated_spell_id": 42
}
```

## Usage Examples

### Example 1: OpenAI with GPT-4

```bash
# .env configuration
AUTO_CREATE_SPELLS=true
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=sk-your-key-here
```

### Example 2: Anthropic with Claude

```bash
# .env configuration
AUTO_CREATE_SPELLS=true
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Example 3: Programmatic Usage

```python
from app.services.spell_generator import SpellGeneratorService
from app.services.llm_service import LLMService
from app.db.database import get_db

# Initialize services
async with get_db() as db:
    llm_service = LLMService(
        provider="openai",
        model="gpt-4-turbo",
        api_key="sk-your-key"
    )
    
    generator = SpellGeneratorService(
        db=db,
        llm_service=llm_service,
        auto_create_enabled=True
    )
    
    # Generate spell
    error_payload = {
        "error_type": "TypeError",
        "message": "Cannot read property 'length' of undefined",
        "context": "const len = myArray.length;"
    }
    
    spell_id = await generator.generate_spell(error_payload)
    print(f"Created spell: {spell_id}")
```

## LLM Prompt Structure

The system sends this prompt to the LLM:

```
You are a code assistant helping to document error patterns and solutions.

Given the following error information, generate a spell (reusable solution pattern):

Error Type: TypeError
Error Message: Cannot read property 'length' of undefined
Code Context: const len = myArray.length;

Pull Request Context:
- Repository: owner/repo
- PR Number: 123
- Files Changed: app/main.js, tests/test.js

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
```

## Monitoring & Telemetry

### Logs

Auto-generation events are logged with structured metadata:

```python
logger.info(
    "Auto-generated spell 42 for owner/repo PR #123",
    extra={
        "spell_id": 42,
        "confidence": 85,
        "error_type": "TypeError",
        "repo": "owner/repo",
        "pr_number": 123
    }
)
```

### Metrics to Track

- Number of auto-generated spells per day
- Average confidence scores
- Auto-generation success/failure rate
- LLM API latency and costs
- Human review rate for auto-generated spells

## Quality Control

### Review Workflow

1. **Query auto-generated spells**:
   ```sql
   SELECT * FROM spells 
   WHERE auto_generated = 1 
   AND human_reviewed = 0 
   ORDER BY confidence_score DESC;
   ```

2. **Review and update**:
   ```python
   # Update spell after human review
   spell.description = "Improved description..."
   spell.solution_code = "Better solution..."
   spell.human_reviewed = 1
   db.commit()
   ```

3. **Filter by confidence**:
   ```sql
   -- High confidence spells (likely good)
   SELECT * FROM spells 
   WHERE auto_generated = 1 
   AND confidence_score >= 80;
   
   -- Low confidence spells (need review)
   SELECT * FROM spells 
   WHERE auto_generated = 1 
   AND confidence_score < 50;
   ```

## Cost Considerations

### OpenAI Pricing (as of Dec 2024)

- GPT-4 Turbo: ~$0.01 per 1K input tokens, ~$0.03 per 1K output tokens
- GPT-3.5 Turbo: ~$0.0005 per 1K input tokens, ~$0.0015 per 1K output tokens

### Anthropic Pricing (as of Dec 2024)

- Claude 3.5 Sonnet: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- Claude 3 Opus: ~$0.015 per 1K input tokens, ~$0.075 per 1K output tokens

### Cost Mitigation

1. **Use cheaper models for initial generation**: Start with GPT-3.5 or Claude Sonnet
2. **Set rate limits**: Limit auto-generation to N spells per hour
3. **Cache similar errors**: Don't regenerate for very similar error patterns
4. **Batch processing**: Generate multiple spells in one request when possible

## Troubleshooting

### Auto-generation not working

1. Check `AUTO_CREATE_SPELLS` is set to `true`
2. Verify API key is correct
3. Check logs for LLM API errors
4. Ensure database migration was run

### LLM API errors

```python
# Check logs for detailed error messages
tail -f logs/app.log | grep "LLM"

# Common issues:
# - Invalid API key
# - Rate limit exceeded
# - Network timeout
# - Invalid model name
```

### Low quality generations

1. Adjust `LLM_MODEL` to use more capable model (e.g., GPT-4)
2. Increase `LLM_MAX_TOKENS` for longer responses
3. Review and update low confidence spells manually
4. Consider adding more context to error payloads

## Future Enhancements

- [ ] Vector embeddings for semantic similarity
- [ ] Deduplication before creating new spells
- [ ] Batch generation for multiple errors
- [ ] Human-in-the-loop review workflow
- [ ] A/B testing different LLM providers
- [ ] Fine-tuned models for specific error types
- [ ] Integration with code analysis tools (MCP)
- [ ] Automatic spell improvement based on usage

## Security Considerations

1. **API Key Protection**: Never commit API keys to version control
2. **Rate Limiting**: Implement rate limits to prevent abuse
3. **Input Validation**: Sanitize error payloads before sending to LLM
4. **Output Validation**: Validate LLM responses before database insertion
5. **Access Control**: Restrict who can enable auto-generation

## Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- Review configuration: `cat .env`
- Test LLM connection: Use the test script (see below)

### Test Script

```python
# test_llm.py
import asyncio
from app.services.llm_service import LLMService

async def test():
    llm = LLMService()
    error = {
        "error_type": "TypeError",
        "message": "Test error",
        "context": "test context"
    }
    result = await llm.generate_spell_content(error)
    print(result)

asyncio.run(test())
```

Run with: `python test_llm.py`
