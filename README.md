# Grimoire Engine Backend

A FastAPI-based backend service that captures GitHub pull request errors and matches them with solution "spells" - reusable code fixes and patterns. Built for hackathon-speed development with extensibility for future enhancements.

## 🚀 Features

- **GitHub Webhook Integration**: Automatically receive and process PR events
- **Spell Management**: Full CRUD API for managing code solution patterns
- **Error Matching**: Rank and match errors with relevant solution spells
- **Async Architecture**: Non-blocking I/O with FastAPI and SQLAlchemy 2.0
- **Docker Ready**: Containerized deployment with Docker Compose
- **Auto Documentation**: Interactive API docs at `/docs`
- **Extensible Design**: Ready for vector DB, sandbox execution, and IDE integrations

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Docker Deployment](#docker-deployment)
- [Testing](#testing)
- [Extension Points](#extension-points)
- [Project Structure](#project-structure)

## ⚡ Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd grimoire-engine-backend

# Create and configure environment file
cp .env.example .env
# Edit .env with your GitHub webhook secret and API token

# Start the service
docker compose up --build

# Access the API
# - API: http://localhost:8000
# - Interactive docs: http://localhost:8000/docs
# - Health check: http://localhost:8000/health
```

### Local Development

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload

# Access at http://localhost:8000
```

## 📦 Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git
- Docker and Docker Compose (for containerized deployment)

### Dependencies

The project uses the following key dependencies:

- **FastAPI 0.104+**: Modern async web framework
- **SQLAlchemy 2.0**: Async ORM for database operations
- **SQLite + aiosqlite**: Lightweight async database
- **Alembic**: Database migration management
- **Uvicorn**: ASGI server
- **Hypothesis**: Property-based testing
- **pytest**: Testing framework

See `requirements.txt` for the complete list.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Application Configuration
APP_ENV=development              # Environment: development, staging, production
LOG_LEVEL=INFO                   # Logging level: DEBUG, INFO, WARNING, ERROR

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./data/grimoire.db  # SQLite database path

# GitHub Configuration
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here       # Secret for webhook validation
GITHUB_API_TOKEN=your_github_token_here              # Token for GitHub API requests

# API Configuration
API_HOST=0.0.0.0                 # Host to bind the server
API_PORT=8000                    # Port to run the server

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8000  # Allowed origins (comma-separated)
```

### GitHub Webhook Setup

1. Go to your GitHub repository settings
2. Navigate to **Webhooks** → **Add webhook**
3. Set **Payload URL** to: `https://your-domain.com/webhook`
4. Set **Content type** to: `application/json`
5. Set **Secret** to match your `GITHUB_WEBHOOK_SECRET`
6. Select events: **Pull requests**
7. Click **Add webhook**

### GitHub API Token

Create a Personal Access Token (PAT) or GitHub App token with the following permissions:
- `repo` scope (for private repositories)
- `public_repo` scope (for public repositories only)

Add the token to your `.env` file as `GITHUB_API_TOKEN`.

## 📚 API Documentation

### Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints Overview

#### Health Check

```http
GET /health
```

Returns the health status of the API.

**Response:**
```json
{
  "status": "healthy",
  "service": "grimoire-engine-backend"
}
```

#### Webhook Endpoint

```http
POST /webhook
```

Receives GitHub webhook events for pull requests.

**Headers:**
- `X-Hub-Signature-256`: GitHub webhook signature
- `X-GitHub-Event`: Event type (e.g., "pull_request")

**Response:**
```json
{
  "status": "success",
  "event": "pull_request",
  "action": "opened"
}
```

### Spell Management API

#### List Spells

```http
GET /api/spells?skip=0&limit=100
```

Retrieve a paginated list of spells.

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum records to return (default: 100)

**Response:**
```json
[
  {
    "id": 1,
    "title": "Fix undefined variable",
    "description": "Solution for undefined variable errors in Python",
    "error_type": "NameError",
    "error_pattern": "name '.*' is not defined",
    "solution_code": "# Define the variable before use\nvariable_name = initial_value",
    "tags": "python,variables",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Get Single Spell

```http
GET /api/spells/{spell_id}
```

Retrieve a specific spell by ID.

**Response:**
```json
{
  "id": 1,
  "title": "Fix undefined variable",
  "description": "Solution for undefined variable errors in Python",
  "error_type": "NameError",
  "error_pattern": "name '.*' is not defined",
  "solution_code": "# Define the variable before use\nvariable_name = initial_value",
  "tags": "python,variables",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Response (404):**
```json
{
  "detail": "Spell with id 999 not found"
}
```

#### Create Spell

```http
POST /api/spells
```

Create a new spell.

**Request Body:**
```json
{
  "title": "Fix undefined variable",
  "description": "Solution for undefined variable errors in Python",
  "error_type": "NameError",
  "error_pattern": "name '.*' is not defined",
  "solution_code": "# Define the variable before use\nvariable_name = initial_value",
  "tags": "python,variables"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "title": "Fix undefined variable",
  "description": "Solution for undefined variable errors in Python",
  "error_type": "NameError",
  "error_pattern": "name '.*' is not defined",
  "solution_code": "# Define the variable before use\nvariable_name = initial_value",
  "tags": "python,variables",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": null
}
```

#### Update Spell

```http
PUT /api/spells/{spell_id}
```

Update an existing spell.

**Request Body:**
```json
{
  "title": "Fix undefined variable (updated)",
  "description": "Updated solution for undefined variable errors",
  "error_type": "NameError",
  "error_pattern": "name '.*' is not defined",
  "solution_code": "# Updated solution code",
  "tags": "python,variables,updated"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Fix undefined variable (updated)",
  "description": "Updated solution for undefined variable errors",
  "error_type": "NameError",
  "error_pattern": "name '.*' is not defined",
  "solution_code": "# Updated solution code",
  "tags": "python,variables,updated",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

#### Delete Spell

```http
DELETE /api/spells/{spell_id}
```

Delete a spell by ID.

**Response:** 204 No Content

**Error Response (404):**
```json
{
  "detail": "Spell with id 999 not found"
}
```

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd grimoire-engine-backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start development server with auto-reload
uvicorn app.main:app --reload --log-level debug
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Code Quality

```bash
# Run linting
ruff check app/

# Format code
ruff format app/

# Type checking
mypy app/

# Run all quality checks
ruff check app/ && mypy app/
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_spell_api.py

# Run with verbose output
pytest -v

# Run property-based tests only
pytest tests/test_spell_properties.py
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_main.py             # Main app tests
├── test_spell_api.py        # Spell CRUD API tests
├── test_spell_properties.py # Property-based tests
├── test_webhook.py          # Webhook endpoint tests
├── test_pr_processor.py     # PR processor service tests
└── test_matcher.py          # Matcher service tests
```

### Property-Based Testing

The project uses Hypothesis for property-based testing to verify correctness properties:

- **Property 5**: Spell CRUD round-trip consistency
- Tests run with 100+ iterations to catch edge cases
- See `tests/test_spell_properties.py` for examples

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Build and start
docker compose up --build

# Start in background
docker compose up -d

# View logs
docker compose logs -f grimoire-api

# Stop services
docker compose down

# Remove volumes (deletes database)
docker compose down -v
```

### Using Docker Directly

```bash
# Build image
docker build -t grimoire-engine-backend .

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  grimoire-engine-backend
```

### Data Persistence

The SQLite database is stored in `./data/grimoire.db` and mounted as a volume. Your data persists across container restarts.

```bash
# Create data directory
mkdir -p data
chmod 755 data
```

See [DOCKER.md](DOCKER.md) for detailed Docker deployment instructions.

## 🔌 Extension Points

The codebase includes clearly marked extension points for future enhancements:

### 1. Vector Database Integration

**Location:** `app/services/matcher.py`

Replace simple keyword matching with semantic similarity using embeddings:
- Add embedding generation (OpenAI, Cohere, etc.)
- Integrate vector database (pgvector, Qdrant, Pinecone)
- Implement cosine similarity search
- Support hybrid search (keyword + vector)

```python
# TODO: Vector DB Integration
# - Generate embeddings for error descriptions
# - Query vector database for similar spell embeddings
# - Use cosine similarity for semantic matching
```

### 2. Sandbox Runner Integration

**Location:** `app/services/pr_processor.py`

Execute code changes in isolated environments:
- Create sandbox containers (Docker, Firecracker)
- Run tests with PR changes applied
- Capture errors and stack traces
- Implement resource limits and security controls

```python
# TODO: Sandbox Runner Integration
# - Extract code changes from PR diff
# - Create isolated execution environment
# - Run tests in sandbox and capture errors
```

### 3. MCP Analyzer Integration

**Location:** `app/services/pr_processor.py`

Use Model Context Protocol for advanced code analysis:
- Integrate language servers (pylint, mypy, ESLint)
- Perform static analysis on code changes
- Extract semantic error patterns
- Identify code smells and potential bugs

```python
# TODO: MCP Analyzer Integration
# - Use Model Context Protocol for code analysis
# - Call MCP analyzers for static analysis
# - Extract semantic error patterns
```

### 4. Kiro IDE Integration

**Location:** `app/services/matcher.py`

Connect with Kiro IDE for context-aware matching:
- Analyze codebase structure and patterns
- Consider project-specific conventions
- Rank spells based on project context
- Provide seamless IDE integration

```python
# TODO: Kiro Vibe-Code Integration
# - Use Kiro's code understanding for context-aware matching
# - Analyze codebase structure and patterns
# - Adjust spell ranking based on project context
```

## 📁 Project Structure

```
grimoire-engine-backend/
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI workflow
├── alembic/
│   ├── versions/            # Database migration files
│   ├── env.py              # Alembic environment config
│   └── script.py.mako      # Migration template
├── app/
│   ├── api/
│   │   ├── spells.py       # Spell CRUD endpoints
│   │   └── webhook.py      # GitHub webhook endpoint
│   ├── db/
│   │   └── database.py     # Database configuration
│   ├── models/
│   │   └── spell.py        # Spell data model
│   ├── services/
│   │   ├── matcher.py      # Spell matching service
│   │   └── pr_processor.py # PR processing service
│   └── main.py             # FastAPI application
├── tests/
│   ├── conftest.py         # Test fixtures
│   ├── test_*.py           # Test files
│   └── ...
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── alembic.ini             # Alembic configuration
├── docker-compose.yml      # Docker Compose config
├── Dockerfile              # Docker image definition
├── DOCKER.md               # Docker deployment guide
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

## 🔒 Security Considerations

- **Webhook Validation**: All webhook requests validated with HMAC-SHA256
- **Timing Attack Prevention**: Uses `hmac.compare_digest()` for secure comparison
- **Secret Management**: Secrets stored in environment variables, never in code
- **Input Validation**: All API inputs validated with Pydantic schemas
- **SQL Injection**: Prevented by SQLAlchemy parameterized queries
- **CORS**: Configure allowed origins in production

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Contact

[Add contact information here]

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Hypothesis](https://hypothesis.readthedocs.io/)
- [Uvicorn](https://www.uvicorn.org/)
