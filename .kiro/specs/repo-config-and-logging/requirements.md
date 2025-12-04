# Requirements Document

## Introduction

This specification covers the addition of repository configuration management and webhook execution logging to the Grimoire Engine Backend. Currently, the system can receive and process GitHub webhooks, but lacks the ability to configure which repositories should have webhooks enabled and to track what happens during each webhook execution. This feature will enable users to manage repository integrations through the API and monitor webhook activity through detailed execution logs.

## Glossary

- **Repository Configuration**: A stored record of a GitHub repository that has webhook integration enabled, including repository metadata and webhook settings
- **Webhook Execution Log**: A detailed record of a single webhook processing run, capturing matched spells, auto-generated spells, errors, and processing metadata
- **Client API**: The REST API endpoints that allow external clients to configure repositories and retrieve webhook logs
- **Repository**: A GitHub repository identified by its full name (e.g., "octocat/Hello-World")
- **Webhook Registration**: The process of configuring a GitHub repository to send webhook events to the Grimoire Engine Backend
- **Execution Status**: The outcome of webhook processing (success, partial_success, error)

## Requirements

### Requirement 1

**User Story:** As a developer, I want to register a new repository for webhook integration, so that the system can track which repositories are configured and their webhook settings.

#### Acceptance Criteria

1. WHEN a user submits a repository configuration request with repository name and webhook URL, THEN the system SHALL create a new repository configuration record in the database
2. WHEN creating a repository configuration, THEN the system SHALL validate that the repository name follows the format "owner/repo"
3. WHEN a repository configuration already exists for the given repository name, THEN the system SHALL return an error indicating the repository is already configured
4. WHEN a repository configuration is created, THEN the system SHALL store the repository name, webhook URL, enabled status, and creation timestamp
5. WHEN a repository configuration is created successfully, THEN the system SHALL return the complete configuration including the generated ID

### Requirement 2

**User Story:** As a developer, I want to list all configured repositories, so that I can see which repositories have webhook integration enabled.

#### Acceptance Criteria

1. WHEN a user requests the list of configured repositories, THEN the system SHALL return all repository configurations ordered by creation date descending
2. WHEN returning repository configurations, THEN the system SHALL include repository name, webhook URL, enabled status, creation date, and last webhook execution date
3. WHEN no repositories are configured, THEN the system SHALL return an empty list
4. WHEN repositories exist, THEN the system SHALL support pagination with configurable page size and offset
5. WHEN returning repository configurations, THEN the system SHALL include a count of total webhook executions for each repository

### Requirement 3

**User Story:** As a developer, I want to update a repository configuration, so that I can enable/disable webhooks or modify settings without deleting the configuration.

#### Acceptance Criteria

1. WHEN a user submits an update request with repository ID and new settings, THEN the system SHALL update the specified repository configuration
2. WHEN updating a repository configuration, THEN the system SHALL allow modification of webhook URL and enabled status
3. WHEN a repository configuration does not exist for the given ID, THEN the system SHALL return a 404 error
4. WHEN a repository configuration is updated, THEN the system SHALL update the updated_at timestamp
5. WHEN a repository configuration is updated successfully, THEN the system SHALL return the complete updated configuration

### Requirement 4

**User Story:** As a developer, I want to delete a repository configuration, so that I can remove repositories that no longer need webhook integration.

#### Acceptance Criteria

1. WHEN a user submits a delete request with repository ID, THEN the system SHALL remove the repository configuration from the database
2. WHEN deleting a repository configuration, THEN the system SHALL also delete all associated webhook execution logs
3. WHEN a repository configuration does not exist for the given ID, THEN the system SHALL return a 404 error
4. WHEN a repository configuration is deleted successfully, THEN the system SHALL return a success confirmation
5. WHEN deleting a repository configuration, THEN the system SHALL log the deletion with repository name and user context

### Requirement 5

**User Story:** As a developer, I want the system to automatically log each webhook execution, so that I can track what happens during webhook processing without manual intervention.

#### Acceptance Criteria

