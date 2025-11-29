# Implementation Plan

- [x] 1. Set up project structure and dependencies
  - Create directory structure: app/, tests/, .github/workflows/
  - Create requirements.txt with FastAPI, SQLAlchemy, aiosqlite, Alembic, pytest, hypothesis, httpx
  - Create .env.example with all required environment variables
  - Create .gitignore for Python projects
  - _Requirements: 6.4, 10.1, 10.2_

- [x] 2. Configure database and ORM
  - Create app/db/database.py with async SQLAlchemy engine and session factory
  - Configure SQLite connection with aiosqlite driver
  - Implement get_db() dependency for FastAPI
  - Initialize Alembic and create initial migration structure
  - _Requirements: 3.1, 3.5_

- [x] 3. Implement Spell data model
  - Create app/models/spell.py with SQLAlchemy Spell model
  - Define all fields: id, title, description, error_type, error_pattern, solution_code, tags, timestamps
  - Add indexes on id, title, and error_type
  - Create Pydantic schemas: SpellBase, SpellCreate, SpellUpdate, SpellResponse
  - _Requirements: 3.3_

- [x] 3.1 Write property test for spell model
  - **Property 5: Spell CRUD round-trip consistency**
  - **Validates: Requirements 2.4, 2.5, 3.3**

- [x] 4. Create FastAPI application and main entry point
  - Create app/main.py with FastAPI app instance
  - Configure CORS middleware
  - Add health check endpoint at /health
  - Set up automatic OpenAPI documentation at /docs
  - Configure logging with appropriate levels
  - _Requirements: 9.1, 10.1_

- [x] 5. Implement Spell CRUD API endpoints
  - Create app/api/spells.py with APIRouter
  - Implement GET /api/spells with pagination (skip, limit parameters)
  - Implement GET /api/spells/{id} with 404 handling
  - Implement POST /api/spells with validation and 201 response
  - Implement PUT /api/spells/{id} with validation
  - Implement DELETE /api/spells/{id} with 204 response
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [ ]* 5.1 Write property test for pagination
  - **Property 3: Spell pagination consistency**
  - **Validates: Requirements 2.1**

- [ ]* 5.2 Write property test for spell retrieval
  - **Property 4: Spell retrieval returns stored data**
  - **Validates: Requirements 2.2**

- [ ]* 5.3 Write property test for spell deletion
  - **Property 6: Spell deletion removes data**
  - **Validates: Requirements 2.6**

- [x] 6. Implement GitHub webhook endpoint
  - Create app/api/webhook.py with APIRouter
  - Implement POST /webhook endpoint
  - Add signature validation using HMAC-SHA256 with timing-safe comparison
  - Parse pull_request event payload
  - Return 401 for invalid signatures with security logging
  - Return 200 for successful webhook receipt
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [ ]* 6.1 Write property test for webhook signature validation
  - **Property 1: Webhook signature validation correctness**
  - **Validates: Requirements 1.2**

- [ ]* 6.2 Write property test for webhook payload parsing
  - **Property 2: Webhook payload parsing preserves structure**
  - **Validates: Requirements 1.4**

- [x] 7. Implement PR Processor service
  - Create app/services/pr_processor.py with PRProcessor class
  - Implement process_pr_event() to extract repo name and PR number from webhook payload
  - Implement fetch_pr_diff() to make authenticated GitHub API request
  - Add TODO comments for authentication setup
  - Implement diff parsing to extract file changes
  - Add error handling for GitHub API failures with logging
  - Add extension point comments for MCP analyzers and sandbox runner
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 8.2, 8.3_

- [ ]* 7.1 Write property test for PR metadata extraction
  - **Property 7: PR metadata extraction correctness**
  - **Validates: Requirements 4.1**

- [ ]* 7.2 Write property test for diff parsing
  - **Property 8: Diff parsing extracts file changes**
  - **Validates: Requirements 4.3**

- [x] 8. Implement Matcher service
  - Create app/services/matcher.py with MatcherService class
  - Implement match_spells() to accept error payload and query database
  - Implement error characteristic extraction (error_type, message, context)
  - Implement _compute_similarity() with simple keyword matching
  - Implement ranking logic to sort spells by similarity score descending
  - Return empty list when no matches found
  - Add extension point comments for vector DB, Kiro integration, and MCP analyzers
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 8.1, 8.4_

- [ ]* 8.1 Write property test for error extraction
  - **Property 9: Error payload extraction completeness**
  - **Validates: Requirements 5.1**

- [ ]* 8.2 Write property test for similarity determinism
  - **Property 10: Similarity score computation is deterministic**
  - **Validates: Requirements 5.3**

- [ ]* 8.3 Write property test for ranking sort order
  - **Property 11: Spell ranking maintains sort order**
  - **Validates: Requirements 5.4**

- [x] 9. Create Alembic migration for Spell table
  - Generate initial migration with alembic revision --autogenerate
  - Review and adjust migration file if needed
  - Add migration to create spells table with all columns and indexes
  - Test migration with alembic upgrade head
  - _Requirements: 3.2_

- [x] 10. Create Docker configuration
  - Create Dockerfile with Python 3.11 base image
  - Install dependencies from requirements.txt in Docker image
  - Set working directory and copy application code
  - Expose port 8000
  - Set CMD to run uvicorn with host 0.0.0.0
  - Create docker-compose.yml with grimoire-api service
  - Configure volume mount for SQLite database persistence (./data:/app/data)
  - Configure environment variables from .env file
  - Add health check using curl to /health endpoint
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 11. Create GitHub Actions CI workflow
  - Create .github/workflows/ci.yml
  - Configure workflow to trigger on push and pull_request events
  - Add job to setup Python 3.11
  - Add step to install dependencies from requirements.txt
  - Add step to run ruff linting
  - Add step to run mypy type checking
  - Add step to run pytest with coverage
  - Configure workflow to fail if any step fails
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 12. Create project documentation
  - Create README.md with project overview, quick start, and API documentation
  - Document all environment variables in .env.example
  - Add setup instructions for local development
  - Add Docker deployment instructions
  - Document API endpoints with example requests/responses
  - Add extension point documentation for future features
  - _Requirements: 8.5, 9.2, 9.3, 10.2_

- [ ] 13. Add comprehensive docstrings and extension comments
  - Add module-level docstrings to all Python files
  - Add function docstrings with Args, Returns, Raises sections
  - Add TODO comments for vector DB integration in matcher.py
  - Add TODO comments for sandbox runner in pr_processor.py
  - Add TODO comments for MCP analyzer integration in pr_processor.py
  - Add TODO comments for Kiro vibe-code integration in matcher.py
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
