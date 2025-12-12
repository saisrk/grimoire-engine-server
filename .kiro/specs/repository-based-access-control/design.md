# Design Document

## Overview

The repository-based access control feature establishes a security model where spell visibility and management are restricted based on user repository ownership. This design transforms the current system from a global spell repository to a multi-tenant architecture where users can only access spells from repositories they have configured.

The implementation involves three key relationships:
1. **User → Repository**: Users own the repositories they configure
2. **Repository → Spell**: Spells are associated with specific repositories  
3. **User → Spell** (derived): Users can access spells only from their owned repositories

This design ensures data isolation between different users while maintaining the existing spell functionality within each user's repository scope.

## Architecture

### Current State
- Spells exist independently without repository association
- All users can see all spells
- Repository configurations exist but are not linked to users
- No access control on spell operations

### Target State
- Spells are linked to repositories via foreign key
- Repository configurations are owned by users
- Spell access is filtered by repository ownership
- All spell operations respect repository access control

### Migration Strategy
The migration will be implemented in phases:
1. **Schema Migration**: Add foreign key relationships
2. **Data Migration**: Associate existing data with appropriate owners
3. **API Migration**: Update endpoints to enforce access control
4. **Webhook Migration**: Update webhook processing to capture repository context

## Components and Interfaces

### Database Schema Changes

#### Repository Configuration Model Updates
```python
class RepositoryConfig(Base):
    __tablename__ = "repository_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(255), nullable=False, unique=True, index=True)
    webhook_url = Column(String(500), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # NEW
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="repositories")  # NEW
    spells = relationship("Spell", back_populates="repository")  # NEW
```

#### Spell Model Updates
```python
class Spell(Base):
    __tablename__ = "spells"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    error_type = Column(String(100), nullable=False, index=True)
    error_pattern = Column(Text, nullable=False)
    solution_code = Column(Text, nullable=False)
    tags = Column(String(500))
    repository_id = Column(Integer, ForeignKey("repository_configs.id"), nullable=False, index=True)  # NEW
    auto_generated = Column(Integer, default=0)
    confidence_score = Column(Integer, default=0)
    human_reviewed = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    repository = relationship("RepositoryConfig", back_populates="spells")  # NEW
    applications = relationship("SpellApplication", back_populates="spell")
```

#### User Model Updates
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    repositories = relationship("RepositoryConfig", back_populates="owner")  # NEW
```

### API Interface Changes

#### Spell API Updates
```python
# Updated spell schemas
class SpellCreate(SpellBase):
    repository_id: int  # NEW - Required field

class SpellResponse(SpellBase):
    id: int
    repository_id: int  # NEW
    repository: Optional[RepositoryInfo] = None  # NEW - Embedded repository info
    auto_generated: int
    confidence_score: int
    human_reviewed: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    applications: List[Any] = Field(default_factory=list)

class RepositoryInfo(BaseModel):
    id: int
    repo_name: str
    enabled: bool

# Updated endpoints with repository filtering
@router.get("", response_model=List[SpellResponse])
async def list_spells(
    skip: int = 0,
    limit: int = 100,
    repository_id: Optional[int] = None,  # NEW - Repository filter
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # NEW - Authentication required
) -> List[SpellResponse]:
    # Filter spells by user's accessible repositories
    # Apply repository_id filter if provided
```

#### Repository API Updates
```python
# All repository endpoints now require authentication
# Repository operations are scoped to the authenticated user
```

### Access Control Service

#### Repository Access Manager
```python
class RepositoryAccessManager:
    """Manages repository access control and validation."""
    
    async def get_user_repositories(self, user_id: int, db: AsyncSession) -> List[RepositoryConfig]:
        """Get all repositories owned by a user."""
        
    async def validate_repository_access(self, user_id: int, repository_id: int, db: AsyncSession) -> bool:
        """Validate if user has access to a repository."""
        
    async def filter_spells_by_access(self, user_id: int, query: Select, db: AsyncSession) -> Select:
        """Filter spell query to only include accessible spells."""
        
    async def get_repository_statistics(self, user_id: int, db: AsyncSession) -> Dict[int, RepositoryStats]:
        """Get spell statistics for user's repositories."""
```

## Data Models

### Repository Statistics Model
```python
class RepositoryStats(BaseModel):
    repository_id: int
    repository_name: str
    total_spells: int
    auto_generated_spells: int
    manual_spells: int
    spell_applications: int
    last_spell_created: Optional[datetime]
    last_application: Optional[datetime]
```

### Enhanced Spell Response Model
```python
class SpellResponseWithRepository(SpellResponse):
    repository: RepositoryInfo
    
class RepositoryInfo(BaseModel):
    id: int
    repo_name: str
    enabled: bool
    owner_id: int  # For admin purposes
