# Quick Setup Guide: Spell Auto-Generation

This guide will help you set up spell auto-generation in 5 minutes.

## Prerequisites

- Python 3.8+
- OpenAI or Anthropic API key
- Running Grimoire Engine instance

## Step 1: Get an API Key

### Option A: OpenAI (Recommended for testing)

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### Option B: Anthropic

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new key
5. Copy the key (starts with `sk-ant-`)

## Step 2: Configure Environment

Edit your `.env` file:

```bash
# Enable auto-generation
AUTO_CREATE_SPELLS=true

# Choose provider (openai or anthropic)
LLM_PROVIDER=openai

# Choose model
LLM_MODEL=gpt-4-turbo

# Add your API key
OPENAI_API_KEY=sk-your-actual-key-here
# OR for Anthropic:
# ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

## Step 3: Run Database Migration

```bash
# Apply the new schema changes
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 52609355075f -> a1b2c3d4e5f6, Add spell auto-generation fields
```

## Step 4: Test Configuration

Run the test script:

```bash
python test_spell_generation.py
```

Expected output:
```
============================================================
Spell Auto-Generation Test Suite
============================================================

Configuration:
  Provider: openai
  Model: gpt-4-turbo
  Auto-create enabled: true
  API Key: sk-proj-ab...xyz ✓

Calling LLM API...
(This may take 10-30 seconds)

✅ SUCCESS! Generated content:
...

🎉 All tests passed! Auto-generation is ready to use.
```

## Step 5: Restart Application

```bash
# If running with uvicorn
uvicorn app.main:app --reload

# If running with Docker
docker-compose restart
```

## Verify It's Working

Send a test webhook or wait for a real PR event. Check logs:

```bash
tail -f logs/app.log | grep "auto-generated"
```

You should see:
```
INFO: Auto-generated spell 42 for owner/repo PR #123
```

## Troubleshooting

### "No API key configured"

- Check your `.env` file has the correct key
- Ensure no extra spaces around the key
- Verify the key starts with `sk-` (OpenAI) or `sk-ant-` (Anthropic)

### "Invalid API key"

- Verify the key is active in your provider dashboard
- Check you haven't exceeded your quota
- Try generating a new key

### "Auto-generation skipped"

- Ensure `AUTO_CREATE_SPELLS=true` (not `false`)
- Check the value is lowercase `true`
- Restart the application after changing `.env`

### Test script fails

```bash
# Check Python environment
python --version  # Should be 3.8+

# Ensure dependencies are installed
pip install -r requirements.txt

# Check .env file exists
ls -la .env

# Verify database is accessible
sqlite3 data/grimoire.db ".tables"
```

## Cost Estimates

### OpenAI GPT-4 Turbo
- ~$0.02 per spell generated
- 50 spells = ~$1.00
- 1000 spells = ~$20.00

### OpenAI GPT-3.5 Turbo (Cheaper)
- ~$0.002 per spell generated
- 500 spells = ~$1.00
- 10,000 spells = ~$20.00

### Anthropic Claude 3.5 Sonnet
- ~$0.01 per spell generated
- 100 spells = ~$1.00
- 2000 spells = ~$20.00

## Recommended Settings

### For Development/Testing
```bash
AUTO_CREATE_SPELLS=true
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo  # Cheaper
LLM_TIMEOUT=30
LLM_MAX_TOKENS=500  # Shorter responses
```

### For Production
```bash
AUTO_CREATE_SPELLS=true
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo  # Better quality
LLM_TIMEOUT=30
LLM_MAX_TOKENS=1000  # Detailed responses
```

### For High Volume (Cost-Conscious)
```bash
AUTO_CREATE_SPELLS=true
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022  # Good balance
LLM_TIMEOUT=30
LLM_MAX_TOKENS=800
```

## Next Steps

1. **Monitor auto-generated spells**: Check the database regularly
   ```sql
   SELECT id, title, confidence_score, created_at 
   FROM spells 
   WHERE auto_generated = 1 
   ORDER BY created_at DESC 
   LIMIT 10;
   ```

2. **Review low-confidence spells**: Update spells with confidence < 70
   ```sql
   SELECT * FROM spells 
   WHERE auto_generated = 1 
   AND confidence_score < 70 
   AND human_reviewed = 0;
   ```

3. **Mark reviewed spells**: After manual review
   ```sql
   UPDATE spells 
   SET human_reviewed = 1 
   WHERE id = 42;
   ```

4. **Set up monitoring**: Track costs and quality metrics

## Support

- Full documentation: See `SPELL_AUTO_GENERATION.md`
- Test script: `python test_spell_generation.py`
- Logs: `tail -f logs/app.log`
- Issues: Check GitHub issues or create a new one

## Quick Reference

| Setting | Values | Default |
|---------|--------|---------|
| `AUTO_CREATE_SPELLS` | true/false | false |
| `LLM_PROVIDER` | openai/anthropic | openai |
| `LLM_MODEL` | gpt-4-turbo, gpt-3.5-turbo, claude-3-5-sonnet-20241022 | gpt-4-turbo |
| `LLM_TIMEOUT` | seconds | 30 |
| `LLM_MAX_TOKENS` | number | 1000 |

---

**Ready to go!** 🚀 Your spell auto-generation is now configured.
