# Implementation Plan

- [x] 1. Create database model and migration for spell applications
  - Create `SpellApplication` model in `app/models/spell_application.py` with all required fields
  - Add relationship to `Spell` model
  - Create Alembic migration for `spell_applications` table
  - Run migration to create table
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 2. Create Pydantic schemas for spell application
  - Define `FailingContext` schema with validation rules
  - Define `AdaptationConstraints` schema with defaults
  - Define `PatchResult` schema for internal use
  - Define `SpellApplicationRequest` schema for API input
  - Define `SpellApplicationResponse` schema for API output
  - Define `SpellApplicationSummary` schema for history listing
  - _Requirements: 1.2, 1.3, 4.1, 4.2, 4.3, 11.2_

- [ ]* 2.1 Write property test for request validation
  - **Property 1: Request validation completeness**
  - **Validates: Requirements 1.2, 1.3**

- [x] 3. Implement Patch Generator Service
  - [x] 3.1 Create `PatchGeneratorService` class in `app/services/patch_generator.py`
    - Initialize with LLM service dependency
    - _Requirements: 2.1_

  - [x] 3.2 Implement prompt construction method
    - Build system prompt with instructions for JSON output
    - Include failing context (language, version, test, stack trace, commit SHA)
    - Include spell incantation
    - Include adaptation constraints (max files, excluded patterns, style preservation)
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 9.1, 9.2, 9.3_

  - [ ]* 3.3 Write property test for prompt completeness
    - **Property 3: Prompt completeness**
    - **Validates: Requirements 2.1, 2.2, 3.1, 3.2, 3.3, 9.1, 9.2, 9.3**

  - [x] 3.4 Implement language inference logic
    - Extract file extensions from spell incantation
    - Map extensions to languages (py→python, js→javascript, etc.)
    - Return most common language or None
    - _Requirements: 9.4_

  - [ ]* 3.5 Write property test for language inference
    - **Property 12: Language inference**
    - **Validates: Requirements 9.4**

  - [x] 3.6 Implement patch validation method
    - Validate git diff header format
    - Validate unified diff markers (+++, ---, @@)
    - Check file paths consistency between patch and files_touched
    - Validate constraint compliance (max files)
    - _Requirements: 7.1, 7.2, 7.3, 3.4_

  - [ ]* 3.7 Write property tests for patch validation
    - **Property 8: Patch format validation - git diff header**
    - **Property 9: Patch and metadata consistency**
    - **Property 10: Patch format validation - unified diff markers**
    - **Property 5: Constraint validation**
    - **Validates: Requirements 7.1, 7.2, 7.3, 3.4**

  - [x] 3.8 Implement main patch generation method
    - Call language inference if needed
    - Build LLM prompt
    - Call LLM service
    - Parse JSON response
    - Validate patch format and constraints
    - Return PatchResult or raise appropriate error
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 7.5_

  - [ ]* 3.9 Write property tests for patch generation flow
    - **Property 4: LLM response parsing**
    - **Property 11: Patch preservation**
    - **Validates: Requirements 2.4, 7.5**

- [x] 4. Extend LLM Service for patch generation
  - Add `generate_patch` method to `LLMService` class
  - Configure 30-second timeout for patch requests
  - Handle JSON parsing and validation
  - Return structured dict with patch, files_touched, rationale
  - Handle errors (timeout, API errors, parsing failures)
  - _Requirements: 2.3, 2.4, 5.1, 5.2, 5.3, 5.4, 6.1_

- [ ]* 4.1 Write unit tests for LLM service patch generation
  - Test successful patch generation with mocked LLM
  - Test timeout handling
  - Test API error handling
  - Test invalid JSON response handling
  - _Requirements: 2.4, 5.1, 5.2, 5.3, 5.4_

