# Backend Clerk Authentication Implementation

**Date**: 2026-01-04
**Agent**: backend-swe
**Task**: #053 - Implement Clerk Authentication (Backend Part)
**Status**: ✅ COMPLETE

---

## Executive Summary

Successfully implemented Clerk authentication for the PaperTrade backend, replacing the spoofable `X-User-Id` header with proper token-based authentication. The implementation follows Clean Architecture principles using the ports and adapters pattern, making it easy to swap authentication providers or use in-memory authentication for testing.

**Key Achievements**:
- ✅ Full Clerk authentication support via `ClerkAuthAdapter`
- ✅ Zero-dependency testing with `InMemoryAuthAdapter`
- ✅ All 418 backend tests passing
- ✅ 100% type safety (strict pyright checks)
- ✅ Clean separation of concerns (ports & adapters)
- ✅ Backward compatibility with UUID user IDs

---

## Changes Made

### 1. Dependencies

Added `clerk-backend-api` package to enable Clerk integration:

```bash
cd backend
uv add clerk-backend-api
```

**New dependencies**:
- `clerk-backend-api==4.2.0`
- `pyjwt==2.10.1` (dependency)
- `cryptography==45.0.7` (dependency)

### 2. Domain Layer

**File**: `backend/src/papertrade/domain/exceptions.py`

Added authentication-related exceptions:

```python
class AuthenticationError(DomainException):
    """Base exception for authentication-related errors."""
    pass

class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid, expired, or malformed."""
    pass
```

### 3. Application Layer - Port Interface

**File**: `backend/src/papertrade/application/ports/auth_port.py` (NEW)

Created the `AuthPort` protocol and `AuthenticatedUser` dataclass:

```python
@dataclass(frozen=True)
class AuthenticatedUser:
    """User identity from authentication provider."""
    id: str  # Clerk user ID (string format)
    email: str

class AuthPort(Protocol):
    """Port for authentication operations."""

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify token and return authenticated user."""
        ...

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        """Get user by ID."""
        ...
```

**Design Decision**: Used `str` for user ID instead of `UUID` because Clerk uses string IDs like `user_2abc123`. Added a compatibility layer in dependencies to convert to UUID for existing code.

### 4. Adapters

#### 4.1 In-Memory Adapter (Testing)

**File**: `backend/src/papertrade/adapters/auth/in_memory_adapter.py` (NEW)

```python
class InMemoryAuthAdapter(AuthPort):
    """In-memory authentication adapter for testing."""

    def __init__(self, users: dict[str, AuthenticatedUser] | None = None):
        self._users = users or {}
        self._tokens: dict[str, str] = {}

    def add_user(self, user: AuthenticatedUser, token: str) -> None:
        """Add a user with their token for testing."""
        self._users[user.id] = user
        self._tokens[token] = user.id

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify token and return user."""
        user_id = self._tokens.get(token)
        if not user_id or user_id not in self._users:
            raise InvalidTokenError("Invalid token")
        return self._users[user_id]
```

**Benefits**:
- No external dependencies (Redis, Clerk, etc.)
- Deterministic behavior for tests
- Fast test execution
- Easy to set up test scenarios

#### 4.2 Clerk Adapter (Production)

**File**: `backend/src/papertrade/adapters/auth/clerk_adapter.py` (NEW)

```python
class ClerkAuthAdapter(AuthPort):
    """Clerk implementation of AuthPort."""

    def __init__(self, secret_key: str):
        self._clerk = Clerk(bearer_auth=secret_key)

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify JWT token with Clerk."""
        try:
            request_state = self._clerk.verify_token(token)
            if not request_state or not hasattr(request_state, "user_id"):
                raise InvalidTokenError("Invalid or expired token")

            user = self._clerk.users.get(user_id=request_state.user_id)
            email = user.email_addresses[0].email_address if user.email_addresses else ""

            return AuthenticatedUser(id=user.id, email=email)
        except InvalidTokenError:
            raise
        except Exception as e:
            raise InvalidTokenError(f"Token verification failed: {str(e)}") from e
```

### 5. API Layer - FastAPI Dependencies

**File**: `backend/src/papertrade/adapters/inbound/api/dependencies.py`

#### 5.1 Added Imports

```python
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from papertrade.adapters.auth.clerk_adapter import ClerkAuthAdapter
from papertrade.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
from papertrade.application.ports.auth_port import AuthenticatedUser, AuthPort
from papertrade.domain.exceptions import InvalidTokenError

security = HTTPBearer()
```

