# Design Document

## Overview

The Grimoire Engine backend is a FastAPI-based asynchronous web service that captures GitHub pull request events via webhooks, processes error patterns, and matches them with stored solution "spells". The architecture follows a layered approach with clear separation between API routes, business logic services, and data persistence. The system is designed for hackathon-speed development while maintaining extensibility for future enhancements like vector similarity search, sandbox code execution, and IDE integrations.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        GitHub                                │
│                    (Webhook Events)                          │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS POST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Layer                                │   │
│  │  • /webhook (GitHub events)                          │   │
│  │  • /api/spells (CRUD operations)                     │   │
│  └──────────────┬───────────────────────┬────────────────┘   │
│                 │                       │                    │
│  ┌──────────────▼───────────┐  ┌───────▼──────────────┐     │
│  │   PR Processor Service   │  │   Matcher Service    │     │
│  │  • Fetch PR diffs        │  │  • Rank spells       │     │
│  │  • Extract errors        │  │  • Similarity calc   │     │
│  │  • GitHub API client     │  │  • [Vector DB hook]  │     │
│  └──────────────┬───────────┘  └───────┬──────────────┘     │
│                 │                       │                    │
│  ┌──────────────▼───────────────────────▼──────────────┐    │
│  │              Data Layer                              │    │
│  │  • SQLAlchemy 2.0 async ORM                         │    │
│  │  • SQLite with aiosqlite driver                     │    │
│  │  • Alembic migrations                               │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Framework**: FastAPI 0.104+ (async ASGI)
- **Python**: 3.11
- **Database**: SQLite with aiosqlite async driver
- **ORM**: SQLAlchemy 2.0 (async session)
- **Migrations**: Alembic
- **Server**: Uvicorn (ASGI server)
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Testing**: pytest + pytest-asyncio + Hypothesis (property-based testing)

### Design Principles

1. **Async-First**: All I/O operations use async/await for non-blocking performance
2. **Layered Architecture**: Clear separation between API, service, and data layers
3. **Dependency Injection**: FastAPI's dependency system for database sessions and services
4. **Configuration as Code**: Environment variables with Pydantic settings
5. **Extensibility**: Stub functions and comments marking future integration points
6. **Security**: Webhook signature validation, no hardcoded secrets
7. **Developer Experience**: Auto-generated OpenAPI docs, type hints throughout

## Components and Interfaces

### 1. API Layer

#### `/webhook` Endpoint (webhook.py)

```python
@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> dict
```

**Responsibilities:**
- Receive GitHub webhook POST requests
- Validate HMAC-SHA256 signature against shared secret
- Parse pull_request event payload
- Trigger PR processor service
- Return acknowledgment response

**Security:**
- Signature validation using `hmac.compare_digest()` for timing-attack resistance
- Reject invalid signatures with 401 status
- Log security violations

#### `/api/spells` Endpoints (spells.py)

```python
# List spells with pagination
@router.get("/api/spells")
async def list_spells(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[SpellResponse]

# Get single spell
@router.get("/api/spells/{spell_id}")
async def get_spell(
    spell_id: int,
    db: AsyncSession = Depends(get_db)
) -> SpellResponse

# Create spell
@router.post("/api/spells", status_code=201)
async def create_spell(
    spell: SpellCreate,
    db: AsyncSession = Depends(get_db)
) -> SpellResponse

# Update spell
@router.put("/api/spells/{spell_id}")
async def update_spell(
    spell_id: int,
    spell: SpellUpdate,
    db: AsyncSession = Depends(get_db)
) -> SpellResponse

# Delete spell
@router.delete("/api/spells/{spell_id}", status_code=204)
async def delete_spell(
    spell_id: int,
    db: AsyncSession = Depends(get_db)
) -> None
```

**Responsibilities:**
- CRUD operations for spell management
- Request validation using Pydantic models
- Database session management via dependency injection
- HTTP status code handling (200, 201, 204, 404)

### 2. Service Layer

#### PR Processor Service (pr_processor.py)

