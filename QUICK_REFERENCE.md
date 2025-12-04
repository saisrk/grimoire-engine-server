# Quick Reference: Spell Auto-Generation

## 🚀 Quick Start Commands

```bash
# 1. Validate configuration
python validate_config.py

# 2. Test auto-generation
python test_spell_generation.py

# 3. Run migration
alembic upgrade head

# 4. Start server
uvicorn app.main:app --reload
```

## 📝 Configuration Checklist

- [ ] Copy `.env.example` to `.env`
- [ ] Set `AUTO_CREATE_SPELLS=true`
- [ ] Choose `LLM_PROVIDER` (openai or anthropic)
- [ ] Set `LLM_MODEL` (gpt-4-turbo or claude-3-5-sonnet-20241022)
- [ ] Add API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`)
- [ ] Run `alembic upgrade head`
- [ ] Test with `python test_spell_generation.py`
- [ ] Restart application

## 🔑 Environment Variables

```bash
# Required for auto-generation
AUTO_CREATE_SPELLS=true
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=sk-your-key-here

# Optional tuning
LLM_TIMEOUT=30
LLM_MAX_TOKENS=1000
```

## 🔗 Get API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/

## 💰 Cost Estimates

| Model | Per Spell | 100 Spells |
|-------|-----------|------------|
| GPT-4 Turbo | $0.02 | $2.00 |
| GPT-3.5 Turbo | $0.002 | $0.20 |
| Claude 3.5 Sonnet | $0.01 | $1.00 |

## 🔍 Check Auto-Generated Spells

```sql
-- View all auto-generated spells
SELECT id, title, confidence_score, created_at
FROM spells
WHERE auto_generated = 1
ORDER BY created_at DESC;

-- View spells needing review
SELECT id, title, confidence_score
FROM spells
WHERE auto_generated = 1
AND human_reviewed = 0
AND confidence_score < 70;

-- Mark spell as reviewed
UPDATE spells
SET human_reviewed = 1
WHERE id = 42;
```

## 📊 API Response

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

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "No API key configured" | Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env` |
| "Invalid API key" | Verify key is active in provider dashboard |
| "Auto-generation skipped" | Set `AUTO_CREATE_SPELLS=true` and restart app |
| Test script fails | Run `pip install -r requirements.txt` |
| Migration fails | Check database path in `DATABASE_URL` |

## 📚 Documentation

- **Quick Setup**: [SETUP_AUTO_GENERATION.md](SETUP_AUTO_GENERATION.md)
- **Full Docs**: [SPELL_AUTO_GENERATION.md](SPELL_AUTO_GENERATION.md)
- **Implementation**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Main README**: [README.md](README.md)

## 🔧 Recommended Models

### Development/Testing
```bash
LLM_MODEL=gpt-3.5-turbo  # Cheapest
```

### Production
```bash
LLM_MODEL=gpt-4-turbo  # Best quality
```

### Balanced
```bash
LLM_MODEL=claude-3-5-sonnet-20241022  # Good quality, reasonable cost
```

## 📝 Logs

```bash
# Watch for auto-generation events
tail -f logs/app.log | grep "auto-generated"

# Check LLM service logs
tail -f logs/app.log | grep "LLM"

# View all webhook events
tail -f logs/app.log | grep "webhook"
```

## ✅ Validation

```bash
# Check configuration
python validate_config.py

# Test LLM connection
python test_spell_generation.py

# Check database
sqlite3 data/grimoire.db "SELECT COUNT(*) FROM spells WHERE auto_generated = 1;"
```

## 🎯 Next Steps After Setup

1. Send a test webhook or wait for a real PR
2. Check logs for auto-generation events
3. Query database for auto-generated spells
4. Review low-confidence spells (< 70)
5. Mark reviewed spells as `human_reviewed = 1`
6. Monitor API costs in provider dashboard

## 🆘 Support

- Run `python validate_config.py` for diagnostics
- Run `python test_spell_generation.py` to test LLM
- Check logs: `tail -f logs/app.log`
- Review documentation in this repository

---

**Quick Reference v1.0** | Last Updated: 2024-12-04
