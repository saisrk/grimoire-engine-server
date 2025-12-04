# Requirements Document

## Introduction

This spec covers the integration work to connect the GitHub webhook endpoint with the PR Processor and Matcher services in the Grimoire Engine backend. The webhook endpoint currently receives and validates GitHub pull request events but does not process them. This integration will complete the end-to-end workflow: webhook receipt → PR processing → error extraction → spell matching → response.

This is a focused integration spec that builds upon the existing grimoire-engine-backend infrastructure where all individual components (webhook endpoint, PR Processor, Matcher service) already exist but are not wired together.

## Glossary

- **Webhook Endpoint**: The FastAPI route at `/webhook/github` that receives GitHub pull_request events
- **PR Processor**: Existing service (`PRProcessor`) that fetches PR diffs from GitHub API and parses file changes
- **Matcher Service**: Existing service (`MatcherService`) that ranks spells based on error payload similarity
- **Service Integration**: The process of connecting the webhook endpoint to call PR Processor and Matcher services
- **Error Payload**: A structured dictionary containing error information (type, message, context) used for spell matching
- **Placeholder Error**: Temporary error data constructed from PR metadata until MCP analyzers are integrated

## Requirements

### Requirement 1

**User Story:** As a developer, I want the webhook endpoint to process PR events using the PR Processor service, so that PR diffs are automatically fetched and parsed when webhooks are received.

#### Acceptance Criteria

1. WHEN a valid pull_request webhook is received, THEN the Webhook Endpoint SHALL instantiate the PR Processor and call its process_pr_event method with the webhook payload
2. WHEN the PR Processor completes successfully, THEN the Webhook Endpoint SHALL extract the repository name, PR number, and files changed from the processing result
3. IF the PR Processor returns an error status, THEN the Webhook Endpoint SHALL log the error details and continue processing without failing the webhook request
4. WHEN PR processing completes, THEN the Webhook Endpoint SHALL include the processing results in the response payload
5. WHEN the GitHub API token is not configured, THEN the PR Processor SHALL log a warning but the webhook SHALL still return success to prevent GitHub retries

### Requirement 2

**User Story:** As a developer, I want the webhook endpoint to create error payloads from PR data, so that the Matcher service can find relevant spells even without full error extraction.

#### Acceptance Criteria

1. WHEN PR processing completes successfully, THEN the Webhook Endpoint SHALL construct an error payload dictionary with error_type, message, and context fields
2. WHEN constructing the error payload, THEN the system SHALL use PR metadata (repository name, PR number, action) as the context
3. WHEN constructing the error payload, THEN the system SHALL use a placeholder error type and message indicating this is PR-based matching
4. WHEN files are changed in the PR, THEN the error payload context SHALL include the list of changed file paths
5. WHEN the error payload is constructed, THEN it SHALL conform to the structure expected by the Matcher Service

### Requirement 3

**User Story:** As a developer, I want the webhook endpoint to match errors with spells using the Matcher service, so that relevant solutions are identified for each PR.

#### Acceptance Criteria

1. WHEN an error payload is constructed, THEN the Webhook Endpoint SHALL instantiate the Matcher Service with the database session
2. WHEN the Matcher Service is called, THEN the Webhook Endpoint SHALL pass the error payload to the match_spells method
3. WHEN the Matcher Service returns spell IDs, THEN the Webhook Endpoint SHALL include the ranked list in the response payload
4. IF the Matcher Service returns an empty list, THEN the Webhook Endpoint SHALL include an empty matched_spells array in the response
5. IF the Matcher Service raises an exception, THEN the Webhook Endpoint SHALL log the error and return an empty matched_spells array without failing the webhook

### Requirement 4

**User Story:** As a developer, I want the webhook response to include processing results, so that I can verify the integration is working correctly.

#### Acceptance Criteria

1. WHEN the webhook processing completes, THEN the response SHALL include a pr_processing object with repo, pr_number, files_changed count, and status
2. WHEN spell matching completes, THEN the response SHALL include a matched_spells array with the ranked spell IDs
3. WHEN any processing step fails, THEN the response SHALL still return HTTP 200 to prevent GitHub webhook retries
4. WHEN errors occur during processing, THEN the pr_processing status SHALL be set to "error" with an error message
5. WHEN the webhook response is returned, THEN it SHALL maintain backward compatibility with the existing response structure

### Requirement 5

**User Story:** As a developer, I want comprehensive error handling in the integration, so that webhook processing is resilient to service failures.

#### Acceptance Criteria

1. WHEN the PR Processor raises an exception, THEN the Webhook Endpoint SHALL catch it, log the error with stack trace, and continue to return success
2. WHEN the Matcher Service raises an exception, THEN the Webhook Endpoint SHALL catch it, log the error with stack trace, and return an empty spell list
3. WHEN any service call fails, THEN the error details SHALL be logged with sufficient context for debugging
4. WHEN processing errors occur, THEN the webhook SHALL still return HTTP 200 status to acknowledge receipt to GitHub
5. WHEN logging errors, THEN sensitive information (tokens, secrets) SHALL never be included in log messages
