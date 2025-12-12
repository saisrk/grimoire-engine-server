# Implementation Plan

- [x] 1. Create database migration for repository-based access control
  - Create Alembic migration to add user_id foreign key to repository_configs table
  - Create Alembic migration to add repository_id foreign key to spells table
  - Add appropriate indexes for the new foreign key columns
  - Define cascade behavior for foreign key constraints
  - _Requirements: 3.2, 1.4, 10.1_

- [ ]* 1.1 Write property test for database constraints
  - **Property 9: Database integrity constraints**
  - **Validates: Requirements 10.1, 10.2, 10.3, 10.5**

- [x] 2. Update data models with repository relationships
  - [x] 2.1 Update RepositoryConfig model to include user_id foreign key and relationships
    - Add user_id column with foreign key to users table
    - Add owner relationship to User model
    - Add spells relationship to Spell model
    - _Requirements: 3.1, 3.2_

  - [x] 2.2 Update Spell model to include repository_id foreign key and relationships
    - Add repository_id column with foreign key to repository_configs table
    - Add repository relationship to RepositoryConfig model
    - Update existing relationships to work with new schema
    - _Requirements: 1.4, 1.1_

  - [x] 2.3 Update User model to include repository relationships
    - Add repositories relationship to RepositoryConfig model
    - Update model to support repository ownership queries
    - _Requirements: 3.1_

  - [ ]* 2.4 Write property test for model relationships
    - **Property 1: Spell-repository association integrity**
    - **Validates: Requirements 1.1, 1.4, 5.2, 5.5**

- [x] 3. Create repository access control service
  - [x] 3.1 Implement RepositoryAccessManager class
    - Create get_user_repositories method to fetch user's repositories
    - Create validate_repository_access method for access validation
    - Create filter_spells_by_access method for query filtering
    - Create get_repository_statistics method for repository stats
    - _Requirements: 2.1, 3.3, 8.1_

  - [ ]* 3.2 Write property test for repository access control
    - **Property 2: Repository-based spell access control**
    - **Validates: Requirements 2.1, 2.2, 2.4, 2.5**

  - [ ]* 3.3 Write property test for repository ownership
    - **Property 3: Repository ownership consistency**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

- [x] 4. Update repository configuration API with user ownership
  - [x] 4.1 Add authentication requirements to all repository endpoints
    - Add current_user dependency to all repository endpoints
    - Update create endpoint to associate repository with authenticated user
    - Update list endpoint to filter by user ownership
    - Update get/update/delete endpoints to verify user ownership
    - _Requirements: 3.1, 3.3, 3.4, 3.5_

  - [x] 4.2 Update repository response schemas to include ownership information
    - Add user_id field to repository response models
    - Include spell statistics in repository responses
    - Update repository creation to return ownership confirmation
    - _Requirements: 8.2, 3.1_

  - [ ]* 4.3 Write unit tests for repository API access control
    - Test repository creation with user association
    - Test repository listing filtered by user
    - Test repository modification access control
    - Test repository deletion access control
    - _Requirements: 3.1, 3.3, 3.4, 3.5_

- [x] 5. Update spell API with repository-based access control
  - [x] 5.1 Add repository_id requirement to spell creation and updates
    - Update SpellCreate schema to require repository_id ✓
    - Update SpellUpdate schema to include repository_id validation ✓
    - Add repository existence and access validation ✓
    - _Requirements: 1.2, 9.1, 9.2_

  - [x] 5.2 Implement spell access filtering in list and get endpoints
    - Add authentication requirement to spell endpoints ✓
    - Filter spell queries by user's accessible repositories ✓
    - Add repository_id query parameter for filtering ✓
    - Update spell responses to include repository information ✓
    - _Requirements: 2.1, 4.1, 7.1_

  - [x] 5.3 Add repository search and filtering capabilities
    - Implement repository-based spell search ✓
    - Add support for combining repository filters with other criteria ✓
    - Validate repository access in search operations ✓
    - Handle invalid repository ID errors appropriately ✓
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

  - [ ]* 5.4 Write property test for spell access control
    - **Property 2: Repository-based spell access control**
    - **Validates: Requirements 2.1, 2.2, 2.4, 2.5**

  - [ ]* 5.5 Write property test for repository-filtered search
    - **Property 4: Repository-filtered search correctness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

  - [ ]* 5.6 Write property test for spell creation validation
    - **Property 8: Spell creation validation**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

