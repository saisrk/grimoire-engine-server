# Grimoire Engine Backend - API Documentation

## Overview

This document provides comprehensive documentation for the Grimoire Engine Backend API, focusing on the Repository Configuration and Webhook Logging features.

## Table of Contents

- [Authentication](#authentication)
- [Repository Configuration API](#repository-configuration-api)
- [Webhook Logs API](#webhook-logs-api)
- [Error Responses](#error-responses)
- [Data Models](#data-models)

---

## Authentication

All API endpoints (except the webhook endpoint) require authentication using JWT Bearer tokens.

### How to Authenticate

Include the JWT token in the `Authorization` header:

```http
Authorization: Bearer <your-jwt-token>
```

### Getting a Token

Obtain a JWT token by authenticating through the `/api/auth/login` endpoint (see User Authentication API documentation).

### Error Response

If authentication fails, you'll receive a `401 Unauthorized` response:

```json
{
  "detail": "Could not validate credentials"
}
```

---

## Repository Configuration API

Manage GitHub repository configurations for webhook integration.

### Base URL

```
/api/repo-configs
```

### Endpoints

#### 1. Create Repository Configuration

Register a new GitHub repository for webhook integration.

**Endpoint:** `POST /api/repo-configs`

**Authentication:** Required

**Request Body:**

```json
{
  "repo_name": "octocat/Hello-World",
  "webhook_url": "https://grimoire.example.com/webhook/github",
  "enabled": true
}
```

**Request Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo_name` | string | Yes | GitHub repository in 'owner/repo' format. Must match pattern: `^[\w\-\.]+/[\w\-\.]+$` |
| `webhook_url` | string | Yes | URL where GitHub should send webhook events (1-500 characters) |
| `enabled` | boolean | No | Whether webhook integration is enabled (default: `true`) |

**Success Response:** `201 Created`

```json
{
  "id": 1,
  "repo_name": "octocat/Hello-World",
  "webhook_url": "https://grimoire.example.com/webhook/github",
  "enabled": true,
  "created_at": "2025-12-05T10:00:00Z",
  "updated_at": null,
  "webhook_count": 0,
  "last_webhook_at": null
}
```

**Error Responses:**

- `409 Conflict` - Repository already configured
- `422 Unprocessable Entity` - Invalid repository name format
- `401 Unauthorized` - Missing or invalid authentication

**Example cURL:**

```bash
curl -X POST "https://api.example.com/api/repo-configs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "octocat/Hello-World",
    "webhook_url": "https://grimoire.example.com/webhook/github",
    "enabled": true
  }'
```

---

#### 2. List Repository Configurations

Retrieve all configured repositories with pagination.

**Endpoint:** `GET /api/repo-configs`

**Authentication:** Required

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Number of records to skip (≥ 0) |
| `limit` | integer | No | 100 | Maximum records to return (1-1000) |

**Success Response:** `200 OK`

```json
[
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
]
```

**Notes:**
- Results are ordered by creation date (newest first)
- `webhook_count` is a computed field showing total webhook executions
- `last_webhook_at` is a computed field showing the most recent webhook execution

**Example cURL:**

```bash
curl -X GET "https://api.example.com/api/repo-configs?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### 3. Get Repository Configuration

Retrieve a specific repository configuration by ID.

**Endpoint:** `GET /api/repo-configs/{config_id}`

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_id` | integer | Repository configuration ID |

**Success Response:** `200 OK`

```json
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

**Error Responses:**

- `404 Not Found` - Repository configuration not found
- `401 Unauthorized` - Missing or invalid authentication

**Example cURL:**

```bash
curl -X GET "https://api.example.com/api/repo-configs/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### 4. Update Repository Configuration

Update an existing repository configuration.

**Endpoint:** `PUT /api/repo-configs/{config_id}`

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_id` | integer | Repository configuration ID |

**Request Body:**

All fields are optional. Only provided fields will be updated.

```json
{
  "webhook_url": "https://new-url.example.com/webhook/github",
  "enabled": false
}
```

**Request Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `webhook_url` | string | No | New webhook URL (1-500 characters) |
| `enabled` | boolean | No | New enabled status |

**Success Response:** `200 OK`

```json
{
  "id": 1,
  "repo_name": "octocat/Hello-World",
  "webhook_url": "https://new-url.example.com/webhook/github",
  "enabled": false,
  "created_at": "2025-12-05T10:00:00Z",
  "updated_at": "2025-12-05T14:00:00Z",
  "webhook_count": 15,
  "last_webhook_at": "2025-12-05T11:45:00Z"
}
```

**Notes:**
- The repository name cannot be changed after creation
- The `updated_at` timestamp is automatically updated

**Error Responses:**

- `404 Not Found` - Repository configuration not found
- `401 Unauthorized` - Missing or invalid authentication

**Example cURL:**

```bash
curl -X PUT "https://api.example.com/api/repo-configs/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

---

#### 5. Delete Repository Configuration

Delete a repository configuration and all associated webhook logs.

**Endpoint:** `DELETE /api/repo-configs/{config_id}`

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_id` | integer | Repository configuration ID |

**Success Response:** `200 OK`

```json
{
  "message": "Repository configuration deleted successfully"
}
```

**Notes:**
- This operation cascades to delete all associated webhook execution logs
- This operation cannot be undone

**Error Responses:**

- `404 Not Found` - Repository configuration not found
- `401 Unauthorized` - Missing or invalid authentication

**Example cURL:**

```bash
curl -X DELETE "https://api.example.com/api/repo-configs/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### 6. Get Repository Webhook Logs

Retrieve all webhook execution logs for a specific repository.

**Endpoint:** `GET /api/repo-configs/{config_id}/logs`

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_id` | integer | Repository configuration ID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Number of records to skip (≥ 0) |
| `limit` | integer | No | 100 | Maximum records to return (1-1000) |

**Success Response:** `200 OK`

```json
[
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
]
```

**Notes:**
- Results are ordered by execution time (newest first)
- Returns an empty array if no logs exist for the repository

**Error Responses:**

- `404 Not Found` - Repository configuration not found
- `401 Unauthorized` - Missing or invalid authentication

**Example cURL:**

```bash
curl -X GET "https://api.example.com/api/repo-configs/1/logs?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Webhook Logs API

Retrieve and filter webhook execution logs across all repositories.

### Base URL

```
/api/webhook-logs
```

### Endpoints

#### 1. List All Webhook Logs

Retrieve all webhook execution logs with optional filtering and pagination.

**Endpoint:** `GET /api/webhook-logs`

**Authentication:** Required

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | - | Filter by execution status (`success`, `partial_success`, `error`) |
| `start_date` | datetime | No | - | Filter logs executed on or after this date (ISO 8601 format) |
| `end_date` | datetime | No | - | Filter logs executed on or before this date (ISO 8601 format) |
| `skip` | integer | No | 0 | Number of records to skip (≥ 0) |
| `limit` | integer | No | 100 | Maximum records to return (1-1000) |

**Success Response:** `200 OK`

```json
[
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
]
```

**Notes:**
- Results are ordered by execution time (newest first)
- Multiple filters can be combined
- Date filters use ISO 8601 format (e.g., `2025-12-05T10:00:00Z`)

**Example cURL:**

```bash
# Get all successful webhook logs
curl -X GET "https://api.example.com/api/webhook-logs?status=success" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get logs within a date range
curl -X GET "https://api.example.com/api/webhook-logs?start_date=2025-12-01T00:00:00Z&end_date=2025-12-05T23:59:59Z" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get error logs with pagination
curl -X GET "https://api.example.com/api/webhook-logs?status=error&skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### 2. Get Webhook Log

Retrieve a specific webhook execution log by ID.

**Endpoint:** `GET /api/webhook-logs/{log_id}`

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `log_id` | integer | Webhook execution log ID |

**Success Response:** `200 OK`

```json
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

**Error Responses:**

- `404 Not Found` - Webhook execution log not found
- `401 Unauthorized` - Missing or invalid authentication

**Example cURL:**

```bash
curl -X GET "https://api.example.com/api/webhook-logs/42" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Error Responses

All API endpoints follow a consistent error response format.

### Standard Error Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Validation Error Format

For request validation errors (422 Unprocessable Entity):

```json
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

### Common HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| `200 OK` | Request succeeded |
| `201 Created` | Resource created successfully |
| `400 Bad Request` | Invalid request parameters |
| `401 Unauthorized` | Missing or invalid authentication |
| `404 Not Found` | Resource not found |
| `409 Conflict` | Resource already exists (duplicate) |
| `422 Unprocessable Entity` | Validation error |
| `500 Internal Server Error` | Server error |

---

## Data Models

### Repository Configuration

Represents a GitHub repository configured for webhook integration.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique identifier |
| `repo_name` | string | GitHub repository in 'owner/repo' format |
| `webhook_url` | string | URL where GitHub sends webhook events |
| `enabled` | boolean | Whether webhook integration is enabled |
| `created_at` | datetime | When the configuration was created |
| `updated_at` | datetime | When the configuration was last updated (null if never updated) |
| `webhook_count` | integer | Total webhook executions (computed field) |
| `last_webhook_at` | datetime | Most recent webhook execution (computed field) |

**Example:**

```json
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

---

### Webhook Execution Log

Represents a detailed record of a single webhook processing run.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique identifier |
| `repo_config_id` | integer | Associated repository configuration ID (null if no config) |
| `repo_name` | string | GitHub repository in 'owner/repo' format |
| `pr_number` | integer | Pull request number (null for non-PR events) |
| `event_type` | string | GitHub webhook event type (e.g., 'pull_request') |
| `action` | string | GitHub webhook action (e.g., 'opened', 'closed') |
| `status` | string | Execution status: 'success', 'partial_success', or 'error' |
| `matched_spell_ids` | array | List of spell IDs that matched this event |
| `auto_generated_spell_id` | integer | ID of auto-generated spell (null if none) |
| `error_message` | string | Error message if processing failed (null on success) |
| `pr_processing_result` | object | Detailed processing result including files changed |
| `execution_duration_ms` | integer | Execution duration in milliseconds |
| `executed_at` | datetime | When the webhook was executed |
| `files_changed_count` | integer | Number of files changed (computed field) |
| `spell_match_attempted` | boolean | Whether spell matching was attempted (computed field) |
| `spell_generation_attempted` | boolean | Whether spell generation was attempted (computed field) |

**Status Values:**

- `success` - Webhook processed successfully, spells matched
- `partial_success` - Webhook processed but with warnings (e.g., no spells matched)
- `error` - Webhook processing failed

**Example:**

```json
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
    "status": "success",
    "spell_match_attempted": true,
    "spell_generation_attempted": false
  },
  "execution_duration_ms": 1850,
  "executed_at": "2025-12-05T11:45:23Z",
  "files_changed_count": 2,
  "spell_match_attempted": true,
  "spell_generation_attempted": false
}
```

---

## Best Practices

### Pagination

Always use pagination when retrieving lists to avoid performance issues:

```bash
# Good: Use pagination
curl -X GET "https://api.example.com/api/webhook-logs?skip=0&limit=50"

# Avoid: Requesting too many records at once
curl -X GET "https://api.example.com/api/webhook-logs?limit=10000"
```

### Filtering

Combine filters to narrow down results efficiently:

```bash
# Get error logs from the last 24 hours
curl -X GET "https://api.example.com/api/webhook-logs?status=error&start_date=2025-12-04T00:00:00Z"
```

### Error Handling

Always check the HTTP status code and handle errors appropriately:

```python
import requests

response = requests.get(
    "https://api.example.com/api/repo-configs/1",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code == 200:
    config = response.json()
    print(f"Repository: {config['repo_name']}")
elif response.status_code == 404:
    print("Repository configuration not found")
elif response.status_code == 401:
    print("Authentication failed")
else:
    print(f"Error: {response.json()['detail']}")
```

### Rate Limiting

Be mindful of API rate limits. Implement exponential backoff for retries:

```python
import time
import requests

def make_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:  # Rate limited
            wait_time = 2 ** attempt  # Exponential backoff
            time.sleep(wait_time)
        else:
            break
    
    return None
```

---

## Support

For questions or issues with the API, please contact the development team or open an issue in the project repository.