```python
class PRProcessor:
    async def process_pr_event(self, payload: dict) -> dict:
        """
        Process GitHub pull request webhook event.
        
        Steps:
        1. Extract repo and PR number from payload
        2. Fetch PR diff from GitHub API
        3. Parse diff to extract changed files
        4. [TODO: Extract error patterns using MCP analyzers]
        5. [TODO: Trigger matcher service with errors]
        6. Return processing result
        """
        
    async def fetch_pr_diff(self, repo: str, pr_number: int) -> str:
        """
        Fetch PR diff from GitHub API.
        
        TODO: Add authentication using GitHub App or PAT
        Extension point: Add retry logic and rate limit handling
        """
```

**Responsibilities:**
- Orchestrate PR event processing workflow
- Fetch PR diffs via GitHub REST API
- Parse diff format to extract file changes
- **Extension Point**: MCP analyzer integration for error extraction
- **Extension Point**: Sandbox runner for testing code changes

**GitHub API Integration:**
- Endpoint: `GET /repos/{owner}/{repo}/pulls/{pr_number}`
- Headers: `Accept: application/vnd.github.v3.diff`
- Authentication: TODO - GitHub App installation token or PAT

#### Matcher Service (matcher.py)

```python
class MatcherService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def match_spells(self, error_payload: dict) -> List[int]:
        """
        Match error payload with relevant spells and return ranked IDs.
        
        Args:
            error_payload: Dict containing error_type, message, context, stack_trace
            
        Returns:
            List of spell IDs sorted by relevance (highest first)
            
        Current implementation: Simple keyword matching
        
        Extension points:
        - [TODO: Vector DB integration] Replace keyword matching with 
          semantic similarity using embeddings (e.g., pgvector, Qdrant)
        - [TODO: Kiro vibe-code] Integrate Kiro's code understanding for
          context-aware matching
        - [TODO: MCP analyzers] Use MCP protocol to analyze error context
          and improve matching accuracy
        """
        
    async def _compute_similarity(self, error: dict, spell: Spell) -> float:
        """
        Compute similarity score between error and spell.
        
        Current: Simple keyword overlap
        Future: Cosine similarity on embeddings
        """
```

**Responsibilities:**
- Accept error payload with type, message, context
- Query database for candidate spells
- Rank spells by similarity score
- Return sorted list of spell IDs
- **Extension Point**: Vector database for semantic similarity
- **Extension Point**: Kiro integration for IDE-aware matching

**Matching Algorithm (v1 - Simple):**
1. Extract keywords from error message
2. Query spells with matching error types
3. Compute keyword overlap score
4. Sort by score descending
5. Return top N spell IDs

**Future Enhancement (Vector DB):**
- Generate embeddings for error descriptions
- Store spell embeddings in vector database
- Use cosine similarity for semantic matching
- Support hybrid search (keyword + vector)

### 3. Data Layer

#### Database Configuration (db/database.py)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./grimoire.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Log SQL in development
    future=True
)

async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes to get database session."""
    async with async_session_maker() as session:
        yield session
```

**Configuration:**
- SQLite file: `./grimoire.db` (relative to app root)
- Async driver: aiosqlite
- Connection pooling: Handled by SQLAlchemy
- Session lifecycle: Per-request via FastAPI dependency

#### Alembic Migrations

```bash
# Initialize Alembic
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Create spells table"

# Apply migrations
alembic upgrade head
```

**Migration Strategy:**
- Auto-generate migrations from SQLAlchemy models
- Version control all migration files
- Run migrations on container startup (optional)
- Support rollback for schema changes

## Data Models

### Spell Model (models/spell.py)

```python
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Spell(Base):
    """
    Represents a reusable code solution or pattern.
    
    A spell captures a specific error pattern and its solution,
    including code snippets, explanations, and metadata for matching.
    """
    __tablename__ = "spells"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    error_type = Column(String(100), nullable=False, index=True)
    error_pattern = Column(Text, nullable=False)
    solution_code = Column(Text, nullable=False)
    tags = Column(String(500))  # Comma-separated tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Extension point: Add vector embedding column when integrating vector DB
    # embedding = Column(Vector(1536))  # For OpenAI ada-002 embeddings
```

**Fields:**
- `id`: Primary key, auto-increment
- `title`: Short name for the spell (e.g., "Fix undefined variable")
- `description`: Detailed explanation of the problem and solution
- `error_type`: Category (e.g., "TypeError", "SyntaxError", "ImportError")
- `error_pattern`: Regex or text pattern to match errors
- `solution_code`: Code snippet that fixes the error
- `tags`: Searchable keywords (comma-separated)
- `created_at`: Timestamp of creation
- `updated_at`: Timestamp of last modification

**Indexes:**
- Primary key on `id`
- Index on `title` for search
- Index on `error_type` for filtering

### Pydantic Schemas

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class SpellBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    error_type: str = Field(..., min_length=1, max_length=100)
    error_pattern: str = Field(..., min_length=1)
    solution_code: str = Field(..., min_length=1)
    tags: Optional[str] = None

class SpellCreate(SpellBase):
    """Schema for creating a new spell."""
    pass

class SpellUpdate(SpellBase):
    """Schema for updating an existing spell."""
    pass

class SpellResponse(SpellBase):
    """Schema for spell responses (includes DB fields)."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True  # SQLAlchemy 2.0 compatibility
