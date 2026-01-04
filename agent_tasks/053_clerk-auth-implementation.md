# Task 053: Implement Clerk Authentication

**Agent**: backend-swe (first), then frontend-swe
**Status**: Not Started
**Created**: 2026-01-04
**Effort**: 2-3 days total
**Dependencies**: Task #052 (documentation update)
**Priority**: HIGH

## Objective

Integrate Clerk for user authentication, replacing the spoofable X-User-Id header with proper token-based auth. Maintain Clean Architecture via adapter pattern.

## Prerequisites

1. Create Clerk account at https://clerk.com
2. Create new Clerk application
3. Get API keys:
   - `CLERK_PUBLISHABLE_KEY` (frontend)
   - `CLERK_SECRET_KEY` (backend)

## Part 1: Backend Integration (backend-swe)

### 1.1 Add Dependencies

```bash
cd backend
uv add clerk-backend-api
```

### 1.2 Create Auth Port Interface

`backend/src/papertrade/application/ports/auth_port.py`:

```python
from typing import Protocol
from uuid import UUID
from dataclasses import dataclass

@dataclass(frozen=True)
class AuthenticatedUser:
    """User identity from authentication provider."""
    id: str  # Clerk user ID (string, not UUID)
    email: str

class AuthPort(Protocol):
    """Port for authentication operations."""

    async def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify token and return authenticated user.

        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        ...

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        """Get user by ID, or None if not found."""
        ...
```

### 1.3 Create Clerk Adapter

`backend/src/papertrade/adapters/auth/clerk_adapter.py`:

```python
from clerk_backend_api import Clerk
from clerk_backend_api.jwks import AuthenticateRequestOptions

from papertrade.application.ports.auth_port import AuthPort, AuthenticatedUser
from papertrade.domain.exceptions import InvalidTokenError

class ClerkAuthAdapter(AuthPort):
    """Clerk implementation of AuthPort."""

    def __init__(self, secret_key: str):
        self._clerk = Clerk(bearer_auth=secret_key)

    async def verify_token(self, token: str) -> AuthenticatedUser:
        try:
            # Verify JWT with Clerk
            request_state = self._clerk.authenticate_request(
                # ... verification logic
            )
            if not request_state.is_signed_in:
                raise InvalidTokenError("Invalid or expired token")

            return AuthenticatedUser(
                id=request_state.user_id,
                email=request_state.claims.get("email", ""),
            )
        except Exception as e:
            raise InvalidTokenError(str(e))

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        try:
            user = self._clerk.users.get(user_id=user_id)
            return AuthenticatedUser(
                id=user.id,
                email=user.email_addresses[0].email_address,
            )
        except Exception:
            return None
```

### 1.4 Create In-Memory Adapter (Testing)

`backend/src/papertrade/adapters/auth/in_memory_adapter.py`:

```python
from papertrade.application.ports.auth_port import AuthPort, AuthenticatedUser
from papertrade.domain.exceptions import InvalidTokenError

class InMemoryAuthAdapter(AuthPort):
    """In-memory auth for testing - no Clerk dependency."""

    def __init__(self, users: dict[str, AuthenticatedUser] | None = None):
        self._users = users or {}
        self._tokens: dict[str, str] = {}  # token -> user_id

    def add_user(self, user: AuthenticatedUser, token: str) -> None:
        """Add a user with their token for testing."""
        self._users[user.id] = user
        self._tokens[token] = user.id

    async def verify_token(self, token: str) -> AuthenticatedUser:
        user_id = self._tokens.get(token)
        if not user_id or user_id not in self._users:
            raise InvalidTokenError("Invalid token")
        return self._users[user_id]

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        return self._users.get(user_id)
```

### 1.5 Create FastAPI Dependency

`backend/src/papertrade/adapters/api/dependencies/auth.py`:

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from papertrade.application.ports.auth_port import AuthPort, AuthenticatedUser
from papertrade.domain.exceptions import InvalidTokenError