1. WHEN a webhook is received and processed, THEN the system SHALL create a webhook execution log record in the database
2. WHEN creating a webhook execution log, THEN the system SHALL capture repository name, PR number, event type, action, execution status, and timestamp
3. WHEN webhook processing completes successfully, THEN the execution log SHALL record all matched spell IDs and any auto-generated spell ID
4. WHEN webhook processing encounters errors, THEN the execution log SHALL capture the error message and stack trace
5. WHEN creating a webhook execution log, THEN the system SHALL link it to the repository configuration if one exists

### Requirement 6

**User Story:** As a developer, I want to retrieve webhook execution logs for a specific repository, so that I can monitor webhook activity and troubleshoot issues.

#### Acceptance Criteria

1. WHEN a user requests webhook logs for a repository ID, THEN the system SHALL return all execution logs for that repository ordered by execution time descending
2. WHEN returning webhook execution logs, THEN the system SHALL include execution status, matched spells, auto-generated spells, errors, and processing metadata
3. WHEN no execution logs exist for a repository, THEN the system SHALL return an empty list
4. WHEN execution logs exist, THEN the system SHALL support pagination with configurable page size and offset
5. WHEN returning execution logs, THEN the system SHALL include the count of matched spells and whether a spell was auto-generated

### Requirement 7

**User Story:** As a developer, I want to retrieve all webhook execution logs across all repositories, so that I can monitor overall system activity.

#### Acceptance Criteria

1. WHEN a user requests all webhook execution logs, THEN the system SHALL return logs from all repositories ordered by execution time descending
2. WHEN returning all execution logs, THEN the system SHALL include repository name to identify which repository each log belongs to
3. WHEN filtering execution logs, THEN the system SHALL support filtering by execution status (success, partial_success, error)
4. WHEN filtering execution logs, THEN the system SHALL support filtering by date range (start_date and end_date)
5. WHEN returning all execution logs, THEN the system SHALL support pagination with configurable page size and offset

### Requirement 8

**User Story:** As a developer, I want to retrieve a specific webhook execution log by ID, so that I can view detailed information about a particular webhook run.

#### Acceptance Criteria

1. WHEN a user requests a webhook execution log by ID, THEN the system SHALL return the complete log record with all details
2. WHEN returning a specific execution log, THEN the system SHALL include all captured data: matched spells, auto-generated spells, errors, processing results, and metadata
3. WHEN a webhook execution log does not exist for the given ID, THEN the system SHALL return a 404 error
4. WHEN returning a specific execution log, THEN the system SHALL include the associated repository configuration details
5. WHEN returning a specific execution log, THEN the system SHALL include the full PR processing result if available

### Requirement 9

**User Story:** As a developer, I want the webhook endpoint to automatically create execution logs, so that all webhook activity is tracked without requiring separate API calls.

#### Acceptance Criteria

1. WHEN the webhook endpoint processes a pull_request event, THEN it SHALL create a webhook execution log before returning the response
2. WHEN creating an execution log, THEN the webhook endpoint SHALL capture the complete processing result including matched spells and errors
3. WHEN the webhook endpoint encounters an error, THEN it SHALL still create an execution log with error status and error details
4. WHEN creating an execution log, THEN the webhook endpoint SHALL not fail if logging fails, but SHALL log the logging error
5. WHEN the webhook endpoint creates an execution log, THEN it SHALL include the execution duration in milliseconds

### Requirement 10

**User Story:** As a system administrator, I want webhook execution logs to include comprehensive metadata, so that I can analyze webhook performance and troubleshoot issues effectively.

#### Acceptance Criteria

1. WHEN creating a webhook execution log, THEN the system SHALL capture the number of files changed in the PR
2. WHEN creating a webhook execution log, THEN the system SHALL capture the list of changed file paths
3. WHEN creating a webhook execution log, THEN the system SHALL capture the execution duration from webhook receipt to response
4. WHEN creating a webhook execution log, THEN the system SHALL capture whether spell matching was attempted and whether it succeeded
5. WHEN creating a webhook execution log, THEN the system SHALL capture whether spell auto-generation was attempted and whether it succeeded
