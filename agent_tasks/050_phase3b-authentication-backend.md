# Task 050: Phase 3b Authentication - Backend Implementation

**Agent**: backend-swe
**Status**: Not Started
**Created**: 2026-01-04
**Effort**: 1.5-2 weeks
**Dependencies**: None
**Discovery Document**: [agent_progress_docs/2026-01-04_05-55-00_phase3b-auth-discovery.md](../agent_progress_docs/2026-01-04_05-55-00_phase3b-auth-discovery.md)

## Objective

Implement complete authentication infrastructure for PaperTrade backend following Clean Architecture principles. This enables secure user registration, login, and JWT-based API authentication required for production deployment.

## Context

**Discovery Analysis** (Task #049):
- Current Status: **0% authentication complete**
- Security Risk: **CRITICAL** - X-User-Id header is spoofable, no user ownership validation
- Infrastructure: 11% prepared (user_id field exists, dependency injection ready)
- Components Needed: 30 missing (78% of total architecture)

**Architecture Reference**: `architecture_plans/phase3-refined/phase3b-authentication.md`

## Implementation Order (Bottom-Up Clean Architecture)

### Week 1: Core Domain + Application Layer

#### 1. Add Dependencies (`backend/pyproject.toml`)
```toml
dependencies = [
    # ... existing ...
    "python-jose[cryptography]>=3.3.0",  # JWT tokens
    "passlib[bcrypt]>=1.7.4",            # Password hashing
    "python-multipart>=0.0.6",           # Form data parsing
]
```

Run: `cd backend && uv sync`

#### 2. Domain Layer (`backend/src/papertrade/domain/`)

**2.1 User Entity** (`entities/user.py`):
```python
from datetime import datetime
from uuid import UUID
from pydantic import EmailStr

class User:
    """User entity representing an authenticated user."""
    id: UUID
    email: EmailStr
    hashed_password: str
    created_at: datetime
    is_active: bool = True

    def __init__(self, ...): ...

    # Domain logic only - no I/O
```

**2.2 Auth Exceptions** (`exceptions.py` - add to existing):
```python
class UserNotFoundError(DomainError):
    """User does not exist."""

class InvalidCredentialsError(DomainError):
    """Invalid email or password."""

class DuplicateEmailError(DomainError):
    """Email already registered."""

class InvalidTokenError(DomainError):
    """Invalid or expired JWT token."""
```

**2.3 Password Service** (`services/password_service.py`):
```python
class PasswordService:
    """Domain service for password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a password against a hash."""
```

#### 3. Application Layer (`backend/src/papertrade/application/`)

**3.1 UserRepository Port** (`ports/user_repository.py`):
```python
from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from papertrade.domain.entities.user import User

class UserRepository(ABC):
    """Repository interface for User persistence."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Save a new user."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Find user by ID."""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update existing user."""
```

**3.2 JWT Service** (`services/jwt_service.py`):
```python
from datetime import datetime, timedelta
from uuid import UUID
from jose import jwt, JWTError

class JWTService:
    """Application service for JWT token generation and validation."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_access_token(
        self, user_id: UUID, expires_delta: timedelta = timedelta(minutes=15)
    ) -> str:
        """Generate access token."""

    def create_refresh_token(
        self, user_id: UUID, expires_delta: timedelta = timedelta(days=7)
    ) -> str:
        """Generate refresh token."""

    def decode_token(self, token: str) -> dict:
        """Decode and validate token."""
        # Raises InvalidTokenError on failure
```

**3.3 Register User Command** (`commands/register_user.py`):
```python
class RegisterUserCommand:
    email: str
    password: str

class RegisterUserHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
    ):
        self.user_repository = user_repository
        self.password_service = password_service

    async def handle(self, command: RegisterUserCommand) -> User:
        """Register a new user."""
        # 1. Check email doesn't exist
        # 2. Hash password
        # 3. Create User entity
        # 4. Save to repository
        # Raises: DuplicateEmailError
```

**3.4 Login User Command** (`commands/login_user.py`):
```python
class LoginUserCommand:
    email: str
    password: str

class LoginResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginUserHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
        jwt_service: JWTService,
    ):
        ...

    async def handle(self, command: LoginUserCommand) -> LoginResult:
        """Authenticate user and return tokens."""
        # 1. Find user by email
        # 2. Verify password
        # 3. Generate access + refresh tokens
        # Raises: InvalidCredentialsError
```

**3.5 Refresh Token Command** (`commands/refresh_token.py`):
```python
class RefreshTokenCommand:
    refresh_token: str

class RefreshTokenHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        jwt_service: JWTService,
    ):
        ...

    async def handle(self, command: RefreshTokenCommand) -> LoginResult:
        """Generate new tokens from refresh token."""
        # 1. Validate refresh token
        # 2. Get user from token
        # 3. Generate new access + refresh tokens
        # Raises: InvalidTokenError, UserNotFoundError
```

**3.6 Get User Query** (`queries/get_user.py`):
```python
class GetUserQuery:
    user_id: UUID

class GetUserHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, query: GetUserQuery) -> User:
        """Get user by ID."""
        # Raises: UserNotFoundError
```

### Week 2: Infrastructure + API Layer

#### 4. Database Layer (`backend/src/papertrade/adapters/outbound/`)

**4.1 UserModel** (`database/models.py` - add to existing):
```python
class UserModel(SQLModel, table=True):
    """Database model for User entity."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_user_email", "email", unique=True),
    )

    id: UUID = Field(primary_key=True)
    email: str = Field(max_length=255, index=True, unique=True)
    hashed_password: str = Field(max_length=255)
    created_at: datetime
    is_active: bool = Field(default=True)
```

**4.2 SQLModelUserRepository** (`database/user_repository.py`):
```python
class SQLModelUserRepository(UserRepository):
    """SQLModel implementation of UserRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        """Save new user to database."""

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Find user by ID."""

    async def get_by_email(self, email: str) -> Optional[User]:
        """Find user by email (case-insensitive)."""

    async def update(self, user: User) -> User:
        """Update existing user."""

    # Helper: _to_entity(model) -> User
    # Helper: _to_model(entity) -> UserModel
```

**4.3 Database Migration** (`backend/migrations/versions/`):
```bash
cd backend
uv run alembic revision -m "create_users_table"
```

Edit generated migration:
```python
def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Add unique index on email
    op.create_index('idx_user_email', 'users', ['email'], unique=True)

    # Add foreign key constraint to portfolios.user_id
    op.create_foreign_key(
        'fk_portfolio_user',
        'portfolios', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_portfolio_user', 'portfolios', type_='foreignkey')
    op.drop_index('idx_user_email')
    op.drop_table('users')
```

#### 5. API Layer (`backend/src/papertrade/adapters/inbound/api/`)

**5.1 Auth Router** (`auth.py` - new file):
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    handler: Annotated[RegisterUserHandler, Depends(get_register_user_handler)],
) -> dict:
    """Register a new user."""
    # Handle DuplicateEmailError -> 409 Conflict

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    handler: Annotated[LoginUserHandler, Depends(get_login_user_handler)],
) -> TokenResponse:
    """Login with email and password."""
    # Handle InvalidCredentialsError -> 401 Unauthorized

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    refresh_token: str,
    handler: Annotated[RefreshTokenHandler, Depends(get_refresh_token_handler)],
) -> TokenResponse:
    """Refresh access token."""
    # Handle InvalidTokenError -> 401 Unauthorized
