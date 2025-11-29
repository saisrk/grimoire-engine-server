# Requirements Document

## Introduction

The Grimoire Engine is a hackathon project that captures errors from GitHub pull requests and matches them with solution "spells" - reusable code fixes and patterns. The system receives GitHub webhook events, processes PR diffs to extract errors, and provides a matching service to rank relevant spells. The backend is built with FastAPI using async patterns, SQLite for data persistence, and is designed to be extensible for future enhancements like vector databases, sandbox execution, and Kiro IDE integration.

## Glossary

- **Grimoire Engine**: The complete system for capturing and matching code error solutions
- **Spell**: A reusable code solution or pattern stored in the system that can fix specific errors
- **Backend API**: The FastAPI server that handles webhooks, spell management, and matching services
- **GitHub Webhook**: HTTP POST requests sent by GitHub when pull request events occur
- **PR Processor**: Service component that fetches and processes pull request diffs from GitHub
- **Matcher Service**: Service component that ranks spells based on error payload similarity
- **SQLite Database**: File-based relational database for storing spell data
- **Alembic**: Database migration tool for managing schema changes
- **MCP Analyzer**: Model Context Protocol analyzer integration point for code analysis
- **Kiro Integration**: Extension points for Kiro IDE vibe-code features

## Requirements

### Requirement 1

**User Story:** As a developer, I want the system to receive GitHub pull request webhook events, so that the Grimoire Engine can automatically process PR changes when they occur.

#### Acceptance Criteria

1. WHEN GitHub sends a pull_request webhook event, THEN the Backend API SHALL receive the HTTP POST request at the webhook endpoint
2. WHEN a webhook request is received, THEN the Backend API SHALL validate the GitHub signature using HMAC-SHA256 to ensure authenticity
3. IF the webhook signature is invalid, THEN the Backend API SHALL reject the request with HTTP 401 status and log the security violation
4. WHEN a valid webhook is received, THEN the Backend API SHALL parse the JSON payload and extract pull request metadata
5. WHEN webhook processing completes successfully, THEN the Backend API SHALL return HTTP 200 status to acknowledge receipt

### Requirement 2

**User Story:** As a developer, I want to manage spells through a REST API, so that I can create, read, update, and delete solution patterns in the system.

#### Acceptance Criteria

1. WHEN a GET request is sent to /api/spells, THEN the Backend API SHALL return a paginated list of all spells with their metadata
2. WHEN a GET request is sent to /api/spells/{id}, THEN the Backend API SHALL return the complete spell data for the specified ID
3. IF a spell ID does not exist, THEN the Backend API SHALL return HTTP 404 status with an error message
4. WHEN a POST request with valid spell data is sent to /api/spells, THEN the Backend API SHALL create a new spell record in the SQLite Database and return HTTP 201 with the created spell
5. WHEN a PUT request with valid data is sent to /api/spells/{id}, THEN the Backend API SHALL update the existing spell and return the updated data
6. WHEN a DELETE request is sent to /api/spells/{id}, THEN the Backend API SHALL remove the spell from the SQLite Database and return HTTP 204

### Requirement 3

**User Story:** As a developer, I want spell data to persist in a database, so that solutions are available across system restarts and can be queried efficiently.

#### Acceptance Criteria

1. WHEN the Backend API starts, THEN the system SHALL initialize an async SQLAlchemy engine connected to the SQLite Database
2. WHEN database schema changes are needed, THEN the system SHALL use Alembic to manage migrations in a version-controlled manner
3. WHEN a spell is created or updated, THEN the SQLite Database SHALL persist the data immediately with ACID guarantees
4. WHEN the application queries spell data, THEN the system SHALL use async database operations to maintain non-blocking performance
5. WHEN the SQLite Database file does not exist on startup, THEN the system SHALL create it automatically with the current schema

### Requirement 4

**User Story:** As a developer, I want the system to fetch pull request diffs from GitHub, so that error patterns can be extracted and analyzed.

#### Acceptance Criteria

1. WHEN the PR Processor receives a pull request event, THEN the system SHALL extract the repository name and PR number from the webhook payload
2. WHEN fetching a PR diff, THEN the PR Processor SHALL make an authenticated HTTP request to the GitHub API using the provided credentials
3. WHEN the GitHub API returns the diff data, THEN the PR Processor SHALL parse the response and extract file changes
4. IF the GitHub API request fails, THEN the PR Processor SHALL log the error with details and return an error status
5. WHEN diff data is successfully retrieved, THEN the PR Processor SHALL return the parsed diff for downstream processing

