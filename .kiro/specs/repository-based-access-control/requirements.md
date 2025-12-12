# Requirements Document

## Introduction

This specification covers the implementation of repository-based access control for spells in the Grimoire Engine Backend. Currently, spells exist independently without any association to repositories or users, which means all users can see all spells regardless of their repository access. This feature will establish proper relationships between users, repositories, and spells, ensuring that users only see spells from repositories they have configured and have access to.

## Glossary

- **Repository-Based Access Control**: A security model where spell visibility is restricted based on user's repository access permissions
- **Repository Owner**: The user who configured a repository in the system and has full access to its spells
- **Spell Repository Association**: The linkage between a spell and the repository it was generated from or applies to
- **Repository Access**: The permission for a user to view and manage spells associated with a specific repository
- **Spell Visibility**: The set of spells that a user can see based on their repository access permissions
- **Repository Search**: The ability to filter spells by repository to find repository-specific solutions
- **Webhook Repository Context**: The repository information captured when processing webhook events for spell generation

## Requirements

### Requirement 1

**User Story:** As a repository owner, I want spells to be associated with the repositories I've configured, so that spells are organized by repository context.

#### Acceptance Criteria

1. WHEN a spell is created through webhook processing, THEN the system SHALL associate the spell with the repository that triggered the webhook
2. WHEN a spell is created manually, THEN the system SHALL require the user to specify which repository the spell belongs to
3. WHEN storing a spell, THEN the system SHALL validate that the specified repository exists and the user has access to it
4. WHEN a spell is associated with a repository, THEN the system SHALL store the repository_id as a foreign key in the spell record
5. WHEN retrieving spell details, THEN the system SHALL include the associated repository information in the response

### Requirement 2

**User Story:** As a repository owner, I want to be the only user who can see spells from my configured repositories, so that repository-specific solutions remain private to authorized users.

#### Acceptance Criteria

1. WHEN a user requests a list of spells, THEN the system SHALL only return spells from repositories that the user has configured
2. WHEN a user attempts to view a specific spell, THEN the system SHALL verify the user has access to the spell's associated repository
3. WHEN a user has not configured any repositories, THEN the system SHALL return an empty spell list
4. WHEN a user tries to access a spell from a repository they don't own, THEN the system SHALL return a 403 forbidden error
5. WHEN filtering spells, THEN the system SHALL apply repository access control to all filter operations

### Requirement 3

**User Story:** As a repository owner, I want repositories to be linked to my user account, so that the system knows which repositories I have access to.

#### Acceptance Criteria

1. WHEN a repository configuration is created, THEN the system SHALL associate it with the authenticated user who created it
2. WHEN storing a repository configuration, THEN the system SHALL record the user_id as a foreign key in the repository record
3. WHEN a user requests their repository list, THEN the system SHALL only return repositories they have configured
4. WHEN a user attempts to modify a repository configuration, THEN the system SHALL verify the user owns that repository
5. WHEN a repository is deleted, THEN the system SHALL only allow the repository owner to perform the deletion

### Requirement 4

**User Story:** As a developer, I want to search for spells within a specific repository, so that I can find repository-specific solutions quickly.

#### Acceptance Criteria

1. WHEN a user searches spells with a repository filter, THEN the system SHALL return only spells associated with the specified repository
2. WHEN searching by repository, THEN the system SHALL verify the user has access to the specified repository before returning results
3. WHEN a repository search is performed, THEN the system SHALL support combining repository filters with other search criteria
4. WHEN no repository filter is specified, THEN the system SHALL return spells from all repositories the user has access to
5. WHEN searching with an invalid repository ID, THEN the system SHALL return an appropriate error message

### Requirement 5

**User Story:** As a webhook processor, I want to capture repository context when processing pull requests, so that generated spells are properly associated with their source repository.

#### Acceptance Criteria

1. WHEN processing a webhook event, THEN the system SHALL extract the repository information from the webhook payload
2. WHEN generating a spell from webhook processing, THEN the system SHALL associate the spell with the repository from the webhook
3. WHEN a webhook is received for an unconfigured repository, THEN the system SHALL create the repository configuration automatically
4. WHEN auto-creating a repository configuration, THEN the system SHALL associate it with a default system user or require authentication
5. WHEN webhook processing creates a spell, THEN the system SHALL ensure the spell is linked to the correct repository

### Requirement 6

**User Story:** As a system administrator, I want existing spells to be migrated to the new repository-based model, so that current data remains accessible after the access control implementation.

#### Acceptance Criteria

1. WHEN migrating existing spells, THEN the system SHALL provide a mechanism to associate orphaned spells with repositories
2. WHEN no repository association can be determined, THEN the system SHALL assign spells to a default "unassigned" repository
3. WHEN migrating repository configurations, THEN the system SHALL associate existing repositories with their appropriate users
4. WHEN migration is complete, THEN the system SHALL ensure all spells have valid repository associations
5. WHEN migration fails for specific records, THEN the system SHALL log the failures and continue processing remaining records

### Requirement 7

**User Story:** As an API client, I want spell endpoints to include repository information, so that I can understand the repository context of each spell.

#### Acceptance Criteria

1. WHEN returning spell data, THEN the system SHALL include repository name and ID in the response
2. WHEN listing spells, THEN the system SHALL provide repository information for each spell in the list
3. WHEN creating or updating spells, THEN the system SHALL accept repository_id as a required field
4. WHEN spell API responses include repository data, THEN the system SHALL ensure the repository information is current and accurate
5. WHEN repository information is not available, THEN the system SHALL handle the case gracefully with appropriate null values

### Requirement 8

**User Story:** As a repository owner, I want to see spell statistics per repository, so that I can understand spell usage and effectiveness within each repository context.

#### Acceptance Criteria

1. WHEN requesting repository statistics, THEN the system SHALL return spell counts for each repository the user owns
2. WHEN displaying repository information, THEN the system SHALL include the number of associated spells
3. WHEN calculating spell statistics, THEN the system SHALL differentiate between auto-generated and manually created spells
4. WHEN repository statistics are requested, THEN the system SHALL include spell application counts per repository
5. WHEN no spells exist for a repository, THEN the system SHALL return zero counts rather than omitting the repository

### Requirement 9

**User Story:** As a developer, I want spell creation to validate repository access, so that spells can only be created for repositories I have permission to access.

#### Acceptance Criteria

1. WHEN creating a spell via API, THEN the system SHALL validate that the specified repository_id exists
2. WHEN creating a spell, THEN the system SHALL verify the authenticated user owns the specified repository
3. WHEN repository validation fails, THEN the system SHALL return a clear error message indicating the access issue
4. WHEN a spell is created successfully, THEN the system SHALL confirm the repository association in the response
5. WHEN updating a spell's repository association, THEN the system SHALL re-validate repository access permissions

### Requirement 10

**User Story:** As a system designer, I want proper database constraints for repository-spell relationships, so that data integrity is maintained at the database level.

#### Acceptance Criteria

1. WHEN defining the spell-repository relationship, THEN the system SHALL implement foreign key constraints to ensure referential integrity
2. WHEN a repository is deleted, THEN the system SHALL handle associated spells according to a defined cascade policy
3. WHEN spell records reference repositories, THEN the system SHALL prevent orphaned spell records through database constraints
4. WHEN repository ownership changes, THEN the system SHALL maintain data consistency for associated spells
5. WHEN database constraints are violated, THEN the system SHALL return appropriate error messages to the API client