```

**5.2 User Router** (`users.py` - new file):
```python
router = APIRouter(prefix="/users", tags=["users"])

class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: CurrentUserDep,
    handler: Annotated[GetUserHandler, Depends(get_get_user_handler)],
) -> UserResponse:
    """Get current authenticated user."""
```

**5.3 Replace Mock Authentication** (`dependencies.py`):
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> UUID:
    """Extract and validate user ID from JWT token."""
    try:
        payload = jwt_service.decode_token(token)
        user_id = UUID(payload.get("sub"))
        return user_id
    except (JWTError, ValueError, InvalidTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

# CurrentUserDep remains the same
```

**5.4 Dependency Injection** (`dependencies.py` - add handlers):
```python
async def get_register_user_handler(...) -> RegisterUserHandler:
    """Provide RegisterUserHandler with dependencies."""

async def get_login_user_handler(...) -> LoginUserHandler:
    """Provide LoginUserHandler with dependencies."""

# ... etc for all handlers
```

**5.5 Error Handlers** (`error_handlers.py` - add to existing):
```python
@app.exception_handler(DuplicateEmailError)
async def duplicate_email_handler(request: Request, exc: DuplicateEmailError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )

@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Incorrect email or password"},
        headers={"WWW-Authenticate": "Bearer"},
    )
```

