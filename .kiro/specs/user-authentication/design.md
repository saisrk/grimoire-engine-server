# User Authentication Design Document

## Overview

This design document outlines the implementation of a JWT-based authentication system for the Grimoire Engine Backend. The system will provide secure user registration, login, and logout functionality using FastAPI's security utilities, SQLAlchemy for data persistence, and industry-standard cryptographic libraries.

The authentication system follows a stateless JWT approach where:
- Users register with email/password credentials
- Passwords are hashed using bcrypt before storage
- Successful authentication returns a JWT access token
- Protected endpoints validate JWT tokens via dependency injection
- Logout is handled by client-side token removal (with optional server-side token blacklisting)

## Architecture

### High-Level Components

```
┌─────────────────┐
│   API Routes    │  (auth.py)
│  /auth/signup   │
│  /auth/login    │
│  /auth/logout   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Auth Service   │  (auth_service.py)
│  - Registration │
│  - Login        │
│  - Token Gen    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   User Model    │  (user.py)
│  - SQLAlchemy   │
│  - Pydantic     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Database     │  (PostgreSQL/SQLite)
│   users table   │
└─────────────────┘
```

### Authentication Flow

**Registration Flow:**
```
Client → POST /auth/signup → Validate Input → Hash Password → Create User → Generate JWT → Return Token + User
```

**Login Flow:**
```
Client → POST /auth/login → Validate Credentials → Verify Password → Generate JWT → Return Token + User
```

**Protected Endpoint Flow:**
```
Client → GET /protected → Extract Bearer Token → Validate JWT → Decode User ID → Execute Handler
```

## Components and Interfaces

### 1. User Model (`app/models/user.py`)

**SQLAlchemy Model:**
```python
class User(Base):
    __tablename__ = "users"
    
    id: int (primary key)
    email: str (unique, indexed)
    hashed_password: str
    is_active: bool (default: True)
    created_at: datetime
    updated_at: datetime
```

**Pydantic Schemas:**
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str (min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: int | None = None
```

### 2. Authentication Service (`app/services/auth_service.py`)

**Password Hashing:**
```python
def hash_password(password: str) -> str
def verify_password(plain_password: str, hashed_password: str) -> bool
```

**JWT Token Management:**
```python
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str
def decode_access_token(token: str) -> TokenData
```

**User Operations:**
```python
async def create_user(db: AsyncSession, user_data: UserCreate) -> User
async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None
async def get_user_by_email(db: AsyncSession, email: str) -> User | None
async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None
```

### 3. Authentication Dependencies (`app/api/deps.py`)

**Dependency Functions:**
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User
```

This dependency will be used to protect endpoints:
```python
@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"user": current_user.email}
```

### 4. Authentication Routes (`app/api/auth.py`)

**Endpoints:**
- `POST /auth/signup` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout (optional server-side handling)
- `GET /auth/me` - Get current user info (protected)

## Data Models

### Users Table Schema

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
);
```

### Token Blacklist Table (Optional Enhancement)

For server-side logout tracking:
```sql
CREATE TABLE token_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_jti VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token_jti (token_jti),
    INDEX idx_expires_at (expires_at)
);
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Acceptance Criteria Testing Prework

1.1 WHEN a user submits valid registration data (email and password) THEN the Authentication System SHALL create a new user account with a hashed password
Thoughts: This is a rule that should apply to all valid registration attempts. We can generate random valid email/password combinations, register users, and verify that: (a) a user record is created, (b) the password is hashed (not stored in plain text), and (c) the hash is different from the original password.
Testable: yes - property

1.2 WHEN a user attempts to register with an email that already exists THEN the Authentication System SHALL reject the registration and return an error indicating the email is already in use
Thoughts: This is testing duplicate email handling across all possible emails. We can create a user with a random email, then attempt to register again with the same email and verify rejection.
Testable: yes - property

1.3 WHEN a user submits a password shorter than 8 characters THEN the Authentication System SHALL reject the registration and return a validation error
Thoughts: This is testing input validation for a specific constraint. We can generate random passwords with length < 8 and verify all are rejected.
Testable: yes - property

1.4 WHEN a user submits an invalid email format THEN the Authentication System SHALL reject the registration and return a validation error
Thoughts: This is testing email validation across various invalid formats. We can generate random invalid email strings and verify all are rejected.
Testable: yes - property

1.5 WHEN a user successfully registers THEN the Authentication System SHALL return the user information and an access token
Thoughts: This is testing the response structure for successful registration. We can generate random valid registrations and verify the response contains both user info and a valid JWT token.
Testable: yes - property

