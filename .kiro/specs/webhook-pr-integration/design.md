# Design Document

## Overview

This design document describes the integration of the GitHub webhook endpoint with the PR Processor and Matcher services in the Grimoire Engine backend. The integration completes the end-to-end workflow for processing pull request events and matching them with relevant solution spells.

The design focuses on minimal changes to existing code while establishing a working integration that can be enhanced later with MCP analyzers and sandbox execution.

## Architecture

### Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Webhook Event                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Webhook Endpoint (webhook.py)                   │
│  1. Validate signature                                       │
│  2. Parse payload                                            │
│  3. Call PR Processor ──────────┐                           │
│  4. Construct error payload     │                           │
│  5. Call Matcher Service ───────┼────┐                      │
│  6. Return response              │    │                      │
└──────────────────────────────────┼────┼──────────────────────┘
                                   │    │
                    ┌──────────────▼────┼──────────────────┐
                    │   PR Processor Service                │
                    │   • Fetch PR diff from GitHub         │
                    │   • Parse diff for file changes       │
                    │   • Return processing results         │
                    └──────────────┬────────────────────────┘
                                   │
                                   │ (files_changed)
                                   │
                    ┌──────────────▼────────────────────────┐
                    │   Error Payload Construction          │
                    │   • Use PR metadata as context        │
                    │   • Create placeholder error          │
                    │   • Format for Matcher Service        │
                    └──────────────┬────────────────────────┘
                                   │
                                   │ (error_payload)
                                   │
                         ┌─────────▼─────────────────────────┐
                         │   Matcher Service                 │
                         │   • Extract error characteristics │
                         │   • Query candidate spells        │
                         │   • Rank by similarity            │
                         │   • Return spell IDs              │
                         └─────────┬─────────────────────────┘
                                   │
                                   │ (spell_ids)
                                   │
                         ┌─────────▼─────────────────────────┐
                         │   Webhook Response                │
                         │   • status: "success"             │
                         │   • pr_processing: {...}          │
                         │   • matched_spells: [...]         │
                         └───────────────────────────────────┘
```

## Components and Interfaces

### Modified Component: Webhook Endpoint

**File:** `app/api/webhook.py`

**Current State:**
- Validates webhook signatures ✅
- Parses JSON payload ✅
- Returns success response ✅
- Has TODO comment for PR processing ❌

**Changes Required:**

```python
from app.services.pr_processor import PRProcessor
from app.services.matcher import MatcherService

@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    # ... existing signature validation code ...
    
    # NEW: Process pull_request events
    pr_processing_result = None
    matched_spells = []
    
    if x_github_event == "pull_request":
        try:
            # Initialize PR Processor
            pr_processor = PRProcessor()
            
            # Process the PR event
            pr_processing_result = await pr_processor.process_pr_event(payload)
            
            # If processing succeeded, match with spells
            if pr_processing_result.get("status") == "success":
                # Construct error payload from PR data
                error_payload = _construct_error_payload(
                    pr_processing_result,
                    payload
                )
                
                # Initialize Matcher Service
                matcher = MatcherService(db)
                
                # Match spells
                matched_spells = await matcher.match_spells(error_payload)
                
        except Exception as e:
            logger.error(
                f"Error processing PR event: {e}",
                exc_info=True,
                extra={
                    "repo": payload.get("repository", {}).get("full_name"),
                    "pr_number": payload.get("pull_request", {}).get("number")
                }
            )
            # Continue to return success to prevent GitHub retries
    
    # Return enhanced response
    return {
        "status": "success",
        "event": x_github_event,
        "action": payload.get("action"),
        "pr_processing": pr_processing_result,
        "matched_spells": matched_spells
    }
