# Design Document

## Overview

The Spell Application feature enables developers to generate context-aware code patches by adapting canonical spell solutions to their specific failing code. The system uses LLM-based prompt engineering to transform a spell's incantation (canonical solution) into a git unified diff patch tailored to the user's repository, language, version, and error context.

The feature consists of three main components:
1. **API Endpoint**: Receives spell application requests with failing context and constraints
2. **Patch Generator Service**: Constructs LLM prompts and generates adapted patches
3. **Application History Storage**: Persists generated patches and metadata for tracking and review

The design leverages the existing LLM Service infrastructure while adding new models, endpoints, and database tables to support patch generation and history tracking.

## Architecture

### System Components

```
┌─────────────────┐
│  Frontend UI    │
│  (Spell Detail) │
└────────┬────────┘
         │ POST /api/spells/{id}/apply
         ▼
┌─────────────────────────────────────┐
│     Spell Application API           │
│  (app/api/spells.py)                │
└────────┬────────────────────────────┘
         │
         ├──► Fetch Spell from DB
         │
         ▼
┌─────────────────────────────────────┐
│   Patch Generator Service           │
│  (app/services/patch_generator.py)  │
└────────┬────────────────────────────┘
         │
         ├──► Build LLM Prompt
         │
         ▼
┌─────────────────────────────────────┐
│      LLM Service                    │
│  (app/services/llm_service.py)      │
└────────┬────────────────────────────┘
         │
         ├──► Call OpenAI/Anthropic API
         │
         ▼
┌─────────────────────────────────────┐
│   Parse & Validate Response         │
│   - Extract patch                   │
│   - Validate format                 │
│   - Check constraints               │
└────────┬────────────────────────────┘
         │
         ├──► Store Application Record
         │
         ▼
┌─────────────────────────────────────┐
│      Database                       │
│  - spell_applications table         │
└─────────────────────────────────────┘
```

### Data Flow

1. User clicks "Apply Spell (Preview)" on spell detail page
2. Frontend sends POST request with spell_id and failing context
3. API endpoint validates request and fetches spell from database
4. Patch Generator Service constructs LLM prompt with context + incantation + constraints
5. LLM Service calls configured provider (OpenAI/Anthropic) with prompt
6. LLM returns JSON response with patch, files_touched, and rationale
7. System validates patch format and constraint compliance
8. Application record is stored in database
9. API returns structured response to frontend
10. Frontend displays patch in side-by-side diff viewer

## Components and Interfaces

### 1. Spell Application API Endpoint

**Location**: `app/api/spells.py`

**New Endpoint**:
```python
@router.post("/{spell_id}/apply", response_model=SpellApplicationResponse)
async def apply_spell(
    spell_id: int,
    request: SpellApplicationRequest,
    db: AsyncSession = Depends(get_db)
) -> SpellApplicationResponse
```

**Request Model** (`SpellApplicationRequest`):
```python
class SpellApplicationRequest(BaseModel):
    failing_context: FailingContext
    adaptation_constraints: Optional[AdaptationConstraints] = None
```

**Response Model** (`SpellApplicationResponse`):
```python
class SpellApplicationResponse(BaseModel):
    application_id: int
    patch: str
    files_touched: List[str]
    rationale: str
    created_at: datetime
```

**Error Responses**:
- 404: Spell not found
- 422: Invalid request or patch validation failed
- 500: LLM configuration error
- 502: LLM API error
- 504: LLM request timeout

### 2. Patch Generator Service

**Location**: `app/services/patch_generator.py`

**Main Class**:
```python
class PatchGeneratorService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
    
    async def generate_patch(
        self,
        spell: Spell,
        failing_context: FailingContext,
        constraints: AdaptationConstraints
    ) -> PatchResult:
        """Generate adapted patch using LLM."""
        pass
    
    def _build_prompt(
        self,
        spell: Spell,
        failing_context: FailingContext,
        constraints: AdaptationConstraints
    ) -> str:
        """Construct LLM prompt for patch generation."""
        pass
    
    def _validate_patch(
        self,
        patch: str,
        files_touched: List[str],
        constraints: AdaptationConstraints
    ) -> bool:
        """Validate patch format and constraint compliance."""
        pass
```