2.1 WHEN a user submits valid login credentials (email and password) THEN the Authentication System SHALL verify the credentials and return an access token
Thoughts: This is a round-trip property. For any user we create, we should be able to log in with their credentials and receive a valid token.
Testable: yes - property

2.2 WHEN a user submits an incorrect password THEN the Authentication System SHALL reject the login attempt and return an authentication error
Thoughts: This tests authentication failure across all users. We can create a user with a known password, then attempt login with a different password and verify rejection.
Testable: yes - property

2.3 WHEN a user submits an email that does not exist THEN the Authentication System SHALL reject the login attempt and return an authentication error
Thoughts: This tests handling of non-existent users. We can generate random emails that haven't been registered and verify all login attempts fail.
Testable: yes - property

2.4 WHEN a user successfully logs in THEN the Authentication System SHALL generate a JWT access token with the user ID and expiration time
Thoughts: This tests token structure. For any successful login, we should be able to decode the JWT and verify it contains the correct user ID and has an expiration time.
Testable: yes - property

2.5 WHEN a user successfully logs in THEN the Authentication System SHALL return both an access token and user information
Thoughts: This tests response completeness. For any successful login, the response should contain both a valid token and user information.
Testable: yes - property

3.1 WHEN an authenticated user requests to log out THEN the Authentication System SHALL invalidate the current access token
Thoughts: This depends on the logout implementation strategy. With client-side token removal, this is not testable server-side. With token blacklisting, we can test that a token works before logout and fails after logout.
Testable: yes - property (if implementing token blacklist)

3.2 WHEN a user logs out THEN the Authentication System SHALL return a success confirmation
Thoughts: This is testing the logout endpoint response. For any authenticated user, calling logout should return a success status.
Testable: yes - example

3.3 WHEN a user attempts to use an invalidated token after logout THEN the Authentication System SHALL reject the request with an authentication error
Thoughts: This tests token invalidation. If we implement token blacklisting, we can verify that tokens are rejected after logout.
Testable: yes - property (if implementing token blacklist)

4.1 WHEN a user password is stored THEN the Authentication System SHALL hash the password using bcrypt with a minimum cost factor of 12
Thoughts: This tests password hashing configuration. For any password, we can verify the resulting hash uses bcrypt and has the correct cost factor.
Testable: yes - property

4.2 WHEN verifying a password THEN the Authentication System SHALL compare the provided password against the stored hash using constant-time comparison
Thoughts: Constant-time comparison is a security property that's difficult to test directly without timing analysis. We can verify that verification works correctly, but timing guarantees are implementation-dependent.
Testable: no

4.3 THE Authentication System SHALL NOT store passwords in plain text at any time
Thoughts: This is an invariant. For any user in the database, the stored password should be a hash, not the original password.
Testable: yes - property

4.4 WHEN a password is hashed THEN the Authentication System SHALL generate a unique salt for each password
Thoughts: This tests that bcrypt generates unique hashes. For the same password hashed multiple times, the resulting hashes should be different (due to unique salts).
Testable: yes - property

5.1 WHEN generating an access token THEN the Authentication System SHALL create a JWT containing the user ID, issued-at time, and expiration time
Thoughts: This tests token structure. For any generated token, we can decode it and verify it contains the required claims.
Testable: yes - property

5.2 WHEN an access token is created THEN the Authentication System SHALL sign the token with a secure secret key
Thoughts: This tests token signing. For any token, we should be able to verify the signature using the secret key.
Testable: yes - property

5.3 WHEN validating an access token THEN the Authentication System SHALL verify the signature and check the expiration time
Thoughts: This tests token validation logic. We can generate tokens with various expiration times and verify that expired tokens are rejected.
Testable: yes - property

5.4 WHEN an expired token is presented THEN the Authentication System SHALL reject the request with an authentication error
Thoughts: This is an edge case of token validation. We can create an expired token and verify it's rejected.
Testable: edge-case

5.5 THE Authentication System SHALL set access token expiration to 24 hours from issuance
Thoughts: This tests token expiration configuration. For any generated token, the expiration time should be 24 hours from the issued-at time.
Testable: yes - property

6.1 WHEN a request to a protected endpoint includes a valid Bearer Token THEN the Authentication System SHALL extract and validate the token
Thoughts: This tests the authentication dependency. For any valid token, accessing a protected endpoint should succeed and provide user information.
Testable: yes - property

6.2 WHEN a request to a protected endpoint lacks an Authorization header THEN the Authentication System SHALL reject the request with an authentication error
Thoughts: This is an edge case testing missing authentication.
Testable: edge-case

