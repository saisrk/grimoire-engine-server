# Design Document

## Overview

This design document describes the addition of repository configuration management and webhook execution logging to the Grimoire Engine Backend. The design introduces two new database tables (repository_configs and webhook_execution_logs), new API endpoints for managing repositories and viewing logs, and automatic logging integration into the existing webhook endpoint.

The design follows the existing patterns in the codebase: FastAPI for REST APIs, SQLAlchemy async ORM for database access, Pydantic for schema validation, and Alembic for database migrations.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Applications                          │
│  (Web UI, CLI tools, CI/CD integrations)                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ HTTP REST API
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                   FastAPI Application                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Repository Config API (/api/repo-configs)               │  │
│  │  • POST   /api/repo-configs (create)                     │  │
│  │  • GET    /api/repo-configs (list all)                   │  │
│  │  • GET    /api/repo-configs/{id} (get one)               │  │
│  │  • PUT    /api/repo-configs/{id} (update)                │  │
│  │  • DELETE /api/repo-configs/{id} (delete)                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Webhook Logs API (/api/webhook-logs)                    │  │
│  │  • GET /api/webhook-logs (list all with filters)         │  │
│  │  • GET /api/webhook-logs/{id} (get one)                  │  │
│  │  • GET /api/repo-configs/{id}/logs (logs by repo)        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Webhook Endpoint (/webhook/github)                      │  │
│  │  • Receives GitHub webhooks                              │  │
│  │  • Processes PR events                                   │  │
│  │  • Creates execution logs automatically                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ SQLAlchemy Async ORM
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                   Database (SQLite)                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  repository_configs                                       │  │
│  │  • id, repo_name, webhook_url, enabled                   │  │
│  │  • created_at, updated_at                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  webhook_execution_logs                                   │  │
│  │  • id, repo_config_id, repo_name, pr_number              │  │
│  │  • event_type, action, status, matched_spell_ids         │  │
│  │  • auto_generated_spell_id, error_message                │  │
│  │  • pr_processing_result, execution_duration_ms           │  │
│  │  • executed_at                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  spells (existing)                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  users (existing)                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Webhook Processing Flow with Logging

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Webhook Event                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Webhook Endpoint (webhook.py)                   │
│  1. Start timer                                              │
│  2. Validate signature                                       │
│  3. Parse payload                                            │
│  4. Process PR (existing logic)                              │
│  5. Match spells (existing logic)                            │
│  6. Create execution log ────────┐                          │
│  7. Return response               │                          │
└───────────────────────────────────┼──────────────────────────┘
                                    │
                     ┌──────────────▼──────────────────────┐
                     │   Create Webhook Execution Log      │
                     │   • Capture all processing data     │
                     │   • Store in database               │
                     │   • Link to repo config if exists   │
                     │   • Never fail webhook on log error │
                     └─────────────────────────────────────┘
