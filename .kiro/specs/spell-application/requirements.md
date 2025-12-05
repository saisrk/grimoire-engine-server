# Requirements Document

## Introduction

The Spell Application feature enables users to apply existing spells to their failing code by generating context-aware patches. When a user views a spell in the detail page and clicks "Apply Spell (Preview)", the system sends the failing context (stack trace, test name, repository metadata) along with the spell's incantation to an LLM, which generates a git unified diff patch adapted to the user's specific codebase. The generated patch is then displayed in a side-by-side diff viewer for user review before application.

## Glossary

- **Spell Application**: The process of adapting and applying a canonical spell solution to a specific codebase context
- **Incantation**: The canonical git diff or code solution stored in a spell that serves as the template for adaptation
- **Failing Context**: The error information including stack trace, failing test name, repository language, version, and commit SHA
- **Adaptation Constraints**: Rules that limit how the spell can be modified, such as file count limits, style preservation, and dependency restrictions
- **Git Unified Diff**: A standardized text format showing line-by-line changes between file versions
- **Patch**: A git unified diff that can be applied to a codebase to implement changes
- **LLM Service**: The service that communicates with language model providers to generate adapted patches
- **Spell Detail Page**: The frontend UI page displaying a single spell's information and actions
- **Side-by-Side Diff Viewer**: A UI component that displays original and modified code in parallel columns

## Requirements

### Requirement 1

**User Story:** As a developer, I want to click "Apply Spell (Preview)" on the spell detail page, so that I can generate a context-aware patch for my failing code.

#### Acceptance Criteria

1. WHEN a user clicks the "Apply Spell (Preview)" button, THEN the frontend SHALL send a POST request to the spell application API endpoint with spell ID and failing context
2. WHEN the request is sent, THEN the frontend SHALL include the failing test name, stack trace, repository language, version, and commit SHA in the request payload
3. WHEN the request is sent, THEN the frontend SHALL include adaptation constraints such as maximum files to modify and style preservation rules
4. WHEN the API processes the request, THEN the system SHALL retrieve the spell's incantation from the database using the provided spell ID
5. WHEN the spell is not found, THEN the API SHALL return HTTP 404 status with an error message indicating the spell does not exist

### Requirement 2

**User Story:** As a developer, I want the system to generate an adapted patch using an LLM, so that the spell solution is tailored to my specific codebase and error context.

#### Acceptance Criteria

1. WHEN the LLM Service receives a patch generation request, THEN the system SHALL construct a prompt containing the failing context, spell incantation, and adaptation constraints
2. WHEN constructing the prompt, THEN the system SHALL format it to instruct the LLM to return only a JSON object with patch, files_touched, and rationale fields
3. WHEN calling the LLM, THEN the system SHALL use the configured provider and model from environment variables
4. WHEN the LLM returns a response, THEN the system SHALL parse the JSON response and validate that it contains the required fields
5. IF the LLM response is invalid or cannot be parsed, THEN the system SHALL return an error response with details about the parsing failure

### Requirement 3

**User Story:** As a developer, I want the generated patch to respect adaptation constraints, so that the changes are safe and aligned with my project requirements.

#### Acceptance Criteria

1. WHEN generating a patch, THEN the LLM prompt SHALL include the maximum number of files that can be modified
2. WHEN generating a patch, THEN the LLM prompt SHALL instruct the LLM to preserve the existing coding style and conventions
3. WHEN generating a patch, THEN the LLM prompt SHALL specify which files or patterns should not be modified
4. WHEN the LLM returns a patch, THEN the system SHALL validate that the number of files touched does not exceed the specified limit
5. IF the patch violates constraints, THEN the system SHALL return an error response indicating which constraint was violated

### Requirement 4

**User Story:** As a developer, I want the API to return a structured response with the patch and metadata, so that the frontend can display the changes in a diff viewer.

#### Acceptance Criteria

1. WHEN patch generation succeeds, THEN the API SHALL return HTTP 200 status with a JSON response containing patch, files_touched, and rationale fields
2. WHEN returning the patch, THEN the response SHALL include the git unified diff as a string in the patch field
3. WHEN returning metadata, THEN the response SHALL include a list of file paths that were modified in the files_touched field
4. WHEN returning the rationale, THEN the response SHALL include a brief explanation of the changes in 1-2 sentences
5. WHEN an error occurs during generation, THEN the API SHALL return an appropriate HTTP error status with a JSON error object containing an error message

### Requirement 5

**User Story:** As a developer, I want the system to handle LLM failures gracefully, so that I receive clear error messages when patch generation fails.

#### Acceptance Criteria

1. WHEN the LLM API call times out, THEN the system SHALL return HTTP 504 status with an error message indicating the request timed out
2. WHEN the LLM API returns an error, THEN the system SHALL log the error details and return HTTP 502 status with a user-friendly error message
3. WHEN the LLM API key is missing or invalid, THEN the system SHALL return HTTP 500 status with an error message indicating configuration issues
4. WHEN the LLM returns a response that cannot generate a valid patch, THEN the system SHALL return HTTP 422 status with the error message from the LLM
5. WHEN any error occurs, THEN the system SHALL log the full error context including request parameters and LLM response for debugging