6.3 WHEN a request includes an invalid or malformed token THEN the Authentication System SHALL reject the request with an authentication error
Thoughts: This tests error handling for invalid tokens. We can generate various malformed tokens and verify all are rejected.
Testable: yes - property

6.4 WHEN a valid token is verified THEN the Authentication System SHALL make the user information available to the endpoint handler
Thoughts: This tests the dependency injection mechanism. For any valid token, the current_user dependency should provide the correct user object.
Testable: yes - property

6.5 THE Authentication System SHALL support the standard Bearer token authentication scheme
Thoughts: This is testing HTTP authentication scheme compliance. We can verify that tokens are accepted in the "Bearer <token>" format.
Testable: yes - example

7.1 WHEN a new user is created THEN the Authentication System SHALL assign a unique integer ID to the user
Thoughts: This is an invariant maintained by the database. For any created user, they should have a unique ID.
Testable: yes - property

7.2 WHEN storing user data THEN the Authentication System SHALL enforce email uniqueness at the database level
Thoughts: This is already covered by 1.2 (duplicate email rejection).
Testable: redundant with 1.2

7.3 WHEN querying users THEN the Authentication System SHALL support lookup by both user ID and email address
Thoughts: This tests query functionality. For any created user, we should be able to retrieve them by either ID or email.
Testable: yes - property

7.4 THE Authentication System SHALL maintain created_at and updated_at timestamps for each user account
Thoughts: This is an invariant. For any user, these timestamps should exist and be valid.
Testable: yes - property

### Property Reflection

After reviewing all properties, the following redundancies were identified:

- **Property 7.2 is redundant with Property 1.2**: Both test email uniqueness enforcement. Property 1.2 already validates that duplicate emails are rejected, which implies database-level uniqueness. We'll remove 7.2.

- **Properties 1.5 and 2.5 can be combined**: Both test that successful authentication returns user info and token. We can create a single property that validates the response structure for both signup and login.

- **Properties 5.1 and 5.2 can be combined**: Both test token structure and signing. We can validate both aspects in a single property that checks token generation produces valid, signed JWTs with required claims.

### Correctness Properties

**Property 1: Registration creates hashed password**
*For any* valid email and password combination, when a user registers, the system should create a user record where the stored password is a bcrypt hash that differs from the plain text password.
**Validates: Requirements 1.1, 4.1, 4.3**

**Property 2: Duplicate email rejection**
*For any* email address, if a user is already registered with that email, attempting to register again with the same email should be rejected with an appropriate error.
**Validates: Requirements 1.2**

**Property 3: Password length validation**
*For any* password string with length less than 8 characters, registration attempts should be rejected with a validation error.
**Validates: Requirements 1.3**

**Property 4: Email format validation**
*For any* string that does not match valid email format, registration attempts should be rejected with a validation error.
**Validates: Requirements 1.4**

**Property 5: Authentication response completeness**
*For any* successful authentication (signup or login), the response should contain both a valid JWT access token and complete user information (id, email, is_active, created_at).
**Validates: Requirements 1.5, 2.5**

**Property 6: Login round-trip**
*For any* user that has been successfully registered, logging in with the same credentials should succeed and return a valid access token.
**Validates: Requirements 2.1**

**Property 7: Invalid password rejection**
*For any* registered user, attempting to login with an incorrect password should be rejected with an authentication error.
**Validates: Requirements 2.2**

**Property 8: Non-existent user rejection**
*For any* email address that has not been registered, login attempts should be rejected with an authentication error.
**Validates: Requirements 2.3**

**Property 9: JWT token structure**
*For any* successful login, the generated JWT token should be validly signed and contain the user ID, issued-at time, and expiration time.
**Validates: Requirements 2.4, 5.1, 5.2**

**Property 10: Unique password hashes**
*For any* password string, hashing it multiple times should produce different hash values due to unique salts.
**Validates: Requirements 4.4**

**Property 11: Token expiration validation**
*For any* access token, if the token has expired, requests using that token should be rejected with an authentication error.
**Validates: Requirements 5.3, 5.4**

**Property 12: Token expiration time**
*For any* generated access token, the expiration time should be exactly 24 hours from the issued-at time.
**Validates: Requirements 5.5**

**Property 13: Protected endpoint authentication**
*For any* valid access token, requests to protected endpoints with that token should succeed and provide the correct user information to the handler.
**Validates: Requirements 6.1, 6.4**

**Property 14: Invalid token rejection**
*For any* malformed or invalid JWT string, requests using that token should be rejected with an authentication error.
**Validates: Requirements 6.3**

**Property 15: User ID uniqueness**
*For any* set of created users, all user IDs should be unique integers.
**Validates: Requirements 7.1**

