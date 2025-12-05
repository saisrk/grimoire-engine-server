# Hackathon Demo Setup Guide

## ✅ Mock LLM Service - Ready for Demo!

Your Grimoire Engine is now configured with a **Mock LLM Service** that works without any API keys or costs. Perfect for your hackathon demo!

## Quick Start

### 1. Verify Configuration

Check your `.env` file has:
```bash
LLM_PROVIDER=mock
AUTO_CREATE_SPELLS=true
```

### 2. Start the Server

```bash
# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test the Mock LLM

Run the test script:
```bash
python test_mock_llm.py
```

You should see:
```
✅ All Mock LLM Tests Passed!
```

## What's Working

### ✅ Spell Application (POST /api/spells/{id}/apply)
- Generates realistic patches without API calls
- Returns valid git unified diffs
- Works with any spell in your database
- No API key required

### ✅ Auto Spell Generation (Webhook)
- Creates spells automatically when no matches found
- Generates titles, descriptions, and solution code
- No API costs or rate limits

### ✅ All Existing Features
- Spell CRUD operations
- Webhook processing
- PR diff fetching
- Spell matching
- Webhook logging

## Demo Flow

### Scenario 1: Apply a Spell

```bash
# 1. Get a spell ID
curl http://localhost:8000/api/spells

# 2. Apply the spell (replace {spell_id} with actual ID)
curl -X POST http://localhost:8000/api/spells/1/apply \
  -H "Content-Type: application/json" \
  -d '{
    "failing_context": {
      "repository": "myorg/myrepo",
      "commit_sha": "abc123def456",
      "language": "python",
      "failing_test": "test_user_login",
      "stack_trace": "AssertionError: user is None"
    }
  }'
```

**Expected Response:**
```json
{
  "application_id": 1,
  "patch": "diff --git a/app/main.py b/app/main.py\n...",
  "files_touched": ["app/main.py"],
  "rationale": "Added null check before accessing user object...",
  "created_at": "2025-12-05T10:30:00Z"
}
```

### Scenario 2: Webhook with Auto-Generation

```bash
# Send a PR webhook (will auto-generate spell if no match)
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-Hub-Signature-256: sha256=dummy" \
  -d @webhook_payload.json
```

**Expected Response:**
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
  "matched_spells": [5],
  "auto_generated_spell_id": 5
}
```

## Key Benefits for Demo

### 🚀 Fast & Reliable
- Instant responses (no network latency)
- No rate limits or quotas
- Deterministic output for consistent demos

### 💰 Zero Cost
- No API charges
- No credit card required
- Unlimited usage

### 🔒 No Secrets Required
- No API keys to manage
- Safe for public demos
- Works in any environment

### 🎯 Realistic Output
- Valid git diff format
- Language-appropriate code
- Professional-looking patches

## Switching to Real LLM (Post-Hackathon)

When you're ready to use real AI:

1. Get an API key from OpenAI or Anthropic
2. Update `.env`:
   ```bash
   LLM_PROVIDER=openai  # or anthropic
   OPENAI_API_KEY=your_real_key_here
   ```
3. Restart the server

That's it! No code changes needed.

## Troubleshooting

### Mock LLM Not Working?

Check:
1. `.env` has `LLM_PROVIDER=mock`
2. Server was restarted after changing `.env`
3. No typos in environment variable

### Want to See Mock in Action?

Run the test:
```bash
python test_mock_llm.py
```

### Need Help?

Check the logs:
```bash
# Server logs will show:
# "Using Mock LLM Service (no API calls)"
```

## Demo Tips

1. **Show the .env file** - Highlight `LLM_PROVIDER=mock` to show no API keys needed
2. **Run test_mock_llm.py** - Quick visual proof it works
3. **Apply a spell live** - Show the patch generation in real-time
4. **Trigger webhook** - Demonstrate auto-generation
5. **Check logs** - Show "Mock LLM Service" messages

## Files Added

- `app/services/mock_llm_service.py` - Mock implementation
- `test_mock_llm.py` - Test script
- `MOCK_LLM_GUIDE.md` - Detailed documentation
- `HACKATHON_SETUP.md` - This file

## Files Modified

- `app/services/llm_service.py` - Added factory function
- `app/services/spell_generator.py` - Uses factory
- `app/api/spells.py` - Uses factory
- `.env` - Set to mock mode
- `.env.example` - Documented mock option

---

**You're all set for the hackathon! 🎉**

The mock LLM service is production-ready for demos and will give you reliable, impressive results without any API costs or complexity.