#### 5.2 New Dependencies

```python
def get_auth_port() -> AuthPort:
    """Get authentication port implementation."""
    clerk_secret_key = os.getenv("CLERK_SECRET_KEY", "")

    if clerk_secret_key and clerk_secret_key != "test":
        return ClerkAuthAdapter(secret_key=clerk_secret_key)

    # Fall back to in-memory for testing
    return InMemoryAuthAdapter()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth: Annotated[AuthPort, Depends(get_auth_port)],
) -> AuthenticatedUser:
    """Extract and verify user from Authorization header."""
    try:
        return await auth.verify_token(credentials.credentials)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
```

#### 5.3 UUID Compatibility Layer

```python
async def get_current_user_id(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UUID:
    """Get current user ID as UUID from authenticated user.

    Compatibility layer that converts Clerk user ID (string) to UUID.
    Creates deterministic UUID from Clerk user ID string.
    """
    from uuid import uuid5, NAMESPACE_DNS
    return uuid5(NAMESPACE_DNS, current_user.id)
```

**Design Decision**: This allows existing code expecting UUIDs to continue working without modification. The same Clerk user ID always produces the same UUID.

#### 5.4 Updated Type Aliases

```python
AuthPortDep = Annotated[AuthPort, Depends(get_auth_port)]
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
CurrentUserDep = Annotated[UUID, Depends(get_current_user_id)]  # For backward compatibility
```

### 6. Test Infrastructure

**File**: `backend/tests/conftest.py`

#### 6.1 Auth Adapter Override

```python
def get_test_auth_port() -> InMemoryAuthAdapter:
    """Override auth port dependency to use in-memory adapter."""
    if not hasattr(get_test_auth_port, "_adapter"):
        adapter = InMemoryAuthAdapter()
        test_user = AuthenticatedUser(
            id="test-user-default",
            email="test@papertrade.example",
        )
        adapter.add_user(test_user, "test-token-default")
        get_test_auth_port._adapter = adapter

    return get_test_auth_port._adapter

# In client fixture:
app.dependency_overrides[get_auth_port] = get_test_auth_port
```

**Design Decision**: Used a singleton pattern (closure variable) to ensure all requests in a test use the same adapter instance, allowing tests to add additional users.

#### 6.2 New Fixtures

```python
@pytest.fixture
def default_user_id() -> UUID:
    """Provide a default user ID for tests."""
    from uuid import NAMESPACE_DNS, uuid5
    return uuid5(NAMESPACE_DNS, "test-user-default")

@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provide authentication headers for test requests."""
    return {"Authorization": "Bearer test-token-default"}
```

### 7. Integration Tests

Updated **3 test files** to use Bearer token authentication:

1. **test_portfolio_api.py**: 7 tests updated
2. **test_transaction_api.py**: 6 tests updated
3. **test_error_handling.py**: 12 tests updated

**Changes**:
- Replaced `headers={"X-User-Id": str(default_user_id)}` with `headers=auth_headers`
- Updated test signatures to include `auth_headers` fixture
- Updated multi-user tests to add additional users to the auth adapter
- Updated auth failure tests to expect `401 Unauthorized` instead of `400 Bad Request`

**Example**:

```python
# Before
def test_create_portfolio(client: TestClient, default_user_id: UUID) -> None:
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "Test", "initial_deposit": "10000.00"},
    )

# After
def test_create_portfolio(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={"name": "Test", "initial_deposit": "10000.00"},
    )
```

---

## Testing Results

### Unit Tests
```bash
cd backend
uv run pytest tests/unit/ -v
```
**Result**: ✅ All 305 unit tests passing

### Integration Tests
```bash
uv run pytest tests/integration/ -v
```
**Result**: ✅ All 113 integration tests passing

### Full Test Suite
```bash
uv run pytest tests/ -v
```
**Result**: ✅ **418/418 tests passing** (4 skipped)

### Code Quality
```bash
uv run ruff check src/ tests/
uv run pyright src/
```
**Result**: ✅ No linting errors, 0 type errors

---

## Architecture Decisions

### 1. Ports & Adapters Pattern

**Decision**: Define `AuthPort` as a protocol in the application layer, with concrete implementations in the adapters layer.

**Rationale**:
- Follows Dependency Inversion Principle
- Makes authentication provider swappable
- Enables zero-dependency testing
- Keeps domain/application layers pure

### 2. String User IDs with UUID Compatibility