### Requirement 6

**User Story:** As a developer, I want the patch generation to be fast and efficient, so that I can quickly preview changes without long wait times.

#### Acceptance Criteria

1. WHEN making an LLM API call, THEN the system SHALL set a timeout of 30 seconds to prevent indefinite waiting
2. WHEN the LLM request is in progress, THEN the system SHALL use async operations to avoid blocking other requests
3. WHEN multiple patch requests are made, THEN the system SHALL handle them concurrently without degrading performance
4. WHEN the LLM response is received, THEN the system SHALL parse and validate it within 1 second
5. WHEN the total request time exceeds 35 seconds, THEN the system SHALL return a timeout error to the client

### Requirement 7

**User Story:** As a developer, I want the system to validate the generated patch format, so that only valid git diffs are returned to the frontend.

#### Acceptance Criteria

1. WHEN a patch is generated, THEN the system SHALL verify that it starts with a valid git diff header
2. WHEN validating the patch, THEN the system SHALL check that file paths in the diff match the files_touched list
3. WHEN validating the patch, THEN the system SHALL ensure the diff contains valid unified diff format markers
4. IF the patch format is invalid, THEN the system SHALL return HTTP 422 status with an error describing the validation failure
5. WHEN the patch is valid, THEN the system SHALL return it without modification to preserve exact formatting

### Requirement 8

**User Story:** As a developer, I want the API endpoint to be documented, so that frontend developers can integrate the spell application feature correctly.

#### Acceptance Criteria

1. WHEN the API is running, THEN the spell application endpoint SHALL appear in the interactive API documentation at /docs
2. WHEN viewing the endpoint documentation, THEN it SHALL include descriptions of all request parameters and their validation rules
3. WHEN viewing the endpoint documentation, THEN it SHALL include example request and response payloads
4. WHEN viewing the endpoint documentation, THEN it SHALL document all possible HTTP status codes and their meanings
5. WHEN viewing the endpoint documentation, THEN it SHALL include the Pydantic schema definitions for request and response models

### Requirement 9

**User Story:** As a developer, I want the system to support multiple programming languages, so that I can apply spells to projects in different languages.

#### Acceptance Criteria

1. WHEN the failing context includes a language field, THEN the system SHALL include it in the LLM prompt to guide language-specific adaptation
2. WHEN the failing context includes a version field, THEN the system SHALL include it in the LLM prompt to ensure compatibility with that version
3. WHEN generating patches for different languages, THEN the system SHALL instruct the LLM to use language-appropriate syntax and conventions
4. WHEN the language is not specified, THEN the system SHALL attempt to infer it from the file extensions in the spell incantation
5. WHEN language inference fails, THEN the system SHALL proceed with generic patch generation and include a warning in the response

### Requirement 10

**User Story:** As a developer, I want the system to store applied spell history in the database, so that I can view past applications and their results on the spell detail page.

#### Acceptance Criteria

1. WHEN a patch is successfully generated, THEN the system SHALL create a spell application record in the database linked to the spell ID
2. WHEN storing the application record, THEN the system SHALL persist the generated patch, files touched, rationale, and failing context
3. WHEN storing the application record, THEN the system SHALL include timestamps for when the application was created
4. WHEN storing the application record, THEN the system SHALL include the repository information and commit SHA
5. WHEN retrieving a spell by ID, THEN the API SHALL include a list of recent applications with their metadata in the response

### Requirement 11

**User Story:** As a developer, I want to view the history of spell applications on the spell detail page, so that I can see how the spell has been used and what patches were generated.

#### Acceptance Criteria

1. WHEN fetching a spell by ID, THEN the system SHALL query the database for all application records associated with that spell
2. WHEN returning spell applications, THEN the system SHALL include the application ID, timestamp, repository name, commit SHA, and files touched
3. WHEN returning spell applications, THEN the system SHALL order them by creation timestamp descending to show most recent first
4. WHEN there are no applications for a spell, THEN the system SHALL return an empty list without raising an error
5. WHEN the spell detail page loads, THEN the frontend SHALL display the application history in a list or table format

### Requirement 12

**User Story:** As a system administrator, I want the spell application feature to log all requests and responses, so that I can monitor usage and debug issues.

#### Acceptance Criteria

1. WHEN a spell application request is received, THEN the system SHALL log the spell ID, repository context, and timestamp
2. WHEN the LLM generates a patch, THEN the system SHALL log the token count, response time, and confidence indicators
3. WHEN an error occurs, THEN the system SHALL log the full error stack trace and request context
4. WHEN logging sensitive information, THEN the system SHALL redact API keys and authentication tokens
5. WHEN logs are written, THEN the system SHALL use structured logging with consistent field names for easy parsing and analysis