```

**Validation:**
- All string fields have length constraints
- Required fields enforced by Pydantic
- Automatic serialization from SQLAlchemy models
- Type safety with Python type hints


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Webhook signature validation correctness

*For any* webhook payload and secret key, computing the HMAC-SHA256 signature and validating it should return true if and only if the signature matches the expected value computed from the payload and secret.

**Validates: Requirements 1.2**

### Property 2: Webhook payload parsing preserves structure

*For any* valid GitHub pull_request webhook JSON payload, parsing the payload should successfully extract all required fields (repository name, PR number, action) without data loss or corruption.

**Validates: Requirements 1.4**

### Property 3: Spell pagination consistency

*For any* collection of spells in the database and any valid pagination parameters (skip, limit), the paginated results should contain the correct subset of spells, and iterating through all pages should return all spells exactly once without duplicates or omissions.

**Validates: Requirements 2.1**

### Property 4: Spell retrieval returns stored data

*For any* spell stored in the database, retrieving it by ID should return a spell object with all fields matching the originally stored values.

**Validates: Requirements 2.2**

### Property 5: Spell CRUD round-trip consistency

*For any* valid spell data, creating a spell in the database and then retrieving it should return the same data, and updating a spell and then retrieving it should return the updated data with all changes preserved.

**Validates: Requirements 2.4, 2.5, 3.3**

### Property 6: Spell deletion removes data

*For any* spell in the database, deleting it by ID should result in subsequent retrieval attempts returning a 404 error, and the spell should not appear in list queries.

**Validates: Requirements 2.6**

### Property 7: PR metadata extraction correctness

*For any* valid GitHub webhook payload containing pull request information, extracting the repository name and PR number should return values that match the corresponding fields in the original payload structure.

**Validates: Requirements 4.1**

### Property 8: Diff parsing extracts file changes

*For any* valid GitHub diff format response, parsing the diff should extract all changed files with their modifications, and the extracted data should preserve the file paths and change types (added, modified, deleted).

**Validates: Requirements 4.3**

### Property 9: Error payload extraction completeness

*For any* error payload containing error information, extracting error characteristics should return all required fields (error_type, message, context) without data loss.

**Validates: Requirements 5.1**

### Property 10: Similarity score computation is deterministic

*For any* error payload and spell, computing the similarity score multiple times should always return the same value, ensuring consistent ranking behavior.

**Validates: Requirements 5.3**

### Property 11: Spell ranking maintains sort order

*For any* list of spells with computed similarity scores, the returned spell IDs should be ordered such that each spell's score is greater than or equal to the next spell's score (descending order).

**Validates: Requirements 5.4**

## Error Handling

### Error Categories

1. **Client Errors (4xx)**
   - 400 Bad Request: Invalid request body or parameters
   - 401 Unauthorized: Invalid webhook signature
   - 404 Not Found: Spell ID does not exist
   - 422 Unprocessable Entity: Validation errors from Pydantic

2. **Server Errors (5xx)**
   - 500 Internal Server Error: Unexpected application errors
   - 503 Service Unavailable: Database connection failures

### Error Response Format

```python
{
    "detail": "Human-readable error message",
    "error_code": "SPELL_NOT_FOUND",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Handling Strategy

**Webhook Endpoint:**
- Invalid signature → 401 with security log
- Malformed JSON → 400 with parsing error details
- Processing failure → 500 with error logged, 200 returned to GitHub (prevent retries)

**Spell API:**
- Validation errors → 422 with field-level error details
- Not found → 404 with spell ID in message
- Database errors → 500 with generic message (hide internal details)

**Service Layer:**
- GitHub API failures → Log error, return error status to caller
- Database connection errors → Raise exception, let FastAPI handle
- Parsing errors → Log warning, return empty/default values where safe

**Logging:**
- All errors logged with context (request ID, user action, timestamp)
- Security violations logged at WARNING level
- Application errors logged at ERROR level
- Include stack traces for 5xx errors in development mode

## Testing Strategy

### Unit Testing

**Framework:** pytest with pytest-asyncio for async test support

**Coverage Areas:**
- **API Endpoints**: Test each route with valid/invalid inputs
  - Example: POST /api/spells with missing required fields should return 422
  - Example: GET /api/spells/{id} with non-existent ID should return 404
  - Example: Webhook with invalid signature should return 401
  
- **Service Functions**: Test business logic in isolation
  - Example: PR processor extracts correct repo name from webhook payload
  - Example: Matcher service returns empty list when no spells match
  
- **Database Operations**: Test CRUD with in-memory SQLite
  - Example: Creating a spell and querying it returns the same data
  - Example: Deleting a spell removes it from subsequent queries

**Test Organization:**
```
tests/
├── test_api/
│   ├── test_webhook.py
│   └── test_spells.py
├── test_services/
│   ├── test_pr_processor.py
│   └── test_matcher.py
└── test_models/
    └── test_spell.py
```

### Property-Based Testing

**Framework:** Hypothesis (Python property-based testing library)

**Configuration:**
- Minimum 100 iterations per property test
- Use Hypothesis strategies to generate random test data
- Each property test tagged with comment referencing design doc property

**Property Test Implementation:**
- Each correctness property from the design document MUST be implemented as a single property-based test
- Tests MUST be tagged with: `# Feature: grimoire-engine-backend, Property {N}: {property_text}`
- Tests MUST use Hypothesis to generate random inputs covering the input space
- Tests MUST verify the property holds across all generated inputs

**Example Property Test Structure:**
```python
from hypothesis import given, strategies as st

# Feature: grimoire-engine-backend, Property 5: Spell CRUD round-trip consistency
@given(spell_data=st.builds(SpellCreate, ...))
async def test_spell_crud_roundtrip(spell_data):
    """For any valid spell data, create->retrieve should preserve data."""
    created = await create_spell(spell_data)
    retrieved = await get_spell(created.id)
    assert created == retrieved
```

**Property Test Coverage:**
- Property 1: Webhook signature validation (generate random payloads + secrets)
- Property 2: Webhook parsing (generate valid webhook structures)
- Property 3: Pagination consistency (generate random spell collections)
- Property 4: Spell retrieval (generate random spells)
- Property 5: CRUD round-trip (generate random spell data)
- Property 6: Deletion removes data (generate random spells)
- Property 7: PR metadata extraction (generate random webhook payloads)
- Property 8: Diff parsing (generate valid diff formats)
- Property 9: Error extraction (generate random error payloads)
- Property 10: Similarity determinism (generate random errors + spells)
- Property 11: Ranking sort order (generate random spell scores)

### Integration Testing

**Scope:** Test complete request flows with real database

**Test Cases:**
- End-to-end webhook processing: Receive webhook → process PR → store results
- Complete spell lifecycle: Create → Read → Update → Delete
- Matcher integration: Store spells → match error → verify ranked results

**Database Strategy:**
- Use separate test database (`:memory:` SQLite)
- Reset database between tests
- Use fixtures for common test data

### Test Execution

**Local Development:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run only property tests
pytest -m property

# Run specific test file
pytest tests/test_api/test_spells.py
```

**CI/CD:**
- Run full test suite on every push
- Fail build if coverage drops below 80%
- Run linting (ruff, mypy) before tests
- Generate and upload coverage reports

## Deployment

### Docker Configuration

**Dockerfile:**
- Base image: `python:3.11-slim`
- Install dependencies from `requirements.txt`
- Copy application code
- Expose port 8000
- Run with uvicorn: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

**docker-compose.yml:**
- Single service: `grimoire-api`
- Volume mount for SQLite database persistence: `./data:/app/data`
- Environment variables from `.env` file
- Port mapping: `8000:8000`
- Health check: `curl http://localhost:8000/health`

### Environment Configuration

**.env.example:**
```bash
# Application
APP_ENV=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/grimoire.db

# GitHub
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_API_TOKEN=your_github_token_here

# API
API_HOST=0.0.0.0
API_PORT=8000
```

**Configuration Loading:**
- Use Pydantic Settings for type-safe config
- Load from environment variables with `.env` file support
- Validate required settings on startup
- Provide sensible defaults for development

### CI/CD Pipeline

**GitHub Actions Workflow (.github/workflows/ci.yml):**

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run linting
        run: ruff check app/
      - name: Run type checking
        run: mypy app/
      - name: Run tests
        run: pytest --cov=app
```

**Pipeline Steps:**
1. Checkout code
2. Setup Python 3.11
3. Install dependencies
4. Run linting (ruff)
5. Run type checking (mypy)
6. Run test suite with coverage
7. Fail if any step fails

## Extension Points

### Vector Database Integration

**Location:** `app/services/matcher.py`

**Current Implementation:**
```python
async def _compute_similarity(self, error: dict, spell: Spell) -> float:
    """
    Compute similarity score between error and spell.
    
    Current: Simple keyword overlap
    
    TODO: Vector DB Integration
    - Generate embeddings for error description using OpenAI/Cohere API
    - Query vector database (pgvector, Qdrant, Pinecone) for similar spell embeddings
    - Use cosine similarity for semantic matching
    - Combine keyword and vector scores for hybrid search
    
    Extension steps:
    1. Add embedding generation function
    2. Store spell embeddings in vector DB on creation
    3. Replace keyword matching with vector similarity query
    4. Add embedding column to Spell model
    """
    # Simple keyword matching implementation
    pass
```

### Sandbox Runner Integration

**Location:** `app/services/pr_processor.py`

**Current Implementation:**
```python
async def process_pr_event(self, payload: dict) -> dict:
    """
    Process GitHub pull request webhook event.
    
    TODO: Sandbox Runner Integration
    - Extract code changes from PR diff
    - Create isolated execution environment (Docker container, VM)
    - Run tests in sandbox with PR changes applied
    - Capture errors, stack traces, and test failures
    - Return structured error data for matching
    
    Extension steps:
    1. Add sandbox creation function (Docker API, Firecracker)
    2. Implement code injection into sandbox
    3. Add test execution and error capture
    4. Parse test output for error patterns
    5. Clean up sandbox after execution
    
    Security considerations:
    - Resource limits (CPU, memory, time)
    - Network isolation
    - File system restrictions
    """
    pass
```

### MCP Analyzer Integration

**Location:** `app/services/pr_processor.py` (error extraction)

**Current Implementation:**
```python
async def extract_errors(self, diff: str) -> List[dict]:
    """
    Extract error patterns from PR diff.
    
    TODO: MCP Analyzer Integration
    - Use Model Context Protocol to analyze code changes
    - Call MCP analyzers for static analysis (linting, type checking)
    - Extract semantic error patterns beyond syntax
    - Identify code smells and potential bugs
    - Return structured error data with context
    
    Extension steps:
    1. Add MCP client library
    2. Configure MCP server endpoints (language servers, linters)
    3. Send code changes to MCP analyzers
    4. Parse MCP responses for error information
    5. Normalize error formats across different analyzers
    
    MCP analyzers to integrate:
    - Python: pylint, mypy, ruff
    - JavaScript: ESLint, TypeScript compiler
    - General: CodeQL, Semgrep
    """
    pass
```

### Kiro Vibe-Code Integration

**Location:** `app/services/matcher.py` (context-aware matching)

**Current Implementation:**
```python
async def match_spells(self, error_payload: dict) -> List[int]:
    """
    Match error payload with relevant spells.
    
    TODO: Kiro Vibe-Code Integration
    - Use Kiro's code understanding for context-aware matching
    - Analyze codebase structure and patterns
    - Consider project-specific conventions and styles
    - Rank spells based on project context fit
    - Integrate with Kiro IDE for seamless developer experience
    
    Extension steps:
    1. Add Kiro API client
    2. Send error context to Kiro for analysis
    3. Receive Kiro's code understanding insights
    4. Adjust spell ranking based on project context
    5. Provide IDE integration hooks for spell application
    
    Kiro features to leverage:
    - Code pattern recognition
    - Project-specific style analysis
    - Dependency and import understanding
    - Test coverage awareness
    """
    pass
```

## Security Considerations

### Webhook Security

- **Signature Validation**: All webhook requests MUST validate HMAC-SHA256 signature
- **Timing Attack Prevention**: Use `hmac.compare_digest()` for constant-time comparison
- **Secret Management**: Store webhook secret in environment variables, never in code
- **Request Logging**: Log all webhook requests with signature validation results

### API Security

- **Input Validation**: All request data validated by Pydantic schemas
- **SQL Injection**: Prevented by SQLAlchemy parameterized queries
- **Rate Limiting**: TODO - Add rate limiting middleware for production
- **CORS**: Configure CORS headers for allowed origins only

### Data Security

- **Secrets in Logs**: Never log sensitive values (tokens, secrets, passwords)
- **Database Encryption**: SQLite file should be encrypted at rest in production
- **Environment Variables**: Use `.env` file for local dev, secure secret management in production

### GitHub API Security

- **Token Storage**: Store GitHub API tokens in environment variables
- **Token Scope**: Use minimal required scopes (read:repo for PR access)
- **Token Rotation**: Support token rotation without code changes
- **Rate Limit Handling**: Respect GitHub API rate limits, implement backoff

## Performance Considerations

### Async Operations

- All I/O operations use async/await for non-blocking execution
- Database queries use async SQLAlchemy sessions
- HTTP requests to GitHub API use async HTTP client (httpx)
- FastAPI handles concurrent requests efficiently with async handlers

### Database Optimization

- Indexes on frequently queried columns (id, title, error_type)
- Pagination to limit result set sizes
- Connection pooling managed by SQLAlchemy
- Query optimization: Select only needed columns

### Caching Strategy (Future)

- Cache frequently accessed spells in Redis
- Cache GitHub API responses with TTL
- Invalidate cache on spell updates
- Use ETags for conditional requests

### Scalability Path

**Current (Hackathon):**
- Single container with SQLite
- Suitable for development and demos
- Low resource requirements

**Future (Production):**
- Migrate to PostgreSQL for concurrent writes
- Add Redis for caching and session storage
- Horizontal scaling with load balancer
- Separate worker processes for background tasks
- Vector database for semantic search (Qdrant, Pinecone)

## Development Workflow

### Local Setup

```bash
# Clone repository
git clone <repo-url>
cd grimoire-backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your values

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Docker Development

```bash
# Build and start services
docker-compose up --build

# View logs
docker-compose logs -f

# Run migrations in container
docker-compose exec grimoire-api alembic upgrade head

# Stop services
docker-compose down
```

### Code Quality

**Linting:**
```bash
ruff check app/
ruff format app/
```

**Type Checking:**
```bash
mypy app/
```

**Testing:**
```bash
pytest
pytest --cov=app --cov-report=html
```

### Git Workflow

1. Create feature branch from `main`
2. Make changes with descriptive commits
3. Run tests and linting locally
4. Push branch and create pull request
5. CI pipeline runs automatically
6. Merge after approval and passing CI

## Documentation

### API Documentation

- **Interactive Docs**: Available at `/docs` (Swagger UI)
- **ReDoc**: Available at `/redoc` (alternative UI)
- **OpenAPI Schema**: Available at `/openapi.json`

### Code Documentation

- All modules include docstrings explaining purpose
- All functions include docstrings with Args, Returns, Raises
- Extension points marked with TODO comments
- Complex logic includes inline comments

### README

The project README should include:
- Project overview and goals
- Quick start guide
- API endpoint documentation
- Environment variable reference
- Development setup instructions
- Docker deployment guide
- Contributing guidelines
- License information