**Decision**: Use `str` for Clerk user IDs internally, but provide UUID conversion for backward compatibility.

**Rationale**:
- Clerk uses string IDs (e.g., `user_2abc123`)
- Existing code expects UUIDs
- Deterministic conversion ensures consistency
- Enables gradual migration to string IDs

### 3. Singleton Auth Adapter in Tests

**Decision**: Cache the `InMemoryAuthAdapter` instance during test execution.

**Rationale**:
- Allows tests to add users dynamically
- Ensures all requests see the same users
- Prevents 401 errors when accessing added users
- Cleaned up after each test for isolation

### 4. 401 Unauthorized vs 400 Bad Request

**Decision**: Return `401 Unauthorized` for missing or invalid tokens (not `400 Bad Request`).

**Rationale**:
- Follows HTTP standards (RFC 7235)
- `401` = "authentication required or failed"
- `400` = "malformed request syntax"
- Missing/invalid tokens are authentication failures

---

## Environment Configuration

### Development/Testing

No configuration needed - automatically uses `InMemoryAuthAdapter`.

### Production

Add to `.env` or environment variables:

```bash
CLERK_SECRET_KEY=sk_test_...  # From Clerk dashboard
```

When `CLERK_SECRET_KEY` is set (and not "test"), the backend will use `ClerkAuthAdapter`.

---

## Migration Notes

### For Existing Code

1. **API Endpoints**: No changes needed if using `CurrentUserDep` type alias
2. **Tests**: Updated to use `auth_headers` fixture instead of `X-User-Id` header
3. **Database**: User IDs are still stored as UUIDs (no migration needed)

### For New Code

Prefer using `CurrentUser` to get the full `AuthenticatedUser` object:

```python
@router.post("/example")
async def example(
    current_user: CurrentUser,  # Full authenticated user object
    # ...
) -> Response:
    user_email = current_user.email
    user_id = current_user.id  # Clerk string ID
```

---

## Known Limitations

1. **Clerk SDK Synchronous API**: The Clerk Python SDK uses synchronous calls. We wrap them in `async` functions for consistency, but they don't provide actual concurrency benefits. This is a limitation of the Clerk SDK, not our implementation.

2. **User ID Format Change**: Clerk uses string IDs. We provide UUID compatibility, but future features should be designed to work with string IDs.

3. **Email Requirement**: We assume users have at least one email address in Clerk. If not, email will be an empty string.

---

## Next Steps (Frontend Integration)

The backend is ready for frontend integration. Next steps:

1. **Install Clerk React SDK**: `npm install @clerk/clerk-react`
2. **Wrap App**: Add `<ClerkProvider>` to `main.tsx`
3. **Add Auth UI**: Use `<SignIn>`, `<SignedIn>`, `<SignedOut>` components
4. **Update API Client**: Add Clerk token to API requests
5. **Remove X-User-Id**: Delete manual user ID management

See Task #053 frontend section for detailed implementation plan.

---

## Files Changed

### Created (4 files)
- `backend/src/papertrade/application/ports/auth_port.py`
- `backend/src/papertrade/adapters/auth/__init__.py`
- `backend/src/papertrade/adapters/auth/clerk_adapter.py`
- `backend/src/papertrade/adapters/auth/in_memory_adapter.py`

### Modified (7 files)
- `backend/pyproject.toml` (added clerk-backend-api)
- `backend/uv.lock` (dependency resolution)
- `backend/src/papertrade/domain/exceptions.py` (auth exceptions)
- `backend/src/papertrade/adapters/inbound/api/dependencies.py` (auth deps)
- `backend/tests/conftest.py` (test fixtures)
- `backend/tests/integration/test_portfolio_api.py` (7 tests)
- `backend/tests/integration/test_transaction_api.py` (6 tests)
- `backend/tests/integration/test_error_handling.py` (12 tests)

---

## Commit

```
Implement Clerk authentication backend integration

- Add clerk-backend-api dependency
- Create InvalidTokenError domain exception
- Implement AuthPort interface with AuthenticatedUser dataclass
- Create ClerkAuthAdapter for production Clerk integration
- Create InMemoryAuthAdapter for testing without Clerk
- Update FastAPI dependencies with Bearer token authentication
- Replace X-User-Id header with Authorization: Bearer token
- Add UUID compatibility layer for existing code
- Update test fixtures to use InMemoryAuthAdapter
- Update all integration tests to use Bearer tokens
- All 418 tests passing with new auth system
```