### Requirement 5

**User Story:** As a developer, I want the system to match errors with relevant spells, so that the most appropriate solutions can be suggested for specific problems.

#### Acceptance Criteria

1. WHEN the Matcher Service receives an error payload, THEN the system SHALL extract error characteristics including error type, message, and context
2. WHEN matching spells, THEN the Matcher Service SHALL query the SQLite Database for candidate spells based on error patterns
3. WHEN ranking spells, THEN the Matcher Service SHALL compute similarity scores between the error and each candidate spell
4. WHEN ranking is complete, THEN the Matcher Service SHALL return a sorted list of spell IDs ordered by relevance score descending
5. IF no matching spells are found, THEN the Matcher Service SHALL return an empty list without raising an error

### Requirement 6

**User Story:** As a developer, I want the system to be containerized with Docker, so that it can be deployed consistently across different environments.

#### Acceptance Criteria

1. WHEN building the Docker image, THEN the system SHALL use Python 3.11 as the base image and install all dependencies from requirements.txt
2. WHEN the container starts, THEN the Backend API SHALL run on a configurable port with uvicorn as the ASGI server
3. WHEN using docker-compose, THEN the system SHALL mount the SQLite Database file as a volume to persist data across container restarts
4. WHEN environment variables are needed, THEN the system SHALL load configuration from a .env file with secure defaults
5. WHEN the container is running, THEN the Backend API SHALL be accessible from the host machine on the mapped port

### Requirement 7

**User Story:** As a developer, I want automated CI/CD with GitHub Actions, so that code quality is verified on every commit.

#### Acceptance Criteria

1. WHEN code is pushed to the repository, THEN the GitHub Actions workflow SHALL trigger automatically
2. WHEN the CI workflow runs, THEN the system SHALL install dependencies and run linting checks on the Python code
3. WHEN tests exist, THEN the CI workflow SHALL execute the test suite and report results
4. IF any CI step fails, THEN the workflow SHALL mark the build as failed and prevent merging
5. WHEN all CI steps pass, THEN the workflow SHALL mark the build as successful with a green status

### Requirement 8

**User Story:** As a developer, I want the codebase to include extension points for future features, so that vector databases, sandbox runners, and Kiro integrations can be added without major refactoring.

#### Acceptance Criteria

1. WHERE vector database integration is planned, the Matcher Service SHALL include comments and stub functions indicating where vector similarity search should be implemented
2. WHERE sandbox execution is planned, the PR Processor SHALL include comments indicating where code execution and testing should be integrated
3. WHERE MCP analyzers are planned, the system SHALL include comments in the error extraction logic indicating where MCP protocol calls should be added
4. WHERE Kiro vibe-code integration is planned, the system SHALL include comments in the spell matching logic indicating where Kiro IDE features should connect
5. WHEN reviewing the codebase, THEN developers SHALL find clear docstrings explaining the purpose and future extension points of each service component

### Requirement 9

**User Story:** As a developer, I want comprehensive API documentation, so that I can understand how to interact with all endpoints without reading source code.

#### Acceptance Criteria

1. WHEN the Backend API is running, THEN the system SHALL serve interactive API documentation at /docs using FastAPI's automatic OpenAPI generation
2. WHEN viewing endpoint documentation, THEN each API route SHALL include descriptions of request parameters, response schemas, and status codes
3. WHEN viewing model documentation, THEN each data model SHALL include field descriptions and validation rules
4. WHEN testing endpoints, THEN developers SHALL be able to execute API calls directly from the /docs interface
5. WHEN the API schema changes, THEN the documentation SHALL update automatically without manual intervention

### Requirement 10

**User Story:** As a developer, I want secure configuration management, so that sensitive credentials are not hardcoded in the source code.

#### Acceptance Criteria

1. WHEN the application starts, THEN the system SHALL load configuration values from environment variables
2. WHEN a .env.example file is provided, THEN it SHALL document all required environment variables with placeholder values
3. WHEN GitHub webhook secrets are configured, THEN the system SHALL store them in environment variables and never log their values
4. WHEN GitHub API tokens are needed, THEN the system SHALL read them from environment variables with clear TODO comments for authentication setup
5. IF required environment variables are missing, THEN the Backend API SHALL log a warning and use safe default values where applicable