**Prompt Template**:
```
SYSTEM:
You are Kiro — an automated code patch generator. You will be given:
(1) failing context (stack trace, failing test name, repo language & version)
(2) a canonical spell incantation (git diff)
(3) adaptation constraints

Produce a git unified diff that applies to the repository at commit SHA: {commit_sha}.

Do not output anything other than: a JSON object with keys "patch" (string with unified git diff), "files_touched" (list of paths), and "rationale" (short, 1-2 lines).

Do NOT include explanations outside the JSON. If unable, return {"error": "..."}.

USER:
Context:
- language: {language}
- version: {version}
- failing_test: {test_name}
- stack: {stack_trace}
- repo_commit: {commit_sha}

Spell (incantation):
{spell_incantation}

Constraints:
- Limit changes to at most {max_files} files
- Keep coding style intact
- Do not change {excluded_patterns}

Return:
{"patch": "...git diff...", "files_touched": ["..."], "rationale": "..."}
```

### 3. LLM Service Extension

**Location**: `app/services/llm_service.py`

**New Method**:
```python
async def generate_patch(
    self,
    prompt: str,
    timeout: Optional[int] = 30
) -> Dict[str, Any]:
    """
    Generate patch using LLM with structured JSON output.
    
    Returns:
        Dict with keys: patch, files_touched, rationale
        Or: Dict with key: error
    """
    pass
```

This method will be similar to `generate_spell_content` but optimized for patch generation with stricter JSON validation.

### 4. Spell Application History Endpoint

**Location**: `app/api/spells.py`

**New Endpoint**:
```python
@router.get("/{spell_id}/applications", response_model=List[SpellApplicationSummary])
async def list_spell_applications(
    spell_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> List[SpellApplicationSummary]
```

**Response Model** (`SpellApplicationSummary`):
```python
class SpellApplicationSummary(BaseModel):
    id: int
    spell_id: int
    repository: str
    commit_sha: str
    files_touched: List[str]
    created_at: datetime
```

## Data Models

### SpellApplication Model

**Location**: `app/models/spell_application.py`

```python
class SpellApplication(Base):
    """
    SQLAlchemy model for spell application history.
    
    Tracks each time a spell is applied to generate a patch,
    storing the context, generated patch, and metadata.
    """
    __tablename__ = "spell_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    spell_id = Column(Integer, ForeignKey("spells.id"), nullable=False, index=True)
    
    # Failing context
    repository = Column(String(500), nullable=False)
    commit_sha = Column(String(40), nullable=False)
    language = Column(String(50))
    version = Column(String(50))
    failing_test = Column(String(500))
    stack_trace = Column(Text)
    
    # Generated patch
    patch = Column(Text, nullable=False)
    files_touched = Column(Text, nullable=False)  # JSON array as string
    rationale = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    spell = relationship("Spell", back_populates="applications")
```

**Update Spell Model**:
```python
# Add to app/models/spell.py
class Spell(Base):
    # ... existing fields ...
    
    # Relationship
    applications = relationship("SpellApplication", back_populates="spell")
```

### Pydantic Schemas

**Location**: `app/models/spell_application.py`