- [x] 6. Update webhook processing to capture repository context
  - [x] 6.1 Modify webhook endpoint to extract repository information
    - Update webhook payload parsing to extract repository details ✓
    - Add repository lookup or auto-creation logic ✓
    - Associate webhook processing with repository context ✓
    - _Requirements: 5.1, 5.3_

  - [x] 6.2 Update spell generation from webhooks to include repository association
    - Modify spell creation in webhook processing to include repository_id ✓
    - Ensure generated spells are properly linked to webhook repository ✓
    - Handle cases where repository configuration doesn't exist ✓
    - _Requirements: 1.1, 5.2, 5.5_

  - [ ]* 6.3 Write property test for webhook repository context
    - **Property 5: Webhook repository context capture**
    - **Validates: Requirements 5.1, 5.3**

- [x] 7. Implement repository statistics and enhanced API responses
  - [x] 7.1 Add repository statistics calculation
    - Implement spell count calculation per repository ✓
    - Add differentiation between auto-generated and manual spells ✓
    - Include spell application counts per repository ✓
    - Handle repositories with zero spells appropriately ✓
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 7.2 Update API responses to include repository information
    - Enhance spell responses with repository details ✓
    - Ensure repository information is current and accurate ✓
    - Handle cases where repository information is unavailable ✓
    - Add repository confirmation in spell creation responses ✓
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 9.4_

  - [ ]* 7.3 Write property test for repository statistics
    - **Property 7: Repository statistics accuracy**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

  - [ ]* 7.4 Write property test for API response repository information
    - **Property 6: API response repository information**
    - **Validates: Requirements 7.1, 7.2, 7.4, 7.5**

- [x] 8. Create data migration script for existing records
  - [x] 8.1 Create migration script to associate existing repositories with users
    - Identify existing repository configurations ✓
    - Create default user associations for orphaned repositories ✓
    - Handle repositories that cannot be automatically associated ✓
    - Log migration results and any failures ✓
    - _Requirements: 6.1, 6.3, 6.5_

  - [x] 8.2 Create migration script to associate existing spells with repositories
    - Identify existing spells without repository associations ✓
    - Create default repository for unassigned spells ✓
    - Associate spells with appropriate repositories where possible ✓
    - Handle spells that cannot be automatically associated ✓
    - _Requirements: 6.1, 6.2, 6.4, 6.5_

  - [ ]* 8.3 Write unit tests for migration scripts
    - Test repository-user association migration
    - Test spell-repository association migration
    - Test handling of orphaned records
    - Test migration error handling and logging
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Update error handling and validation
  - [x] 10.1 Implement comprehensive access control error handling
    - Add 403 Forbidden responses for unauthorized repository access
    - Add 404 Not Found responses for non-existent repositories/spells
    - Add 422 Unprocessable Entity for validation failures
    - Ensure clear error messages for all access control scenarios
    - _Requirements: 2.4, 4.5, 9.3, 10.5_

  - [x] 10.2 Add database constraint violation handling
    - Handle foreign key constraint violations gracefully
    - Provide appropriate error responses for constraint failures
    - Ensure referential integrity is maintained
    - Add logging for constraint violation attempts
    - _Requirements: 10.1, 10.3, 10.5_

  - [ ]* 10.3 Write unit tests for error handling
    - Test access control error responses
    - Test validation error handling
    - Test database constraint error handling
    - Test error message clarity and appropriateness
    - _Requirements: 2.4, 4.5, 9.3, 10.5_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.