```

### Search and Filter Models
```python
class SpellSearchFilters(BaseModel):
    repository_id: Optional[int] = None
    error_type: Optional[str] = None
    tags: Optional[List[str]] = None
    auto_generated: Optional[bool] = None
    human_reviewed: Optional[bool] = None
    
class SpellSearchRequest(BaseModel):
    query: Optional[str] = None
    filters: Optional[SpellSearchFilters] = None
    skip: int = 0
    limit: int = 100
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, several properties can be consolidated:
- Properties 1.1, 1.4, 5.2, and 5.5 all relate to spell-repository association and can be combined
- Properties 2.1, 2.2, 2.4, and 2.5 all relate to spell access control and can be combined  
- Properties 3.1, 3.2, 3.3, 3.4, and 3.5 all relate to repository ownership and can be combined
- Properties 4.1, 4.2, 4.3, and 4.4 all relate to repository-filtered search and can be combined
- Properties 7.1, 7.2, 7.4, and 7.5 all relate to API response format and can be combined
- Properties 9.1, 9.2, 9.3, 9.4, and 9.5 all relate to spell creation validation and can be combined
- Properties 10.1, 10.2, 10.3, and 10.5 all relate to database integrity and can be combined

Property 1: Spell-repository association integrity
*For any* spell creation or webhook processing, the created spell should be properly associated with a valid repository that the user has access to
**Validates: Requirements 1.1, 1.4, 5.2, 5.5**

Property 2: Repository-based spell access control
*For any* spell access operation (list, view, filter), users should only see spells from repositories they own, and attempts to access unauthorized spells should be rejected
**Validates: Requirements 2.1, 2.2, 2.4, 2.5**

Property 3: Repository ownership consistency
*For any* repository operation (create, list, modify, delete), only the repository owner should be able to perform the operation
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

Property 4: Repository-filtered search correctness
*For any* spell search operation, repository filters should only return spells from accessible repositories and respect user access permissions
**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

Property 5: Webhook repository context capture
*For any* webhook processing, the system should correctly extract repository information and create appropriate repository associations
**Validates: Requirements 5.1, 5.3**

Property 6: API response repository information
*For any* spell API response, the system should include accurate and current repository information
**Validates: Requirements 7.1, 7.2, 7.4, 7.5**

Property 7: Repository statistics accuracy
*For any* repository statistics request, the returned counts should accurately reflect the current state of spells and applications
**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

Property 8: Spell creation validation
*For any* spell creation or update operation, the system should validate repository existence, user access, and return appropriate responses
**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

Property 9: Database integrity constraints
*For any* database operation involving spell-repository relationships, foreign key constraints should prevent orphaned records and maintain referential integrity
**Validates: Requirements 10.1, 10.2, 10.3, 10.5**

## Error Handling

### Access Control Errors
- **403 Forbidden**: User attempts to access spell from repository they don't own
- **404 Not Found**: Repository or spell doesn't exist
- **422 Unprocessable Entity**: Invalid repository_id in spell creation

### Validation Errors
- **400 Bad Request**: Missing required repository_id in spell creation
- **409 Conflict**: Repository name already exists during creation
- **422 Unprocessable Entity**: Repository validation fails during spell operations

### Database Constraint Errors
- **500 Internal Server Error**: Foreign key constraint violations
- **409 Conflict**: Unique constraint violations

### Migration Errors
- **Data Integrity Warnings**: Orphaned spells without repository associations
- **Migration Failures**: Records that cannot be automatically associated

## Testing Strategy

### Unit Testing Approach
Unit tests will focus on:
- Individual access control validation functions
- Repository ownership verification logic
- Spell-repository association validation
- API input validation and error handling
- Database constraint enforcement

### Property-Based Testing Approach
Property-based tests will use **Hypothesis** for Python to verify universal properties across all inputs. Each property-based test will run a minimum of 100 iterations to ensure comprehensive coverage.

**Property Test Requirements:**
- Each property-based test must be tagged with a comment referencing the design document property
- Tag format: `**Feature: repository-based-access-control, Property {number}: {property_text}**`
- Tests must generate realistic data that respects system constraints
- Tests should cover edge cases like empty repositories, unauthorized access attempts, and constraint violations

**Test Data Generation:**
- Generate users with varying repository ownership patterns
- Create repositories with different spell counts and types
- Generate webhook payloads with valid and invalid repository information
- Create spell data with various repository associations
- Generate search queries with different filter combinations

**Integration Testing:**
- End-to-end API testing with authentication
- Database migration testing with existing data
- Webhook processing with repository context
- Cross-user access control verification

The dual testing approach ensures both specific examples work correctly (unit tests) and universal properties hold across all possible inputs (property tests), providing comprehensive correctness validation.