```

## Components and Interfaces

### New Model: RepositoryConfig

**File:** `app/models/repository_config.py`

**Purpose:** Store configuration for repositories that have webhook integration enabled

**SQLAlchemy Model:**
```python
class RepositoryConfig(Base):
    __tablename__ = "repository_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(255), nullable=False, unique=True, index=True)
    webhook_url = Column(String(500), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Pydantic Schemas:**
```python
class RepositoryConfigBase(BaseModel):
    repo_name: str = Field(..., pattern=r"^[\w\-\.]+/[\w\-\.]+$")
    webhook_url: str = Field(..., min_length=1, max_length=500)
    enabled: bool = True

class RepositoryConfigCreate(RepositoryConfigBase):
    pass

class RepositoryConfigUpdate(BaseModel):
    webhook_url: Optional[str] = None
    enabled: Optional[bool] = None

class RepositoryConfigResponse(RepositoryConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    webhook_count: int = 0  # Computed field
    last_webhook_at: Optional[datetime] = None  # Computed field
```

### New Model: WebhookExecutionLog

**File:** `app/models/webhook_execution_log.py`

**Purpose:** Store detailed logs of each webhook execution

**SQLAlchemy Model:**
```python
class WebhookExecutionLog(Base):
    __tablename__ = "webhook_execution_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_config_id = Column(Integer, ForeignKey("repository_configs.id", ondelete="CASCADE"), nullable=True, index=True)
    repo_name = Column(String(255), nullable=False, index=True)
    pr_number = Column(Integer, nullable=True)
    event_type = Column(String(50), nullable=False)
    action = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, index=True)  # success, partial_success, error
    matched_spell_ids = Column(Text, nullable=True)  # JSON array as string
    auto_generated_spell_id = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    pr_processing_result = Column(Text, nullable=True)  # JSON object as string
    execution_duration_ms = Column(Integer, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
```

**Pydantic Schemas:**
```python
class WebhookExecutionLogResponse(BaseModel):
    id: int
    repo_config_id: Optional[int]
    repo_name: str
    pr_number: Optional[int]
    event_type: str
    action: Optional[str]
    status: str
    matched_spell_ids: List[int]
    auto_generated_spell_id: Optional[int]
    error_message: Optional[str]
    pr_processing_result: Optional[Dict[str, Any]]
    execution_duration_ms: Optional[int]
    executed_at: datetime
    
    # Computed fields
    files_changed_count: int = 0
    spell_match_attempted: bool = False
    spell_generation_attempted: bool = False
```

### New API: Repository Config Endpoints

**File:** `app/api/repo_configs.py`

**Endpoints:**

1. **POST /api/repo-configs** - Create new repository configuration
2. **GET /api/repo-configs** - List all repository configurations
3. **GET /api/repo-configs/{id}** - Get specific repository configuration
4. **PUT /api/repo-configs/{id}** - Update repository configuration
5. **DELETE /api/repo-configs/{id}** - Delete repository configuration
6. **GET /api/repo-configs/{id}/logs** - Get webhook logs for specific repository

### New API: Webhook Logs Endpoints

**File:** `app/api/webhook_logs.py`

**Endpoints:**

1. **GET /api/webhook-logs** - List all webhook execution logs with filtering
   - Query params: status, start_date, end_date, skip, limit
2. **GET /api/webhook-logs/{id}** - Get specific webhook execution log

### Modified Component: Webhook Endpoint

**File:** `app/api/webhook.py`

**Changes Required:**

Add logging service integration at the end of webhook processing:

```python
@router.post("/webhook/github")
async def github_webhook(...):
    start_time = time.time()
    
    # ... existing webhook processing logic ...
    
    # NEW: Create execution log before returning
    try:
        execution_duration_ms = int((time.time() - start_time) * 1000)
        
        await _create_execution_log(
            db=db,
            repo_name=repo_name,
            pr_number=pr_number,
            event_type=x_github_event,
            action=payload.get("action"),
            status=_determine_status(pr_processing_result, matched_spells),
            matched_spell_ids=matched_spells,
            auto_generated_spell_id=auto_generated_spell_id,
            error_message=pr_processing_result.get("error") if pr_processing_result else None,
            pr_processing_result=pr_processing_result,
            execution_duration_ms=execution_duration_ms
        )
    except Exception as e:
        # Never fail webhook due to logging errors
        logger.error(f"Failed to create execution log: {e}", exc_info=True)
    
    return {
        "status": "success",
        ...
    }
```

### New Service: Webhook Logging Service

**File:** `app/services/webhook_logger.py`

**Purpose:** Encapsulate webhook execution log creation logic

```python
async def create_execution_log(
    db: AsyncSession,
    repo_name: str,
    event_type: str,
    status: str,
    pr_number: Optional[int] = None,
    action: Optional[str] = None,
    matched_spell_ids: Optional[List[int]] = None,
    auto_generated_spell_id: Optional[int] = None,
    error_message: Optional[str] = None,
    pr_processing_result: Optional[Dict[str, Any]] = None,
    execution_duration_ms: Optional[int] = None
) -> WebhookExecutionLog:
    """Create a webhook execution log entry."""
    
    # Find associated repo config if exists
    repo_config_id = await _find_repo_config_id(db, repo_name)
    
    # Create log entry
    log_entry = WebhookExecutionLog(
        repo_config_id=repo_config_id,
        repo_name=repo_name,
        pr_number=pr_number,
        event_type=event_type,
        action=action,
        status=status,
        matched_spell_ids=json.dumps(matched_spell_ids or []),
        auto_generated_spell_id=auto_generated_spell_id,
        error_message=error_message,
        pr_processing_result=json.dumps(pr_processing_result) if pr_processing_result else None,
        execution_duration_ms=execution_duration_ms
    )
    
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    
    return log_entry
```

## Data Models

### Repository Configuration Data Model

```python
{
    "id": 1,
    "repo_name": "octocat/Hello-World",
    "webhook_url": "https://grimoire.example.com/webhook/github",
    "enabled": true,
    "created_at": "2025-12-05T10:00:00Z",
    "updated_at": "2025-12-05T12:00:00Z",
    "webhook_count": 15,
    "last_webhook_at": "2025-12-05T11:45:00Z"
}
```

### Webhook Execution Log Data Model

```python
{
    "id": 42,
    "repo_config_id": 1,
    "repo_name": "octocat/Hello-World",
    "pr_number": 123,
    "event_type": "pull_request",
    "action": "opened",
    "status": "success",
    "matched_spell_ids": [5, 12, 3],
    "auto_generated_spell_id": null,
    "error_message": null,
    "pr_processing_result": {
        "repo": "octocat/Hello-World",
        "pr_number": 123,
        "files_changed": ["app/main.py", "tests/test_main.py"],
        "status": "success"
    },
    "execution_duration_ms": 1850,
    "executed_at": "2025-12-05T11:45:23Z",
    "files_changed_count": 2,
    "spell_match_attempted": true,
    "spell_generation_attempted": false
}
```

### Status Values

**Execution Status:**
- `success` - Webhook processed successfully, spells matched
- `partial_success` - Webhook processed but with warnings (e.g., no spells matched)
- `error` - Webhook processing failed

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Repository creation persistence

*For any* valid repository name and webhook URL, creating a repository configuration should result in a record that can be retrieved from the database with all fields intact.

**Validates: Requirements 1.1, 1.4, 1.5**

### Property 2: Repository name format validation

*For any* string, the system should accept it as a repository name only if it matches the format "owner/repo" (alphanumeric, hyphens, dots, underscores allowed).

**Validates: Requirements 1.2**

### Property 3: Repository uniqueness enforcement

*For any* repository name, attempting to create a second repository configuration with the same name should result in an error, and the database should contain only one record for that name.

**Validates: Requirements 1.3**

### Property 4: Repository list ordering

*For any* set of repository configurations, listing them should return all configurations ordered by creation date in descending order (newest first).

**Validates: Requirements 2.1**

### Property 5: Repository update persistence

*For any* existing repository configuration, updating its webhook URL or enabled status should result in those changes being persisted and retrievable, with the updated_at timestamp being greater than the original.

**Validates: Requirements 3.1, 3.2, 3.4, 3.5**

### Property 6: Cascade deletion

*For any* repository configuration with associated webhook execution logs, deleting the repository configuration should also delete all associated logs.

**Validates: Requirements 4.1, 4.2**

### Property 7: Automatic webhook logging

*For any* webhook processing (successful or failed), a webhook execution log should be created in the database with all required fields populated.

**Validates: Requirements 5.1, 5.2, 9.1, 9.2**

### Property 8: Error capture in logs

*For any* webhook processing that encounters an error, the execution log should contain the error message and have status set to "error".

**Validates: Requirements 5.4, 9.3**

### Property 9: Spell matching capture

*For any* webhook processing that successfully matches spells, the execution log should contain all matched spell IDs in the matched_spell_ids field.

**Validates: Requirements 5.3, 9.2**

### Property 10: Repository log filtering

*For any* repository configuration, requesting logs for that repository should return only logs associated with that repository, ordered by execution time descending.

**Validates: Requirements 6.1**

### Property 11: Log status filtering

*For any* set of webhook execution logs with different statuses, filtering by a specific status should return only logs with that status.

**Validates: Requirements 7.3**

### Property 12: Log date range filtering

*For any* set of webhook execution logs with different execution times, filtering by a date range should return only logs within that range.

**Validates: Requirements 7.4**

### Property 13: Webhook logging resilience

*For any* webhook processing, if logging fails, the webhook should still return HTTP 200 and the original response should be unaffected.

**Validates: Requirements 9.4**

### Property 14: Execution duration capture

*For any* webhook processing, the execution log should contain a positive execution_duration_ms value representing the time from webhook receipt to response.

**Validates: Requirements 9.5, 10.3**

### Property 15: PR metadata capture

*For any* pull_request webhook, the execution log should capture the number of files changed and the list of changed file paths from the PR processing result.

**Validates: Requirements 10.1, 10.2**

## Error Handling

### Repository Configuration Errors

**Validation Errors:**
- Invalid repository name format → HTTP 400 with error message
- Missing required fields → HTTP 400 with field validation errors
- Duplicate repository name → HTTP 409 Conflict with error message

**Not Found Errors:**
- Repository config ID doesn't exist → HTTP 404 with error message
- Applies to: GET, PUT, DELETE operations

**Database Errors:**
- Connection failures → HTTP 500 with generic error message
- Constraint violations → HTTP 400 or 409 depending on constraint
- Transaction failures → HTTP 500 with generic error message

### Webhook Logging Errors

**Logging Failures:**
- Database unavailable during logging → Log error, webhook returns success
- Invalid data during logging → Log error, webhook returns success
- Foreign key constraint failure → Log error, create log without repo_config_id

**Query Errors:**
- Invalid filter parameters → HTTP 400 with validation errors
- Invalid pagination parameters → HTTP 400 with validation errors
- Log ID doesn't exist → HTTP 404 with error message

### Error Response Format

All API errors follow this format:
```python
{
    "detail": "Error message describing what went wrong"
}
```

For validation errors:
```python
{
    "detail": [
        {
            "loc": ["body", "repo_name"],
            "msg": "string does not match regex pattern",
            "type": "value_error.str.regex"
        }
    ]
}
```

## Testing Strategy

### Unit Testing

**Repository Config API Tests** (`tests/test_repo_config_api.py`):
- Test create repository config with valid data
- Test create repository config with invalid repo name format
- Test create duplicate repository config returns 409
- Test list repository configs returns all configs ordered by date
- Test list repository configs includes webhook count
- Test get repository config by ID
- Test get non-existent repository config returns 404
- Test update repository config webhook URL
- Test update repository config enabled status
- Test update non-existent repository config returns 404
- Test delete repository config
- Test delete repository config cascades to logs
- Test delete non-existent repository config returns 404

**Webhook Logs API Tests** (`tests/test_webhook_logs_api.py`):
- Test list all webhook logs ordered by execution time
- Test list webhook logs with status filter
- Test list webhook logs with date range filter
- Test list webhook logs with pagination
- Test get webhook logs by repository ID
- Test get webhook logs for repository with no logs returns empty list
- Test get webhook log by ID
- Test get non-existent webhook log returns 404

**Webhook Logging Integration Tests** (`tests/test_webhook_logging.py`):
- Test webhook creates execution log on success
- Test webhook creates execution log on PR processing error
- Test webhook creates execution log on matcher error
- Test webhook includes matched spell IDs in log
- Test webhook includes auto-generated spell ID in log
- Test webhook includes execution duration in log
- Test webhook includes PR metadata in log
- Test webhook still succeeds if logging fails
- Test webhook links log to repo config if exists
- Test webhook creates log without repo config if none exists

### Property-Based Testing

**Framework:** Hypothesis (Python)

**Property Tests:**

```python
# Feature: repo-config-and-logging, Property 1: Repository creation persistence
@given(repo_name=st.from_regex(r'^[\w\-\.]+/[\w\-\.]+$'), webhook_url=st.text(min_size=1))
async def test_repository_creation_persistence(repo_name, webhook_url):
    """For any valid repo name and webhook URL, creation should persist all fields."""
    created = await create_repo_config(repo_name, webhook_url)
    retrieved = await get_repo_config(created.id)
    assert retrieved.repo_name == repo_name
    assert retrieved.webhook_url == webhook_url
    assert retrieved.id is not None
```

```python
# Feature: repo-config-and-logging, Property 2: Repository name format validation
@given(repo_name=st.text())
async def test_repository_name_validation(repo_name):
    """For any string, only valid owner/repo format should be accepted."""
    is_valid_format = bool(re.match(r'^[\w\-\.]+/[\w\-\.]+$', repo_name))
    try:
        await create_repo_config(repo_name, "http://example.com")
        assert is_valid_format, "Invalid format was accepted"
    except ValidationError:
        assert not is_valid_format, "Valid format was rejected"
```

```python
# Feature: repo-config-and-logging, Property 3: Repository uniqueness enforcement
@given(repo_name=st.from_regex(r'^[\w\-\.]+/[\w\-\.]+$'))
async def test_repository_uniqueness(repo_name):
    """For any repo name, creating twice should fail on second attempt."""
    await create_repo_config(repo_name, "http://example.com")
    with pytest.raises(HTTPException) as exc:
        await create_repo_config(repo_name, "http://example.com")
    assert exc.value.status_code == 409
```

```python
# Feature: repo-config-and-logging, Property 7: Automatic webhook logging
@given(webhook_payload=st.builds(generate_webhook_payload))
async def test_automatic_webhook_logging(webhook_payload):
    """For any webhook processing, a log should be created."""
    logs_before = await count_webhook_logs()
    await process_webhook(webhook_payload)
    logs_after = await count_webhook_logs()
    assert logs_after == logs_before + 1
```

```python
# Feature: repo-config-and-logging, Property 10: Repository log filtering
@given(repo_configs=st.lists(st.builds(generate_repo_config), min_size=2))
async def test_repository_log_filtering(repo_configs):
    """For any repository, its logs should only include logs for that repo."""
    # Create repos and logs
    for config in repo_configs:
        await create_repo_config(config)
        await create_webhook_log(repo_name=config.repo_name)
    
    # Get logs for first repo
    target_repo = repo_configs[0]
    logs = await get_logs_by_repo(target_repo.id)
    
    # All logs should be for target repo
    assert all(log.repo_name == target_repo.repo_name for log in logs)
```

```python
# Feature: repo-config-and-logging, Property 13: Webhook logging resilience
@given(webhook_payload=st.builds(generate_webhook_payload))
async def test_webhook_logging_resilience(webhook_payload, monkeypatch):
    """For any webhook, logging failure should not affect webhook success."""
    # Mock logging to fail
    monkeypatch.setattr('app.services.webhook_logger.create_execution_log', 
                       lambda *args, **kwargs: raise_exception())
    
    response = await process_webhook(webhook_payload)
    assert response.status_code == 200
```

### Integration Testing

**End-to-End Workflow Tests:**

1. **Complete Repository Lifecycle:**
   - Create repository config
   - Trigger webhook for that repository
   - Verify execution log is created and linked
   - List logs for repository
   - Update repository config
   - Delete repository config
   - Verify logs are also deleted

2. **Multi-Repository Webhook Processing:**
   - Create multiple repository configs
   - Trigger webhooks for different repositories
   - Verify logs are correctly associated
   - Filter logs by repository
   - Filter logs by status
   - Verify pagination works correctly

3. **Error Handling Flow:**
   - Trigger webhook that causes PR processing error
   - Verify log captures error details
   - Trigger webhook that causes matcher error
   - Verify log captures error but webhook succeeds
   - Simulate logging failure
   - Verify webhook still succeeds

## Implementation Notes

### Database Migration Strategy

**Migration File:** `alembic/versions/xxx_add_repo_config_and_logging.py`

**Order of Operations:**
1. Create `repository_configs` table
2. Create `webhook_execution_logs` table with foreign key to `repository_configs`
3. Add indexes on frequently queried columns
4. Add cascade delete constraint

**Indexes:**
- `repository_configs.repo_name` (unique)
- `webhook_execution_logs.repo_config_id`
- `webhook_execution_logs.repo_name`
- `webhook_execution_logs.status`
- `webhook_execution_logs.executed_at`

### JSON Storage Strategy

**Storing Lists and Objects:**
- `matched_spell_ids`: Store as JSON string, parse on retrieval
- `pr_processing_result`: Store as JSON string, parse on retrieval

**Rationale:**
- SQLite doesn't have native JSON array type
- Keeps schema simple
- Easy to migrate to PostgreSQL JSON type later

### Performance Considerations

**Query Optimization:**
- Use indexes on filter columns (status, executed_at, repo_name)
- Implement pagination to limit result set size
- Use eager loading for related data (repo config with logs)

**Expected Performance:**
- Repository config CRUD: <50ms
- Webhook log creation: <100ms (should not slow webhook)
- Log listing with filters: <200ms for 1000 records
- Cascade delete: <500ms for repo with 100 logs

### Backward Compatibility

**Webhook Endpoint:**
- Logging is additive, doesn't change existing response
- Webhook continues to work even if logging fails
- No breaking changes to webhook API

**Database:**
- New tables don't affect existing tables
- No changes to existing schemas
- Migration is forward-only (no data migration needed)

## Deployment Considerations

### Migration Steps

1. **Deploy Database Migration:**
   ```bash
   alembic upgrade head
   ```

2. **Deploy Application Code:**
   - New models and schemas
   - New API endpoints
   - Modified webhook endpoint with logging

3. **Verify Deployment:**
   - Test repository config CRUD operations
   - Trigger test webhook and verify log creation
   - Query logs through API

### Rollback Plan

**If Issues Arise:**

1. **Rollback Application:**
   - Deploy previous version without new endpoints
   - Webhook continues to work (logging code is try-catch wrapped)

2. **Rollback Database (if needed):**
   ```bash
   alembic downgrade -1
   ```
   - Drops new tables
   - No data loss for existing tables

### Monitoring and Observability

**Metrics to Track:**
- Repository config creation rate
- Webhook log creation rate
- Webhook log creation failures
- API endpoint response times
- Database query performance

**Alerts:**
- High rate of webhook logging failures
- Slow webhook log queries (>500ms)
- Database connection errors
- Cascade delete taking too long (>1s)

### Security Considerations

**API Authentication:**
- Repository config endpoints should require authentication
- Webhook logs endpoints should require authentication
- Use existing JWT authentication from user auth system

**Data Privacy:**
- Don't log sensitive data (tokens, secrets, passwords)
- Sanitize error messages before storing
- Consider data retention policy for old logs

**Input Validation:**
- Validate repository name format strictly
- Validate webhook URL format
- Sanitize all user inputs
- Use Pydantic schemas for validation

## Future Enhancements

### Phase 2 Enhancements

1. **GitHub Webhook Registration:**
   - Automatically register webhooks with GitHub API
   - Store webhook secret per repository
   - Validate signatures per repository

2. **Log Retention Policy:**
   - Automatically delete logs older than N days
   - Archive old logs to cold storage
   - Configurable retention per repository

3. **Enhanced Filtering:**
   - Filter by PR number
   - Filter by matched spell IDs
   - Full-text search in error messages

4. **Webhook Replay:**
   - Store original webhook payload
   - Allow replaying failed webhooks
   - Reprocess with updated spells

5. **Analytics Dashboard:**
   - Webhook success rate over time
   - Most common errors
   - Most matched spells
   - Repository activity heatmap

### Migration to PostgreSQL

When migrating from SQLite to PostgreSQL:
- Change `matched_spell_ids` from TEXT to JSONB
- Change `pr_processing_result` from TEXT to JSONB
- Add GIN indexes on JSONB columns
- Use native array type for spell IDs
