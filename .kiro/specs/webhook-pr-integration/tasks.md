# Implementation Plan

- [x] 1. Add PR Processor integration to webhook endpoint
  - Import PRProcessor from app.services.pr_processor
  - Check if event type is "pull_request" before processing
  - Instantiate PRProcessor in webhook handler
  - Call process_pr_event() with webhook payload
  - Store processing result in pr_processing_result variable
  - Wrap PR processor call in try-except block
  - Log errors with repo and PR number context
  - _Requirements: 1.1, 1.2, 1.3, 5.1_

- [ ]* 1.1 Write property test for PR processor integration
  - **Property 1: PR Processor integration preserves webhook success**
  - **Validates: Requirements 1.3, 5.4**

- [x] 2. Implement error payload construction helper function
  - Create _construct_error_payload() function in webhook.py
  - Accept pr_result and webhook_payload as parameters
  - Extract repo, pr_number, files_changed, and action from inputs
  - Build context string with PR metadata
  - Include first 5 changed files in context
  - Return dictionary with error_type, message, context, stack_trace fields
  - Use "PullRequestChange" as placeholder error_type
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]* 2.1 Write property test for error payload construction
  - **Property 2: Error payload construction completeness**
  - **Validates: Requirements 2.1, 2.5**

- [ ]* 2.2 Write unit tests for error payload construction
  - Test with minimal PR result (repo and pr_number only)
  - Test with full PR result including files_changed
  - Test with empty files_changed list
  - Test with large files_changed list (>5 files)
  - Verify all required fields are present and non-empty
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Add Matcher Service integration to webhook endpoint
  - Import MatcherService from app.services.matcher
  - Check if PR processing succeeded before matching
  - Call _construct_error_payload() with PR result
  - Instantiate MatcherService with database session
  - Call match_spells() with error payload
  - Store result in matched_spells variable
  - Initialize matched_spells as empty list
  - Wrap matcher call in try-except block
  - Log matcher errors without failing webhook
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 5.2_

- [ ]* 3.1 Write property test for matcher integration resilience
  - **Property 3: Matcher service integration resilience**
  - **Validates: Requirements 3.4, 3.5, 5.2**

- [x] 4. Update webhook response structure
  - Add pr_processing field to response dictionary
  - Add matched_spells field to response dictionary
  - Ensure pr_processing includes repo, pr_number, files_changed, status
  - Set pr_processing to None if not a pull_request event
  - Set matched_spells to empty list if matching fails
  - Maintain existing status, event, and action fields
  - Ensure response is always a valid dictionary
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 4.1 Write property test for response structure consistency
  - **Property 4: Response structure consistency**
  - **Validates: Requirements 4.1, 4.2, 4.3**

- [ ]* 4.2 Write unit tests for response structure
  - Test response with successful PR processing
  - Test response with failed PR processing
  - Test response with successful spell matching
  - Test response with failed spell matching
  - Test response for non-pull_request events
  - Verify all required fields are present
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 5. Add comprehensive error handling and logging
  - Wrap PR processor call in try-except with specific exception handling
  - Wrap matcher service call in try-except with specific exception handling
  - Log all exceptions with full stack trace using exc_info=True
  - Include PR metadata (repo, pr_number) in all log messages
  - Use logger.error() for exceptions
  - Use logger.info() for successful processing
  - Ensure webhook always returns HTTP 200 even on errors
  - Never log sensitive data (tokens, secrets) in error messages
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 5.1 Write property test for service failure isolation
  - **Property 5: Service failure isolation**
  - **Validates: Requirements 5.1, 5.2, 5.3**

- [ ]* 5.2 Write unit tests for error handling
  - Test PR processor raises exception (webhook returns 200)
  - Test matcher service raises exception (webhook returns 200)
  - Test error details are logged with context
  - Test matched_spells is empty on matcher failure
  - Test pr_processing.status is "error" on processor failure
  - Mock services to raise various exception types
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 6. Add integration tests for end-to-end webhook processing
  - Test complete flow: webhook → PR processor → matcher → response
  - Test with valid GitHub webhook payload
  - Test with GITHUB_API_TOKEN configured
  - Test with GITHUB_API_TOKEN not configured
  - Mock GitHub API responses for PR diff
  - Create test spells in database for matching
  - Verify response includes pr_processing and matched_spells
  - Verify spell IDs are returned in ranked order
  - _Requirements: 1.1, 1.2, 3.1, 3.2, 4.1_

- [x] 7. Update webhook endpoint documentation
  - Add docstring examples showing new response structure
  - Document pr_processing field and its structure
  - Document matched_spells field
  - Add example responses for success and error cases
  - Update module docstring to mention PR processing integration
  - Add inline comments explaining integration logic
  - _Requirements: 4.1, 4.2_

- [x] 8. Checkpoint - Ensure all tests pass
  - Run all unit tests and verify they pass
  - Run all property tests and verify they pass
  - Run integration tests and verify they pass
  - Check test coverage for new code
  - Manually test with sample webhook payload
  - Verify logs contain appropriate information
  - Ask the user if questions arise
