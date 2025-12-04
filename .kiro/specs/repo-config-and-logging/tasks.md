# Implementation Plan

- [x] 1. Create database models and migration
  - Create RepositoryConfig and WebhookExecutionLog SQLAlchemy models with all fields and relationships
  - Create Pydantic schemas for request/response validation
  - Create Alembic migration to add both tables with proper indexes and foreign key constraints
  - _Requirements: 1.1, 1.4, 5.1, 5.2_

- [ ]* 1.1 Write property test for repository creation persistence
  - **Property 1: Repository creation persistence**
  - **Validates: Requirements 1.1, 1.4, 1.5**

- [ ]* 1.2 Write property test for repository name format validation
  - **Property 2: Repository name format validation**
  - **Validates: Requirements 1.2**

- [x] 2. Implement repository configuration API endpoints
  - Create app/api/repo_configs.py with FastAPI router
  - Implement POST /api/repo-configs (create repository config)
  - Implement GET /api/repo-configs (list all with pagination)
  - Implement GET /api/repo-configs/{id} (get single config)
  - Implement PUT /api/repo-configs/{id} (update config)
  - Implement DELETE /api/repo-configs/{id} (delete with cascade)
  - Add computed fields: webhook_count and last_webhook_at
  - Register router in app/main.py
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 2.1, 2.2, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4_

- [ ]* 2.1 Write property test for repository uniqueness enforcement
  - **Property 3: Repository uniqueness enforcement**
  - **Validates: Requirements 1.3**

- [ ]* 2.2 Write property test for repository list ordering
  - **Property 4: Repository list ordering**
  - **Validates: Requirements 2.1**

- [ ]* 2.3 Write property test for repository update persistence
  - **Property 5: Repository update persistence**
  - **Validates: Requirements 3.1, 3.2, 3.4, 3.5**

- [ ]* 2.4 Write property test for cascade deletion
  - **Property 6: Cascade deletion**
  - **Validates: Requirements 4.1, 4.2**

- [ ]* 2.5 Write unit tests for repository config API
  - Test create with valid data
  - Test create with invalid repo name format
  - Test create duplicate returns 409
  - Test list returns all ordered by date
  - Test get by ID
  - Test get non-existent returns 404
  - Test update webhook URL and enabled status
  - Test update non-existent returns 404
  - Test delete removes config
  - Test delete non-existent returns 404
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 3.1, 3.2, 3.3, 4.1, 4.3_

- [x] 3. Implement webhook logging service
  - Create app/services/webhook_logger.py
  - Implement create_execution_log function with all parameters
  - Implement helper to find repo_config_id by repo_name
  - Implement helper to determine execution status from processing results
  - Handle JSON serialization for matched_spell_ids and pr_processing_result
  - Add comprehensive error handling with logging
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 3.1 Write property test for automatic webhook logging
  - **Property 7: Automatic webhook logging**
  - **Validates: Requirements 5.1, 5.2, 9.1, 9.2**

- [ ]* 3.2 Write property test for error capture in logs
  - **Property 8: Error capture in logs**
  - **Validates: Requirements 5.4, 9.3**

- [ ]* 3.3 Write property test for spell matching capture
  - **Property 9: Spell matching capture**
  - **Validates: Requirements 5.3, 9.2**

- [x] 4. Integrate webhook logging into webhook endpoint
  - Modify app/api/webhook.py to import webhook_logger
  - Add timer at start of webhook processing
  - Add try-catch block for logging at end of webhook processing
  - Calculate execution_duration_ms before logging
  - Call create_execution_log with all captured data
  - Ensure webhook never fails due to logging errors
  - Log any logging failures with full context
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ]* 4.1 Write property test for webhook logging resilience
  - **Property 13: Webhook logging resilience**
  - **Validates: Requirements 9.4**

- [ ]* 4.2 Write property test for execution duration capture
  - **Property 14: Execution duration capture**
  - **Validates: Requirements 9.5, 10.3**

- [ ]* 4.3 Write property test for PR metadata capture
  - **Property 15: PR metadata capture**
  - **Validates: Requirements 10.1, 10.2**

- [ ]* 4.4 Write integration tests for webhook logging
  - Test webhook creates log on success
  - Test webhook creates log on PR processing error
  - Test webhook creates log on matcher error
  - Test webhook includes matched spell IDs in log
  - Test webhook includes auto-generated spell ID in log
  - Test webhook includes execution duration in log
  - Test webhook includes PR metadata in log
  - Test webhook still succeeds if logging fails
  - Test webhook links log to repo config if exists
  - Test webhook creates log without repo config if none exists
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3_

- [ ] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement webhook logs API endpoints
  - Create app/api/webhook_logs.py with FastAPI router
  - Implement GET /api/webhook-logs (list all with filters and pagination)
  - Add query parameters: status, start_date, end_date, skip, limit
  - Implement GET /api/webhook-logs/{id} (get single log)
  - Implement GET /api/repo-configs/{id}/logs (get logs by repository)
  - Parse JSON fields (matched_spell_ids, pr_processing_result) in responses
  - Add computed fields: files_changed_count, spell_match_attempted, spell_generation_attempted
  - Register router in app/main.py
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 6.1 Write property test for repository log filtering
  - **Property 10: Repository log filtering**
  - **Validates: Requirements 6.1**

- [ ]* 6.2 Write property test for log status filtering
  - **Property 11: Log status filtering**
  - **Validates: Requirements 7.3**

- [ ]* 6.3 Write property test for log date range filtering
  - **Property 12: Log date range filtering**
  - **Validates: Requirements 7.4**

- [ ]* 6.4 Write unit tests for webhook logs API
  - Test list all logs ordered by execution time
  - Test list logs with status filter
  - Test list logs with date range filter
  - Test list logs with pagination
  - Test get logs by repository ID
  - Test get logs for repository with no logs returns empty list
  - Test get log by ID
  - Test get non-existent log returns 404
  - Test response includes all required fields
  - Test response includes computed fields
  - _Requirements: 6.1, 6.2, 6.4, 7.1, 7.3, 7.4, 7.5, 8.1, 8.3_

- [x] 7. Add authentication to new endpoints
  - Import authentication dependencies from app/api/auth.py
  - Add Depends(get_current_user) to all repository config endpoints
  - Add Depends(get_current_user) to all webhook logs endpoints
  - Ensure webhook endpoint remains unauthenticated (uses signature validation)
  - _Requirements: Security consideration from design_

- [ ]* 7.1 Write unit tests for authentication on new endpoints
  - Test repository config endpoints require authentication
  - Test webhook logs endpoints require authentication
  - Test endpoints return 401 without valid token
  - Test endpoints work with valid token
  - _Requirements: Security consideration from design_

- [ ] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Update API documentation
  - Add docstrings to all new API endpoints with examples
  - Document request/response schemas
  - Document query parameters and filters
  - Document error responses
  - _Requirements: All requirements (documentation)_
