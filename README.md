# Grimoire Engine Backend

A FastAPI-based backend service that captures GitHub pull request errors and matches them with solution "spells" - reusable code fixes and patterns. Built for hackathon-speed development with extensibility for future enhancements.

## 🚀 Features

- **GitHub Webhook Integration**: Automatically receive and process PR events
- **Spell Management**: Full CRUD API for managing code solution patterns
- **Error Matching**: Rank and match errors with relevant solution spells
- **🆕 AI-Powered Auto-Generation**: Automatically create spells using LLMs (OpenAI/Anthropic) when no matches found
- **Async Architecture**: Non-blocking I/O with FastAPI and SQLAlchemy 2.0
- **Docker Ready**: Containerized deployment with Docker Compose
- **Auto Documentation**: Interactive API docs at `/docs`
- **Extensible Design**: Ready for vector DB, sandbox execution, and IDE integrations

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [AI Auto-Generation Setup](#ai-auto-generation-setup)
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

## 🤖 AI Auto-Generation Setup

**NEW!** Grimoire can now automatically generate spells using AI when no matches are found.

### Quick Setup (5 minutes)

1. **Get an API key**:
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/

2. **Configure `.env`**:
   ```bash
   AUTO_CREATE_SPELLS=true
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4-turbo
   OPENAI_API_KEY=sk-your-key-here
   ```

3. **Run migration**:
   ```bash
   alembic upgrade head
   ```

4. **Test it**:
   ```bash
   python test_spell_generation.py
   ```

5. **Restart app**:
   ```bash
   uvicorn app.main:app --reload
   ```

📚 **Full documentation**: See [SETUP_AUTO_GENERATION.md](SETUP_AUTO_GENERATION.md) and [SPELL_AUTO_GENERATION.md](SPELL_AUTO_GENERATION.md)

### How It Works

When a PR is received and no matching spells exist:
1. Error context is extracted from the PR
2. LLM generates human-readable title, description, and solution
3. New spell is automatically created in the database
4. Spell is marked as auto-generated with confidence score
5. Can be reviewed and refined by humans later

**Cost**: ~$0.01-0.02 per spell with GPT-4, ~$0.002 with GPT-3.5

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

# JWT Authentication Configuration
SECRET_KEY=your_secret_key_here                      # Secret key for JWT signing (generate with: openssl rand -hex 32)
ALGORITHM=HS256                                      # JWT signing algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=1440                     # Token expiration time (24 hours)

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

### JWT Secret Key

Generate a secure secret key for JWT token signing:

```bash
# Using OpenSSL (recommended)
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

Add the generated key to your `.env` file as `SECRET_KEY`. Never commit this key to version control.

## 📚 API Documentation

### Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Comprehensive API Documentation

For detailed API documentation including all endpoints, request/response schemas, error handling, and examples:

📖 **[View Complete API Documentation](API_DOCUMENTATION.md)**

The comprehensive documentation covers:
- Repository Configuration API (manage webhook integrations)
- Webhook Logs API (monitor webhook executions)
- Authentication and authorization
- Request/response schemas with examples
- Error handling and status codes
- Best practices and usage patterns

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

### Authentication API

The authentication system uses JWT (JSON Web Token) for secure, stateless authentication. All protected endpoints require a valid Bearer token in the Authorization header.

#### User Signup

```http
POST /auth/signup
```

Register a new user account with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Validation Rules:**
- Email must be a valid email format
- Password must be at least 8 characters long

**Response (201 Created):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Error Responses:**
- `422 Unprocessable Entity`: Invalid email format or password too short
- `409 Conflict`: Email already registered

#### User Login

```http
POST /auth/login
```

Authenticate with email and password to receive an access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Error Response:**
- `401 Unauthorized`: Incorrect email or password

#### User Logout

```http
POST /auth/logout
```

Log out the current user. Requires authentication.

**Headers:**
```
Authorization: Bearer <your_access_token>
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

**Note:** In a stateless JWT system, logout is handled client-side by removing the token. The server confirms the request but doesn't invalidate the token server-side.

**Error Response:**
- `401 Unauthorized`: Missing or invalid token

#### Get Current User

```http
GET /auth/me
```

Retrieve information about the currently authenticated user. This is a protected endpoint.

**Headers:**
```
Authorization: Bearer <your_access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Missing, invalid, or expired token

#### Using Bearer Tokens

After successful signup or login, include the access token in the Authorization header for all protected endpoints:

```bash
# Example using curl
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  http://localhost:8000/auth/me

# Example using httpie
http GET http://localhost:8000/auth/me \
  Authorization:"Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# Example using JavaScript fetch
fetch('http://localhost:8000/auth/me', {
  headers: {
    'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...'
  }
})
```

**Token Details:**
- Tokens expire after 24 hours
- Tokens are signed with HS256 algorithm
- Tokens contain user ID and expiration time

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