- [x] 5. Implement spell application API endpoint
  - [x] 5.1 Add `apply_spell` endpoint to `app/api/spells.py`
    - Accept POST requests at `/api/spells/{spell_id}/apply`
    - Validate request with `SpellApplicationRequest` schema
    - Fetch spell from database by ID
    - Return 404 if spell not found
    - _Requirements: 1.1, 1.4, 1.5_

  - [ ]* 5.2 Write property test for spell retrieval
    - **Property 2: Spell retrieval consistency**
    - **Validates: Requirements 1.4**

  - [x] 5.3 Integrate patch generator service
    - Initialize `PatchGeneratorService` with LLM service
    - Call `generate_patch` with spell, context, and constraints
    - Handle errors and return appropriate HTTP status codes
    - _Requirements: 2.1, 4.5, 5.1, 5.2, 5.3, 5.4_

  - [ ]* 5.4 Write property test for error response structure
    - **Property 7: Error response structure**
    - **Validates: Requirements 4.5**

  - [x] 5.5 Store application record in database
    - Create `SpellApplication` record with all fields
    - Link to spell via spell_id foreign key
    - Store patch, files_touched (as JSON string), rationale
    - Store failing context fields
    - Commit to database
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 5.6 Write property test for application record storage
    - **Property 13: Application record completeness**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

  - [x] 5.7 Return structured response
    - Build `SpellApplicationResponse` with application_id, patch, files_touched, rationale, created_at
    - Return HTTP 200 with response
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 5.8 Write property test for response structure
    - **Property 6: Response structure validity**
    - **Validates: Requirements 4.1, 4.2, 4.3**

- [x] 6. Implement spell application history endpoint
  - Add `list_spell_applications` endpoint to `app/api/spells.py`
  - Accept GET requests at `/api/spells/{spell_id}/applications`
  - Query database for applications by spell_id
  - Order by created_at descending
  - Support pagination with skip and limit
  - Return list of `SpellApplicationSummary` objects
  - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ]* 6.1 Write property test for application history retrieval
  - **Property 15: Application history retrieval**
  - **Validates: Requirements 11.1, 11.2, 11.3**

- [x] 7. Update spell detail endpoint to include applications
  - Modify `get_spell` endpoint in `app/api/spells.py`
  - Use `selectinload` to eagerly load applications relationship
  - Include applications list in spell response
  - _Requirements: 10.5_

- [ ]* 7.1 Write property test for spell response with applications
  - **Property 14: Spell response includes applications**
  - **Validates: Requirements 10.5**

- [x] 8. Implement logging with sensitive data redaction
  - Create utility function for redacting sensitive patterns
  - Redact API keys (patterns: "sk-", "Bearer ", "token=")
  - Apply redaction to all log statements in patch generation flow
  - Log request parameters, LLM responses, and errors
  - Use structured logging with consistent field names
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ]* 8.1 Write property test for sensitive data redaction
  - **Property 16: Sensitive data redaction**
  - **Validates: Requirements 12.4**

- [x] 9. Add environment variable configuration
  - Add `PATCH_GENERATION_TIMEOUT` to `.env.example` with default 30
  - Add `PATCH_MAX_FILES_DEFAULT` to `.env.example` with default 3
  - Document new environment variables in README
  - _Requirements: 6.1_

- [x] 10. Update API documentation
  - Add docstrings to new endpoints with parameter descriptions
  - Add example request/response payloads in docstrings
  - Document all HTTP status codes and error responses
  - Verify endpoints appear in `/docs` with complete schemas
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Run all unit tests
  - Run all property-based tests
  - Verify test coverage for new code
  - Fix any failing tests
  - Ask user if questions arise

- [ ]* 12. Write integration tests for end-to-end flow
  - Test complete flow: create spell → apply spell → verify record → retrieve history
  - Test with in-memory SQLite database
  - Mock LLM service responses
  - Verify database relationships and constraints
  - Test error scenarios (spell not found, LLM timeout, invalid patch)
  - _Requirements: All_

- [ ] 13. Final checkpoint - Ensure all tests pass
  - Run full test suite
  - Verify all property-based tests pass with 100+ iterations
  - Check test coverage meets requirements
  - Ask user if questions arise