```

### New Helper Function: Error Payload Construction

**Location:** `app/api/webhook.py`

**Purpose:** Convert PR processing results into error payload format for Matcher Service

```python
def _construct_error_payload(
    pr_result: Dict[str, Any],
    webhook_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Construct error payload from PR processing results.
    
    Creates a placeholder error payload using PR metadata until
    MCP analyzers are integrated for real error extraction.
    
    Args:
        pr_result: Result from PR Processor containing repo, pr_number, files_changed
        webhook_payload: Original GitHub webhook payload
        
    Returns:
        Error payload dictionary with structure:
            {
                "error_type": str,
                "message": str,
                "context": str,
                "stack_trace": str (optional)
            }
    """
    repo = pr_result.get("repo", "unknown")
    pr_number = pr_result.get("pr_number", 0)
    files_changed = pr_result.get("files_changed", [])
    action = webhook_payload.get("action", "unknown")
    
    # Construct context from PR metadata
    context_parts = [
        f"Repository: {repo}",
        f"PR #{pr_number}",
        f"Action: {action}",
        f"Files changed: {len(files_changed)}"
    ]
    
    if files_changed:
        context_parts.append(f"Modified files: {', '.join(files_changed[:5])}")
        if len(files_changed) > 5:
            context_parts.append(f"... and {len(files_changed) - 5} more")
    
    return {
        "error_type": "PullRequestChange",
        "message": f"Pull request {action} in {repo}",
        "context": " | ".join(context_parts),
        "stack_trace": ""
    }
```

## Data Models

### Error Payload Structure

The error payload is a dictionary that bridges PR processing results with the Matcher Service:

```python
{
    "error_type": str,      # Type of error (placeholder: "PullRequestChange")
    "message": str,         # Human-readable message about the PR
    "context": str,         # PR metadata: repo, PR number, files changed
    "stack_trace": str      # Optional, empty for now
}
```

**Example:**
```python
{
    "error_type": "PullRequestChange",
    "message": "Pull request opened in octocat/Hello-World",
    "context": "Repository: octocat/Hello-World | PR #123 | Action: opened | Files changed: 3 | Modified files: app/main.py, tests/test_main.py, README.md",
    "stack_trace": ""
}
```

### Enhanced Webhook Response

The webhook response is extended to include processing results:

```python
{
    "status": str,              # "success" or "error"
    "event": str,               # GitHub event type
    "action": str,              # PR action (opened, synchronize, etc.)
    "pr_processing": {          # NEW: PR processing results
        "repo": str,
        "pr_number": int,
        "files_changed": List[str],
        "status": str,
        "error": str (optional)
    },
    "matched_spells": List[int] # NEW: Ranked spell IDs
}
```

**Example Success Response:**
```python
{
    "status": "success",
    "event": "pull_request",
    "action": "opened",
    "pr_processing": {
        "repo": "octocat/Hello-World",
        "pr_number": 123,
        "files_changed": ["app/main.py", "tests/test_main.py"],
        "status": "success"
    },
    "matched_spells": [5, 12, 3]
}
```

**Example Error Response:**
```python
{
    "status": "success",  # Still 200 to prevent GitHub retries
    "event": "pull_request",
    "action": "opened",
    "pr_processing": {
        "repo": "octocat/Hello-World",
        "pr_number": 123,
        "status": "error",
        "error": "Failed to fetch PR diff"
    },
    "matched_spells": []
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: PR Processor integration preserves webhook success

*For any* valid pull_request webhook payload, even if PR processing fails, the webhook endpoint should return HTTP 200 status to prevent GitHub from retrying the webhook.

**Validates: Requirements 1.3, 5.4**

### Property 2: Error payload construction completeness

*For any* PR processing result containing repo and pr_number, constructing an error payload should produce a dictionary with all required fields (error_type, message, context) populated with non-empty values.

**Validates: Requirements 2.1, 2.5**

### Property 3: Matcher service integration resilience

*For any* error payload, calling the Matcher Service should either return a list of spell IDs or an empty list, but never cause the webhook to fail with an HTTP error status.

**Validates: Requirements 3.4, 3.5, 5.2**

### Property 4: Response structure consistency

*For any* webhook processing outcome (success or failure), the response should always include the status, event, action, pr_processing, and matched_spells fields with appropriate values.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 5: Service failure isolation

*For any* service failure (PR Processor or Matcher Service), the error should be logged with context but should not propagate to cause the webhook endpoint to return an error status.

**Validates: Requirements 5.1, 5.2, 5.3**

## Error Handling

### Error Handling Strategy

**PR Processor Failures:**
- Network errors fetching from GitHub API → Log error, set pr_processing.status = "error"
- Invalid payload structure → Log error, set pr_processing.status = "error"
- GitHub API rate limit → Log error with reset time, set pr_processing.status = "error"
- All failures → Return HTTP 200 with error details in response

**Matcher Service Failures:**
- Database connection errors → Log error, return empty matched_spells array
- Invalid error payload → Log error, return empty matched_spells array
- Query failures → Log error, return empty matched_spells array
- All failures → Return HTTP 200 with empty spell list

**Logging Requirements:**
- All exceptions logged with full stack trace
- Include PR metadata (repo, pr_number) in log context
- Never log sensitive data (tokens, secrets)
- Use appropriate log levels (ERROR for failures, INFO for success)

### Error Response Examples

**PR Processing Failed:**
```python
{
    "status": "success",
    "event": "pull_request",
    "action": "opened",
    "pr_processing": {
        "repo": "octocat/Hello-World",
        "pr_number": 123,
        "status": "error",
        "error": "Failed to fetch PR diff: HTTP 404"
    },
    "matched_spells": []
}
```

**Matcher Service Failed:**
```python
{
    "status": "success",
    "event": "pull_request",
    "action": "opened",
    "pr_processing": {
        "repo": "octocat/Hello-World",
        "pr_number": 123,
        "files_changed": ["app/main.py"],
        "status": "success"
    },
    "matched_spells": []  # Empty due to matcher failure
}
```

## Testing Strategy

### Unit Testing

**Test Coverage:**

1. **Webhook Integration Tests** (`tests/test_webhook.py`)
   - Test PR Processor is called with correct payload
   - Test error payload construction with various PR results
   - Test Matcher Service is called with constructed error payload
   - Test response includes pr_processing and matched_spells
   - Test PR Processor failure handling
   - Test Matcher Service failure handling

2. **Error Payload Construction Tests**
   - Test with minimal PR result (repo, pr_number only)
   - Test with full PR result (including files_changed)
   - Test with empty files_changed list
   - Test with large files_changed list (>5 files)
   - Test all required fields are present and non-empty

3. **Integration Error Handling Tests**
   - Test webhook returns 200 when PR Processor raises exception
   - Test webhook returns 200 when Matcher Service raises exception
   - Test error details are logged appropriately
   - Test matched_spells is empty array on matcher failure

### Property-Based Testing

**Framework:** Hypothesis

**Property Tests:**

```python
# Feature: webhook-pr-integration, Property 1: PR Processor integration preserves webhook success
@given(webhook_payload=st.builds(generate_pr_webhook_payload))
async def test_webhook_always_returns_success(webhook_payload):
    """For any valid PR webhook, endpoint returns 200 even if processing fails."""
    response = await github_webhook(webhook_payload)
    assert response.status_code == 200
```

```python
# Feature: webhook-pr-integration, Property 2: Error payload construction completeness
@given(pr_result=st.builds(generate_pr_result))
def test_error_payload_has_all_fields(pr_result):
    """For any PR result, error payload has all required non-empty fields."""
    error_payload = _construct_error_payload(pr_result, {})
    assert error_payload["error_type"]
    assert error_payload["message"]
    assert error_payload["context"]
    assert "error_type" in error_payload
    assert "message" in error_payload
    assert "context" in error_payload
```

```python
# Feature: webhook-pr-integration, Property 4: Response structure consistency
@given(webhook_payload=st.builds(generate_pr_webhook_payload))
async def test_response_structure_consistent(webhook_payload):
    """For any webhook outcome, response has consistent structure."""
    response = await github_webhook(webhook_payload)
    assert "status" in response
    assert "event" in response
    assert "action" in response
    assert "pr_processing" in response
    assert "matched_spells" in response
```

### Manual Testing

**Test Scenarios:**

1. **Happy Path:**
   - Send valid PR webhook with GITHUB_API_TOKEN configured
   - Verify PR diff is fetched
   - Verify spells are matched
   - Verify response includes all data

2. **No GitHub Token:**
   - Send valid PR webhook without GITHUB_API_TOKEN
   - Verify warning is logged
   - Verify webhook still returns success

3. **GitHub API Failure:**
   - Mock GitHub API to return 404
   - Verify error is logged
   - Verify pr_processing.status = "error"
   - Verify webhook returns 200

4. **No Matching Spells:**
   - Send PR webhook with no spells in database
   - Verify matched_spells is empty array
   - Verify webhook returns success

## Implementation Notes

### Minimal Changes Approach

This integration is designed to make minimal changes to existing code:

1. **No changes to PR Processor** - Use as-is
2. **No changes to Matcher Service** - Use as-is
3. **Only modify webhook.py** - Add integration logic
4. **Add one helper function** - Error payload construction

### Future Enhancements

This integration establishes the foundation for future enhancements:

1. **MCP Analyzer Integration:**
   - Replace `_construct_error_payload()` with real error extraction
   - Call MCP analyzers to get actual errors from code changes
   - Keep the same error payload structure

2. **Sandbox Runner Integration:**
   - Add sandbox execution after PR processing
   - Extract real runtime errors from test execution
   - Feed real errors to Matcher Service

3. **Enhanced Matching:**
   - Add vector database for semantic similarity
   - Improve error payload with more context
   - Use Kiro vibe-code for project-aware matching

### Configuration Requirements

**Environment Variables:**
- `GITHUB_API_TOKEN` - Optional, but recommended for PR diff fetching
- `GITHUB_WEBHOOK_SECRET` - Required, already configured

**No New Dependencies:**
- All required services already exist
- No new packages needed
- No database schema changes

## Deployment Considerations

### Backward Compatibility

The integration maintains backward compatibility:
- Existing response fields unchanged
- New fields added (pr_processing, matched_spells)
- Existing webhook consumers unaffected
- HTTP status codes unchanged

### Performance Impact

Expected performance characteristics:
- PR Processor: ~1-2 seconds (GitHub API call)
- Matcher Service: ~100-500ms (database query + matching)
- Total webhook processing: ~1.5-2.5 seconds
- Acceptable for webhook processing (GitHub timeout: 10 seconds)

### Monitoring and Observability

Recommended monitoring:
- Log all webhook processing attempts
- Track PR processing success/failure rates
- Track matcher service success/failure rates
- Monitor GitHub API rate limit usage
- Alert on high error rates

### Rollback Plan

If issues arise:
1. Comment out PR processing code block
2. Return original simple response
3. Webhook functionality restored immediately
4. No database rollback needed (no schema changes)