```python
class FailingContext(BaseModel):
    """Context about the failing code."""
    repository: str = Field(..., min_length=1, max_length=500)
    commit_sha: str = Field(..., min_length=7, max_length=40)
    language: Optional[str] = Field(None, max_length=50)
    version: Optional[str] = Field(None, max_length=50)
    failing_test: Optional[str] = Field(None, max_length=500)
    stack_trace: Optional[str] = None

class AdaptationConstraints(BaseModel):
    """Constraints for patch generation."""
    max_files: int = Field(default=3, ge=1, le=10)
    excluded_patterns: List[str] = Field(default_factory=lambda: ["package.json", "*.lock"])
    preserve_style: bool = Field(default=True)

class PatchResult(BaseModel):
    """Result of patch generation."""
    patch: str
    files_touched: List[str]
    rationale: str

class SpellApplicationRequest(BaseModel):
    """Request to apply a spell."""
    failing_context: FailingContext
    adaptation_constraints: Optional[AdaptationConstraints] = None

class SpellApplicationResponse(BaseModel):
    """Response from spell application."""
    application_id: int
    patch: str
    files_touched: List[str]
    rationale: str
    created_at: datetime

class SpellApplicationSummary(BaseModel):
    """Summary of a spell application for history."""
    id: int
    spell_id: int
    repository: str
    commit_sha: str
    files_touched: List[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Request validation completeness

*For any* spell application request, the system should validate that all required fields in the failing context (repository, commit_sha) are present and properly typed, and optional fields (language, version, failing_test, stack_trace) are validated when provided.

**Validates: Requirements 1.2, 1.3**

### Property 2: Spell retrieval consistency

*For any* valid spell ID in the database, requesting spell application should successfully retrieve the spell's incantation, and for any invalid spell ID, the system should return a 404 error.

**Validates: Requirements 1.4**

### Property 3: Prompt completeness

*For any* valid failing context, spell incantation, and adaptation constraints, the generated LLM prompt should contain all required sections: failing context (language, version, test name, stack trace, commit SHA), spell incantation, and adaptation constraints (max files, excluded patterns, style preservation).

**Validates: Requirements 2.1, 2.2, 3.1, 3.2, 3.3, 9.1, 9.2, 9.3**

### Property 4: LLM response parsing

*For any* LLM response that is valid JSON containing patch, files_touched, and rationale fields, parsing should succeed and extract all fields correctly, and for any invalid JSON or missing required fields, parsing should fail with a descriptive error.

**Validates: Requirements 2.4**

### Property 5: Constraint validation

*For any* patch result where the number of files in files_touched exceeds the max_files constraint, validation should fail, and for any patch result within the constraint, validation should succeed.

**Validates: Requirements 3.4**

### Property 6: Response structure validity

*For any* successful patch generation, the API response should contain all required fields (application_id, patch as string, files_touched as list of strings, rationale as string, created_at as datetime) with correct types.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 7: Error response structure

*For any* error during patch generation (timeout, LLM failure, validation failure), the API response should contain an error object with a descriptive message and appropriate HTTP status code.

**Validates: Requirements 4.5**

### Property 8: Patch format validation - git diff header

*For any* generated patch, it should start with a valid git diff header (matching pattern "diff --git") to ensure it's a valid unified diff format.

**Validates: Requirements 7.1**

### Property 9: Patch and metadata consistency

*For any* generated patch and files_touched list, every file path mentioned in the patch diff headers should appear in the files_touched list.

**Validates: Requirements 7.2**

### Property 10: Patch format validation - unified diff markers

*For any* generated patch, it should contain valid unified diff format markers (+++, ---, @@) to ensure it can be applied by git.

**Validates: Requirements 7.3**

### Property 11: Patch preservation

*For any* valid patch that passes format validation, the system should return it without modification to preserve exact formatting and whitespace.

**Validates: Requirements 7.5**

### Property 12: Language inference

*For any* spell incantation containing file paths with extensions, when language is not specified in failing context, the system should infer the language from the most common file extension in the incantation.

**Validates: Requirements 9.4**

### Property 13: Application record completeness

*For any* successful patch generation, the created spell application record in the database should contain all required fields: spell_id, repository, commit_sha, patch, files_touched, rationale, and created_at timestamp.

**Validates: Requirements 10.1, 10.2, 10.3, 10.4**

### Property 14: Spell response includes applications

*For any* spell retrieved by ID, the API response should include a list of associated application records (may be empty) with their metadata.

**Validates: Requirements 10.5**

### Property 15: Application history retrieval

*For any* spell with application records, fetching the spell's applications should return all records with required fields (id, spell_id, repository, commit_sha, files_touched, created_at) ordered by created_at descending.

**Validates: Requirements 11.1, 11.2, 11.3**

### Property 16: Sensitive data redaction

*For any* logged data containing API keys or authentication tokens (matching patterns like "sk-", "Bearer ", "token="), the system should redact these values before writing to logs.

**Validates: Requirements 12.4**

## Error Handling

### Error Categories

1. **Client Errors (4xx)**
   - 404 Not Found: Spell ID doesn't exist
   - 422 Unprocessable Entity: Invalid request format, patch validation failed, constraint violations
   
2. **Server Errors (5xx)**
   - 500 Internal Server Error: LLM configuration missing or invalid
   - 502 Bad Gateway: LLM API returned an error
   - 504 Gateway Timeout: LLM request exceeded timeout

### Error Response Format

All errors return a consistent JSON structure:

```json
{
  "detail": "Human-readable error message",
  "error_code": "SPELL_NOT_FOUND",
  "context": {
    "spell_id": 123,
    "additional_info": "..."
  }
}
```

### Error Handling Strategy

1. **Validation Errors**: Caught early with Pydantic validation, return 422 with field-specific errors
2. **Database Errors**: Wrapped in try-except, logged with full context, return 500
3. **LLM Errors**: Categorized by type (timeout, API error, parsing error), return appropriate 5xx status
4. **Constraint Violations**: Validated after LLM response, return 422 with specific constraint that failed

### Logging

All errors are logged with:
- Request ID for tracing
- Full request parameters (with sensitive data redacted)
- Error stack trace
- Timestamp and severity level

## Testing Strategy

### Unit Testing

Unit tests will cover:

1. **API Endpoint Tests**
   - Valid request handling
   - Invalid spell ID returns 404
   - Request validation errors return 422
   - Response structure matches schema

2. **Patch Generator Service Tests**
   - Prompt construction with various inputs
   - Constraint validation logic
   - Patch format validation
   - Language inference from file extensions

3. **Database Operations Tests**
   - Application record creation
   - Application history retrieval
   - Relationship between spells and applications
   - Ordering by timestamp

4. **LLM Service Integration Tests**
   - Mock LLM responses for success cases
   - Mock LLM errors for failure cases
   - Timeout handling
   - JSON parsing edge cases

### Property-Based Testing

The project will use **Hypothesis** for Python property-based testing. Each property-based test will run a minimum of 100 iterations.

Property-based tests will cover:

1. **Property 1: Request validation completeness**
   - Generate random failing contexts with various field combinations
   - Verify all required fields are validated
   - **Feature: spell-application, Property 1: Request validation completeness**

2. **Property 2: Spell retrieval consistency**
   - Generate random spell IDs (valid and invalid)
   - Verify correct retrieval or 404 response
   - **Feature: spell-application, Property 2: Spell retrieval consistency**

3. **Property 3: Prompt completeness**
   - Generate random contexts, spells, and constraints
   - Verify all sections appear in generated prompt
   - **Feature: spell-application, Property 3: Prompt completeness**

4. **Property 4: LLM response parsing**
   - Generate random valid and invalid JSON responses
   - Verify parsing succeeds/fails appropriately
   - **Feature: spell-application, Property 4: LLM response parsing**

5. **Property 5: Constraint validation**
   - Generate random patch results with varying file counts
   - Verify constraint enforcement
   - **Feature: spell-application, Property 5: Constraint validation**

6. **Property 6: Response structure validity**
   - Generate random successful patch results
   - Verify response contains all required fields with correct types
   - **Feature: spell-application, Property 6: Response structure validity**

7. **Property 7: Error response structure**
   - Generate random error conditions
   - Verify error responses have consistent structure
   - **Feature: spell-application, Property 7: Error response structure**

8. **Property 8: Patch format validation - git diff header**
   - Generate random patch strings
   - Verify git diff header detection
   - **Feature: spell-application, Property 8: Patch format validation - git diff header**

9. **Property 9: Patch and metadata consistency**
   - Generate random patches and file lists
   - Verify files in patch appear in metadata
   - **Feature: spell-application, Property 9: Patch and metadata consistency**

10. **Property 10: Patch format validation - unified diff markers**
    - Generate random patch strings
    - Verify unified diff marker detection
    - **Feature: spell-application, Property 10: Patch format validation - unified diff markers**

11. **Property 11: Patch preservation**
    - Generate random valid patches
    - Verify they are returned unchanged
    - **Feature: spell-application, Property 11: Patch preservation**

12. **Property 12: Language inference**
    - Generate random spell incantations with file paths
    - Verify language inference from extensions
    - **Feature: spell-application, Property 12: Language inference**

13. **Property 13: Application record completeness**
    - Generate random patch results
    - Verify database records contain all fields
    - **Feature: spell-application, Property 13: Application record completeness**

14. **Property 14: Spell response includes applications**
    - Generate random spells with/without applications
    - Verify applications list is included
    - **Feature: spell-application, Property 14: Spell response includes applications**

15. **Property 15: Application history retrieval**
    - Generate random application records
    - Verify retrieval and ordering
    - **Feature: spell-application, Property 15: Application history retrieval**

16. **Property 16: Sensitive data redaction**
    - Generate random log data with sensitive patterns
    - Verify redaction before logging
    - **Feature: spell-application, Property 16: Sensitive data redaction**

### Integration Testing

Integration tests will verify:

1. **End-to-End Flow**
   - Create spell → Apply spell → Verify application record → Retrieve history
   - Test with real database (SQLite in-memory for tests)

2. **LLM Integration**
   - Test with mock LLM service
   - Verify prompt construction and response handling
   - Test error scenarios (timeout, invalid response)

3. **Database Relationships**
   - Verify foreign key constraints
   - Test cascade behavior
   - Verify application history queries

### Test Configuration

- Minimum 100 iterations for each property-based test
- Use pytest fixtures for database setup/teardown
- Use async test client for API endpoint tests
- Mock external LLM calls to avoid API costs and ensure deterministic tests
- Use Hypothesis strategies for generating test data

## Implementation Notes

### Database Migration

A new Alembic migration will be created to add the `spell_applications` table:

```bash
alembic revision --autogenerate -m "add_spell_applications_table"
alembic upgrade head
```

### Environment Variables

New environment variables for patch generation:

```bash
# Patch generation settings
PATCH_GENERATION_TIMEOUT=30  # Seconds
PATCH_MAX_FILES_DEFAULT=3    # Default max files to modify
```

### LLM Provider Configuration

The feature will use the existing LLM Service configuration:
- `LLM_PROVIDER`: openai or anthropic
- `LLM_MODEL`: Model name (e.g., gpt-4-turbo, claude-3-opus)
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: API credentials

### Frontend Integration

The frontend will need to:

1. Add "Apply Spell (Preview)" button to spell detail page
2. Collect failing context from user (or auto-detect from CI/CD)
3. Send POST request to `/api/spells/{id}/apply`
4. Display loading state during patch generation
5. Render patch in side-by-side diff viewer
6. Display application history on spell detail page

### Performance Considerations

1. **Async Operations**: All database and LLM calls use async/await
2. **Timeout Management**: 30-second timeout for LLM calls prevents hanging requests
3. **Connection Pooling**: SQLAlchemy connection pool handles concurrent requests
4. **Caching**: Consider caching spell data for frequently applied spells (future enhancement)

### Security Considerations

1. **Input Validation**: All inputs validated with Pydantic schemas
2. **SQL Injection**: Prevented by SQLAlchemy parameterized queries
3. **API Key Protection**: Keys stored in environment variables, never logged
4. **Rate Limiting**: Consider adding rate limits for patch generation (future enhancement)
5. **Sensitive Data**: Redact API keys and tokens from logs

## Future Enhancements

1. **Patch Application**: Automatically apply patches to repositories via GitHub API
2. **Patch Testing**: Run tests in sandbox to verify patch correctness
3. **Patch Refinement**: Allow users to provide feedback and regenerate patches
4. **Batch Application**: Apply spells to multiple repositories at once
5. **Patch Templates**: Learn from successful applications to improve future generations
6. **Vector Search**: Use embeddings to find similar past applications for better context
7. **Confidence Scoring**: Add confidence scores to generated patches based on context similarity
8. **User Feedback Loop**: Track which patches are accepted/rejected to improve LLM prompts