**Property 16: User lookup consistency**
*For any* created user, retrieving the user by ID or by email should return the same user record.
**Validates: Requirements 7.3**

**Property 17: Timestamp presence**
*For any* created user, the user record should have valid created_at and updated_at timestamps.
**Validates: Requirements 7.4**

## Error Handling

### Error Types and HTTP Status Codes

1. **Validation Errors (422 Unprocessable Entity)**
   - Invalid email format
   - Password too short
   - Missing required fields

2. **Authentication Errors (401 Unauthorized)**
   - Invalid credentials
   - Expired token
   - Malformed token
   - Missing Authorization header

3. **Conflict Errors (409 Conflict)**
   - Email already registered

4. **Server Errors (500 Internal Server Error)**
   - Database connection failures
   - Unexpected exceptions

### Error Response Format

All errors will follow FastAPI's standard error response format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

For validation errors, FastAPI automatically provides detailed field-level errors:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

## Testing Strategy

### Unit Testing

Unit tests will cover specific examples and edge cases:

1. **Password Hashing Tests**
   - Test that bcrypt hashing works correctly
   - Test that password verification works for correct passwords
   - Test that password verification fails for incorrect passwords

2. **JWT Token Tests**
   - Test token generation with specific user data
   - Test token decoding with valid tokens
   - Test token validation with expired tokens
   - Test token validation with invalid signatures

3. **API Endpoint Tests**
   - Test signup with valid data returns 201
   - Test signup with duplicate email returns 409
   - Test login with valid credentials returns 200
   - Test login with invalid credentials returns 401
   - Test protected endpoint without token returns 401
   - Test protected endpoint with valid token returns 200

### Property-Based Testing

Property-based tests will verify universal properties across all inputs using the Hypothesis library:

**Configuration:**
- Each property test will run a minimum of 100 iterations
- Tests will use Hypothesis strategies to generate random valid and invalid inputs
- Each test will be tagged with a comment referencing the specific correctness property from this design document

**Test Tagging Format:**
```python
# Feature: user-authentication, Property 1: Registration creates hashed password
@given(email=emails(), password=text(min_size=8, max_size=100))
def test_registration_creates_hashed_password(email, password):
    ...
```

**Property Test Coverage:**
1. Password hashing properties (Properties 1, 10)
2. Registration validation properties (Properties 2, 3, 4)
3. Authentication response properties (Property 5)
4. Login authentication properties (Properties 6, 7, 8)
5. JWT token properties (Properties 9, 11, 12)
6. Protected endpoint properties (Properties 13, 14)
7. User data properties (Properties 15, 16, 17)

**Key Testing Principles:**
- Unit tests catch specific bugs and verify concrete examples
- Property tests verify general correctness across all inputs
- Together they provide comprehensive coverage
- Property tests will use realistic data generators (valid emails, passwords, etc.)
- Tests will clean up database state between runs to ensure independence

## Security Considerations

1. **Password Security**
   - Bcrypt with cost factor 12 (adjustable for future security needs)
   - Automatic salting per password
   - No plain text password storage

2. **JWT Security**
   - Secret key stored in environment variables
   - Token expiration enforced
   - Signature verification on every request

3. **API Security**
   - HTTPS required in production
   - CORS properly configured
   - Rate limiting (future enhancement)

4. **Database Security**
   - Parameterized queries (SQLAlchemy ORM)
   - Email uniqueness enforced at DB level
   - Connection pooling for performance

## Dependencies

New dependencies to add to `requirements.txt`:

```
# Authentication
python-jose[cryptography]==3.3.0  # JWT token handling
passlib[bcrypt]==1.7.4            # Password hashing
python-multipart==0.0.6           # Form data parsing (already present)
```

## Configuration

Environment variables to add to `.env`:

```
# JWT Configuration
SECRET_KEY=<generate-secure-random-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
```

## Migration Strategy

1. Create Alembic migration for users table
2. Add authentication dependencies and service
3. Implement authentication routes
4. Update existing protected endpoints to use authentication
5. Add comprehensive tests

## Future Enhancements

1. **Refresh Tokens**: Implement refresh token mechanism for extended sessions
2. **Token Blacklist**: Server-side token invalidation for logout
3. **Email Verification**: Require email verification before account activation
4. **Password Reset**: Forgot password flow with email-based reset
5. **OAuth Integration**: Social login (Google, GitHub, etc.)
6. **Multi-Factor Authentication**: TOTP-based 2FA
7. **Rate Limiting**: Prevent brute force attacks on login endpoint
8. **Account Lockout**: Temporary lockout after failed login attempts