**5.6 Update Main App** (`main.py`):
```python
from papertrade.adapters.inbound.api.auth import router as auth_router
from papertrade.adapters.inbound.api.users import router as users_router

app.include_router(auth_router)
app.include_router(users_router)
```

**5.7 Configuration** (`config.py` - add):
```python
class Settings(BaseSettings):
    # ... existing ...

    # JWT Settings
    JWT_SECRET_KEY: str = Field(..., description="Secret key for JWT signing")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
```

`.env` example:
```bash
JWT_SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
```

## Testing Strategy

### Domain Tests (`tests/unit/domain/`)
- ✅ User entity validation
- ✅ Password service hashing/verification
- ✅ Auth exceptions

### Application Tests (`tests/unit/application/`)
- ✅ RegisterUserHandler (happy path, duplicate email)
- ✅ LoginUserHandler (valid credentials, invalid credentials)
- ✅ RefreshTokenHandler (valid token, expired token, invalid token)
- ✅ GetUserHandler (existing user, non-existent user)
- ✅ JWTService token generation and validation

### Integration Tests (`tests/integration/`)
- ✅ UserRepository CRUD operations
- ✅ Database constraints (unique email)
- ✅ Foreign key constraint on portfolios.user_id

### API Tests (`tests/integration/api/`)
- ✅ POST /auth/register (201, 409 duplicate)
- ✅ POST /auth/login (200 with tokens, 401 invalid)
- ✅ POST /auth/refresh (200 with new tokens, 401 invalid)
- ✅ GET /users/me (200 with user data, 401 unauthorized)
- ✅ Protected endpoints reject missing/invalid tokens
- ✅ Protected endpoints accept valid tokens

### Coverage Target
- **Minimum**: 85% (existing standard)
- **Auth-Specific**: 95% (security-critical code)

## Security Checklist

- ✅ Passwords hashed with bcrypt (salt rounds ≥ 12)
- ✅ JWT secret from environment variable (not hardcoded)
- ✅ Access tokens short-lived (15 minutes)
- ✅ Refresh tokens longer-lived (7 days)
- ✅ Case-insensitive email lookups
- ✅ User enumeration prevented (generic login error messages)
- ✅ Passwords never logged or returned in responses
- ✅ 401 responses include WWW-Authenticate header

## Success Criteria

1. ✅ All new tests passing (95%+ coverage on auth code)
2. ✅ Existing tests still pass (no regressions)
3. ✅ Alembic migration runs successfully
4. ✅ Can register user via POST /auth/register
5. ✅ Can login via POST /auth/login (returns JWT tokens)
6. ✅ Protected endpoints reject invalid/missing tokens
7. ✅ Protected endpoints accept valid tokens
8. ✅ Token refresh works via POST /auth/refresh
9. ✅ Foreign key constraint enforces user ownership
10. ✅ Type checking passes (pyright --strict)

## Notes

- Replace ALL X-User-Id header references with JWT authentication
- Update API documentation to reflect new auth endpoints
- Ensure backward compatibility: existing portfolios can be migrated to users
- Frontend integration happens in Task #051 (depends on this task)

## References

- Architecture: `architecture_plans/phase3-refined/phase3b-authentication.md`
- Discovery: `agent_progress_docs/2026-01-04_05-55-00_phase3b-auth-discovery.md`
- Copilot Instructions: `.github/copilot-instructions.md`