security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth: Annotated[AuthPort, Depends(get_auth_port)],  # Injected
) -> AuthenticatedUser:
    """Extract and verify user from Authorization header."""
    try:
        return await auth.verify_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Type alias for cleaner route signatures
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
```

### 1.6 Update Existing Endpoints

Replace `X-User-Id` header with `CurrentUser` dependency:

```python
# Before
@router.post("/portfolios")
async def create_portfolio(
    request: CreatePortfolioRequest,
    user_id: UUID = Header(..., alias="X-User-Id"),
):
    ...

# After
@router.post("/portfolios")
async def create_portfolio(
    request: CreatePortfolioRequest,
    current_user: CurrentUser,
):
    # Use current_user.id instead of user_id
    ...
```

### 1.7 Update Configuration

`backend/src/papertrade/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings

    # Clerk
    clerk_secret_key: str = ""

    model_config = SettingsConfigDict(env_file=".env")
```

### 1.8 Update Tests

Update `conftest.py` to use `InMemoryAuthAdapter`:

```python
@pytest.fixture
def auth_adapter():
    adapter = InMemoryAuthAdapter()
    test_user = AuthenticatedUser(id="test-user-123", email="test@example.com")
    adapter.add_user(test_user, "test-token")
    return adapter

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}
```

## Part 2: Frontend Integration (frontend-swe)

### 2.1 Add Dependencies

```bash
cd frontend
npm install @clerk/clerk-react
```

### 2.2 Configure Environment

`.env.local`:
```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

### 2.3 Wrap App with ClerkProvider

`frontend/src/main.tsx`:

```typescript
import { ClerkProvider } from '@clerk/clerk-react'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ClerkProvider>
  </React.StrictMode>
)
```

### 2.4 Add Auth Components

`frontend/src/App.tsx`:

```typescript
import { SignedIn, SignedOut, SignIn, UserButton } from '@clerk/clerk-react'

function App() {
  return (
    <>
      <SignedOut>
        <div className="flex items-center justify-center min-h-screen">
          <SignIn />
        </div>
      </SignedOut>
      <SignedIn>
        <Header />
        <TradingDashboard />
      </SignedIn>
    </>
  )
}

function Header() {
  return (
    <header className="flex justify-between p-4">
      <h1>PaperTrade</h1>
      <UserButton />  {/* Pre-built profile dropdown */}
    </header>
  )
}
```

### 2.5 Add Token to API Requests

`frontend/src/lib/api.ts`:

```typescript
import { useAuth } from '@clerk/clerk-react'

// Create authenticated fetch wrapper
export function useAuthenticatedApi() {
  const { getToken } = useAuth()

  return async (url: string, options: RequestInit = {}) => {
    const token = await getToken()
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    })
  }
}
```

### 2.6 Remove X-User-Id Logic

- Remove `useUserId` hook
- Remove localStorage user ID storage
- Remove manual user ID headers from API calls

## Migration Notes

### User ID Format Change

Clerk uses string IDs (e.g., `user_2abc123`), not UUIDs. Update:
- Portfolio `user_id` column to TEXT (or keep UUID and map)
- Consider storing both Clerk ID and internal UUID

### Existing Data

For development, existing portfolios can be:
1. Deleted (clean slate)
2. Migrated to test user ID

## Success Criteria

- [ ] Backend: `AuthPort` interface defined
- [ ] Backend: `ClerkAuthAdapter` implemented
- [ ] Backend: `InMemoryAuthAdapter` for testing
- [ ] Backend: All endpoints use `CurrentUser` dependency
- [ ] Backend: All tests pass with `InMemoryAuthAdapter`
- [ ] Frontend: App wrapped in `ClerkProvider`
- [ ] Frontend: `<SignIn>`, `<SignedIn>`, `<SignedOut>` working
- [ ] Frontend: `<UserButton>` shows profile menu
- [ ] Frontend: API requests include Clerk token
- [ ] Frontend: No more X-User-Id references
- [ ] E2E: Can sign up, sign in, create portfolio, trade

## References

- Clerk React: https://clerk.com/docs/react/getting-started/quickstart
- Clerk Python: https://github.com/clerk/clerk-sdk-python
- Clerk FastAPI: https://clerk.com/docs/backend-requests/handling/fastapi
