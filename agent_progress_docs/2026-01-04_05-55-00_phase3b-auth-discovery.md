# Phase 3b Authentication - Discovery & Gap Analysis

**Date**: 2026-01-04  
**Agent**: Architect  
**Task**: #049 - Phase 3b Authentication Discovery  
**Status**: ✅ ANALYSIS COMPLETE

---

## Executive Summary

**Completion Status**: **0% - No authentication infrastructure exists**

**Key Findings**:
- ❌ No User entity in domain layer
- ❌ No authentication/authorization logic anywhere in codebase
- ❌ No JWT libraries or password hashing dependencies
- ❌ No auth endpoints (login/register)
- ❌ Mock implementation only: X-User-Id header accepted without validation
- ❌ No user table in database schema
- ❌ No auth-related frontend pages or state management

**Recommendation**: **Implement full Phase 3b architecture specification from scratch**

**Estimated Effort**: 2-3 weeks (as per architecture plan)

**Impact**: This is a **CRITICAL** blocker for production deployment. The current implementation has:
- No data privacy (all portfolios are public via mock user IDs)
- No authorization (anyone can modify any portfolio with spoofed header)
- Security vulnerabilities (user IDs stored in localStorage can be easily manipulated)
- Cannot support multi-user scenarios

---

## Discovery Process

### Areas Analyzed

1. ✅ Domain Layer - Entities, value objects, exceptions
2. ✅ Application Layer - Use cases, commands, services
3. ✅ API Layer - Endpoints, middleware, dependencies
4. ✅ Database Layer - Models, migrations
5. ✅ Dependencies - JWT/password libraries
6. ✅ Frontend - Pages, state management, token storage

### Commands Executed

```bash
# Domain layer search
find backend/src/papertrade/domain -name "*user*" -o -name "*auth*"
grep -r "class User" backend/src/papertrade/domain/

# Application layer search
find backend/src/papertrade/application -name "*user*" -o -name "*auth*"
grep -r "bcrypt\|hash_password\|verify_password" backend/src/papertrade/

# API layer search
find backend/src/papertrade/adapters/inbound/api -name "*auth*"
grep -r "/auth/\|register\|login" backend/src/papertrade/adapters/inbound/api/
grep -r "JWT\|jwt\|Bearer\|get_current_user" backend/src/papertrade/

# Database search
grep -r "owner_id\|user_id" backend/src/papertrade/
ls -la backend/migrations/versions/

# Dependencies search
grep -E "python-jose|pyjwt|passlib|bcrypt" backend/pyproject.toml

# Frontend search
find frontend/src -name "*auth*" -o -name "*login*" -o -name "*register*"
grep -r "localStorage.*token\|authToken" frontend/src/
```

---

## Detailed Findings

### 1. Domain Layer - ❌ 0% Complete

**Status**: No authentication domain entities exist

**Checked**:
- ✅ `backend/src/papertrade/domain/entities/` - No User entity
- ✅ Domain exceptions - No auth-related exceptions

**Existing Entities**:
```
backend/src/papertrade/domain/entities/
├── portfolio.py      # Has user_id: UUID field (FK ready)
├── holding.py
└── transaction.py
```

**Existing Exceptions**:
```python
# backend/src/papertrade/domain/exceptions.py
- DomainException (base)
- InvalidValueObjectError
- InvalidMoneyError
- InvalidTickerError
- InvalidQuantityError
- InvalidEntityError
- InvalidPortfolioError
- InvalidTransactionError
- BusinessRuleViolationError
- InsufficientFundsError
- InsufficientSharesError
```

**Missing (Required by Architecture)**:
- ❌ User entity (`backend/src/papertrade/domain/entities/user.py`)
- ❌ Email value object
- ❌ Password value object (or hashing service)
- ❌ Auth-specific exceptions:
  - `UserNotFoundError`
  - `InvalidCredentialsError`
  - `DuplicateEmailError`
  - `InactiveUserError`

**Evidence**:
```bash
$ find backend/src/papertrade/domain -name "*user*" -o -name "*auth*"
# (no output - no files found)

$ grep -r "class User" backend/src/papertrade/domain/
# No User class found
```

**What EXISTS (user_id references)**:
- Portfolio entity has `user_id: UUID` field (line 36 in `domain/entities/portfolio.py`)
- This field is **documented** as "Owner of the portfolio (immutable)"
- Database model `PortfolioModel` includes `user_id: UUID` with index (line 36 in `adapters/outbound/database/models.py`)
- **Interpretation**: Infrastructure is **prepared** for user relationships, but User entity doesn't exist yet

---

### 2. Application Layer - ❌ 0% Complete

**Status**: No authentication use cases or services exist

**Checked**:
- ✅ `backend/src/papertrade/application/commands/` - No auth commands
- ✅ `backend/src/papertrade/application/queries/` - No user queries
- ✅ Password hashing - Not found anywhere

**Existing Commands**:
```
backend/src/papertrade/application/commands/
├── create_portfolio.py
├── deposit_funds.py
├── buy_stock.py
├── sell_stock.py
└── withdraw_funds.py
```

**Existing Queries**:
```
backend/src/papertrade/application/queries/
├── get_portfolio.py
├── get_portfolio_value.py
└── get_transactions.py
```

**Missing (Required by Architecture)**:
- ❌ `RegisterUserCommand` / `RegisterUserHandler`
- ❌ `LoginUserCommand` / `LoginUserHandler`
- ❌ `RefreshTokenCommand` / `RefreshTokenHandler`
- ❌ `GetUserQuery` / `GetUserQueryHandler`
- ❌ Password hashing service (bcrypt/passlib)
- ❌ JWT token generation/validation service
- ❌ UserRepository port interface

**Evidence**:
```bash
$ find backend/src/papertrade/application -name "*user*" -o -name "*auth*"
# (no output - no files found)

$ grep -r "bcrypt\|hash_password\|verify_password" backend/src/papertrade/
# No password hashing found
```

---

### 3. API Layer - ⚠️ 10% Complete (Mock Only)

**Status**: Mock authentication exists via X-User-Id header, no real auth

**Checked**:
- ✅ Auth endpoints - None exist
- ✅ JWT middleware - Not implemented
- ✅ Current user dependency - **Mock implementation found**

**Existing Endpoints**:
```
backend/src/papertrade/adapters/inbound/api/
├── portfolios.py    # Uses CurrentUserDep (mock)
├── transactions.py  # Uses CurrentUserDep (mock)
├── prices.py        # No auth required
└── dependencies.py  # Contains mock get_current_user_id
```

**Mock Implementation** (`dependencies.py` lines 74-108):
```python
async def get_current_user_id(
    x_user_id: Annotated[str | None, Header()] = None,
) -> "UUID":
    """Get current user ID from request headers.

    This is a mock implementation for Phase 1. In production, this would:
    - Validate JWT token
    - Extract user ID from token
    - Raise 401 if unauthorized

    For now, we accept a user ID via X-User-Id header for testing.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header is required (authentication not yet implemented)",
        )
    try:
        return UUID(x_user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-User-Id header: must be a valid UUID, got '{x_user_id}'",
        ) from e

CurrentUserDep = Annotated[UUID, Depends(get_current_user_id)]
```

**What This Means**:
- ✅ Dependency injection pattern is **ready** for real auth
- ✅ API routes already use `CurrentUserDep` for authorization checks
- ⚠️ **Security Risk**: Anyone can send any UUID in X-User-Id header
- ⚠️ No validation, no token, no security

**Missing (Required by Architecture)**:
- ❌ `/api/v1/auth/register` endpoint
- ❌ `/api/v1/auth/login` endpoint
- ❌ `/api/v1/auth/refresh` endpoint
- ❌ `/api/v1/auth/logout` endpoint (optional)
- ❌ `/api/v1/users/me` endpoint (get current user profile)
- ❌ JWT token validation middleware
- ❌ Replace `get_current_user_id` with real JWT validation
- ❌ Error handlers for 401 Unauthorized

**Evidence**:
```bash
$ find backend/src/papertrade/adapters/inbound/api -name "*auth*"
# (no output - no auth router files)

$ grep -r "/auth/\|register\|login" backend/src/papertrade/adapters/inbound/api/
backend/src/papertrade/adapters/inbound/api/error_handlers.py:def register_exception_handlers(app: FastAPI) -> None:
# (only found "register" in error handler registration context)

$ grep -r "JWT\|jwt\|Bearer" backend/src/papertrade/
backend/src/papertrade/adapters/inbound/api/dependencies.py:    - Validate JWT token
# (only found in mock implementation comment)
```

---

### 4. Database Layer - ⚠️ 20% Complete (Schema Ready)

**Status**: No User table, but Portfolio has user_id foreign key ready

**Checked**:
- ✅ Database models - No UserModel
- ✅ Migrations - No user table migrations
- ✅ Portfolio model - Has user_id field with index

**Existing Models** (`backend/src/papertrade/adapters/outbound/database/models.py`):
```python
class PortfolioModel(SQLModel, table=True):
    """Database model for Portfolio entity."""
    __tablename__ = "portfolios"
    __table_args__ = (Index("idx_portfolio_user_id", "user_id"),)
    
    id: UUID = Field(primary_key=True)
    user_id: UUID = Field(index=True)  # ✅ Ready for FK constraint
    name: str = Field(max_length=100)
    created_at: datetime
    updated_at: datetime
    version: int = Field(default=1)
```

**Evidence**:
```bash
$ grep -r "user_id" backend/src/papertrade/adapters/outbound/database/models.py
Line 25: user_id: Foreign key to user (UUID) - indexed for get_by_user queries
Line 33: __table_args__ = (Index("idx_portfolio_user_id", "user_id"),)
Line 36: user_id: UUID = Field(index=True)
```

**Existing Migrations**:
```
backend/migrations/versions/
├── e46ccf3fcc35_add_price_history_table.py
└── 7ca1e9126eba_add_ticker_watchlist_table.py
```

**What This Means**:
- ✅ Portfolio table **already has** `user_id` column
- ✅ Index exists on `user_id` for efficient `get_by_user` queries
- ⚠️ **No foreign key constraint** (because User table doesn't exist)
- ⚠️ Current `user_id` values are unconstrained UUIDs

**Missing (Required by Architecture)**:
- ❌ UserModel in `backend/src/papertrade/adapters/outbound/database/models.py`
- ❌ Migration to create `users` table:
  ```sql
  CREATE TABLE users (
      id UUID PRIMARY KEY,
      email VARCHAR(255) UNIQUE NOT NULL,
      hashed_password VARCHAR(255) NOT NULL,
      full_name VARCHAR(100),
      is_active BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMP NOT NULL,
      updated_at TIMESTAMP NOT NULL
  );
  ```
- ❌ Migration to add foreign key constraint:
  ```sql
  ALTER TABLE portfolios 
  ADD CONSTRAINT fk_portfolio_user 
  FOREIGN KEY (user_id) REFERENCES users(id);
  ```
- ❌ SQLModelUserRepository implementation

---

### 5. Dependencies - ❌ 0% Complete

**Status**: No JWT or password hashing libraries installed

**Checked**:
- ✅ `backend/pyproject.toml` dependencies
- ✅ No JWT libraries (python-jose, pyjwt)
- ✅ No password hashing (passlib, bcrypt)

**Current Backend Dependencies**:
```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlmodel>=0.0.22",
    "pydantic-settings>=2.6.0",
    "aiosqlite>=0.20.0",
    "asyncpg>=0.30.0",
    "greenlet>=3.0.0",
    "httpx>=0.27.0",
    "redis>=5.0.0",
    "alembic>=1.13.0",
    "apscheduler>=3.10.0",
]
```

**Evidence**:
```bash
$ grep -E "python-jose|pyjwt|passlib|bcrypt" backend/pyproject.toml
# No JWT/password libraries found
```

**Missing (Required by Architecture)**:
- ❌ `python-jose[cryptography]>=3.3.0` - JWT encoding/decoding
- ❌ `passlib[bcrypt]>=1.7.4` - Password hashing
- ❌ `python-multipart>=0.0.6` - Form data parsing (login forms)

**Recommended Additions**:
```toml
dependencies = [
    # ... existing ...
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.6",
]
```

---

### 6. Frontend - ⚠️ 15% Complete (Prepared Infrastructure)

**Status**: No auth pages, but infrastructure is prepared for tokens

**Checked**:
- ✅ Auth pages (login/register) - None exist
- ✅ State management - Zustand installed but no auth store
- ✅ Token storage - Commented code found

**Existing Frontend Structure**:
```
frontend/src/
├── pages/
│   ├── Dashboard.tsx        # No auth protection
│   └── PortfolioDetail.tsx  # No auth protection
├── services/
│   └── api/
│       └── client.ts        # Has commented auth code
└── (no auth-related files)
```

**Mock User ID Implementation** (`frontend/src/services/api/client.ts` lines 11-37):
```typescript
/**
 * Get or create a stable mock user ID for Phase 1.
 * Stored in localStorage to persist across sessions.
 *
 * TODO: Replace with real authentication in Phase 2
 */
function getMockUserId(): string {
  const STORAGE_KEY = 'papertrade_mock_user_id'
  
  // Check localStorage for existing ID
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    return stored
  }
  
  // Generate new ID and store it
  const newId = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, newId)
  return newId
}

const MOCK_USER_ID = getMockUserId()

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-User-Id': MOCK_USER_ID, // Mock authentication header
  },
})
```

**Prepared Infrastructure** (`frontend/src/services/api/client.ts` lines 42-50):
```typescript
// Request interceptor (for future auth token injection)
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token when implemented
    // const token = localStorage.getItem('authToken')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
)
```

**What This Means**:
- ✅ Axios interceptor pattern is **ready** for JWT injection
- ✅ Zustand installed (can create auth store)
- ⚠️ **Security Risk**: Mock user ID in localStorage can be manipulated
- ⚠️ No login/logout flow

**Missing (Required by Architecture)**:
- ❌ Login page (`frontend/src/pages/Login.tsx`)
- ❌ Register page (`frontend/src/pages/Register.tsx`)
- ❌ Auth store with Zustand:
  ```typescript
  interface AuthStore {
    user: User | null
    token: string | null
    login: (email: string, password: string) => Promise<void>
    register: (email: string, password: string, fullName: string) => Promise<void>
    logout: () => void
    refreshToken: () => Promise<void>
  }
  ```
- ❌ Protected route component (redirect to login if not authenticated)
- ❌ Auth API service functions:
  - `login(email, password)`
  - `register(email, password, fullName)`
  - `refreshToken()`
  - `logout()`
- ❌ Uncomment and implement token injection in axios interceptor
- ❌ Token refresh logic (before token expires)

**Frontend Dependencies**:
```json
"dependencies": {
  "@tanstack/react-query": "^5.62.11",  // ✅ Good for auth state
  "axios": "^1.13.2",                    // ✅ HTTP client ready
  "react-router-dom": "^7.11.0",         // ✅ Can add protected routes
  "zustand": "^5.0.3"                    // ✅ State management ready
}
```

**Evidence**:
```bash
$ find frontend/src -name "*auth*" -o -name "*login*" -o -name "*register*"
# (no output - no auth pages)

$ grep -r "localStorage.*token\|authToken" frontend/src/
frontend/src/services/api/client.ts:    // const token = localStorage.getItem('authToken')
# (only commented code found)
```

---

## Gap Analysis Table

| Component | Required | Exists | Status | Location/Notes |
|-----------|----------|--------|--------|----------------|
| **Domain Layer** |
| User entity | ✅ Yes | ❌ No | 🔴 Missing | Need `backend/src/papertrade/domain/entities/user.py` |
| Email value object | ✅ Yes | ❌ No | 🔴 Missing | Can use Pydantic EmailStr |
| Password hashing | ✅ Yes | ❌ No | 🔴 Missing | Need domain service or value object |
| UserNotFoundError | ✅ Yes | ❌ No | 🔴 Missing | Add to `domain/exceptions.py` |
| InvalidCredentialsError | ✅ Yes | ❌ No | 🔴 Missing | Add to `domain/exceptions.py` |
| DuplicateEmailError | ✅ Yes | ❌ No | 🔴 Missing | Add to `domain/exceptions.py` |
| **Application Layer** |
| RegisterUserCommand | ✅ Yes | ❌ No | 🔴 Missing | Need `application/commands/register_user.py` |
| LoginUserCommand | ✅ Yes | ❌ No | 🔴 Missing | Need `application/commands/login_user.py` |
| RefreshTokenCommand | ✅ Yes | ❌ No | 🔴 Missing | Need `application/commands/refresh_token.py` |
| GetUserQuery | ✅ Yes | ❌ No | 🔴 Missing | Need `application/queries/get_user.py` |
| UserRepository port | ✅ Yes | ❌ No | 🔴 Missing | Need `application/ports/user_repository.py` |
| JWT service | ✅ Yes | ❌ No | 🔴 Missing | Token generation/validation |
| Password service | ✅ Yes | ❌ No | 🔴 Missing | Hash/verify passwords |
| **API Layer** |
| /auth/register endpoint | ✅ Yes | ❌ No | 🔴 Missing | Need `adapters/inbound/api/auth.py` |
| /auth/login endpoint | ✅ Yes | ❌ No | 🔴 Missing | Need `adapters/inbound/api/auth.py` |
| /auth/refresh endpoint | ✅ Yes | ❌ No | 🔴 Missing | Need `adapters/inbound/api/auth.py` |
| /users/me endpoint | ✅ Yes | ❌ No | 🔴 Missing | Get current user profile |
| JWT middleware | ✅ Yes | ⚠️ Mock | 🟡 Replace | Replace `get_current_user_id` mock |
| CurrentUserDep | ✅ Yes | ✅ Yes | 🟢 Ready | `dependencies.py` line 206 |
| 401 error handlers | ✅ Yes | ❌ No | 🔴 Missing | Add to `error_handlers.py` |
| **Database Layer** |
| UserModel | ✅ Yes | ❌ No | 🔴 Missing | Need in `database/models.py` |
| Users table migration | ✅ Yes | ❌ No | 🔴 Missing | Create alembic migration |
| Portfolio FK constraint | ✅ Yes | ❌ No | 🔴 Missing | Add foreign key to users table |
| user_id in Portfolio | ✅ Yes | ✅ Yes | 🟢 Exists | `models.py` line 36 (no FK yet) |
| user_id index | ✅ Yes | ✅ Yes | 🟢 Exists | `models.py` line 33 |
| SQLModelUserRepository | ✅ Yes | ❌ No | 🔴 Missing | Need `database/user_repository.py` |
| **Dependencies** |
| python-jose | ✅ Yes | ❌ No | 🔴 Missing | JWT library |
| passlib[bcrypt] | ✅ Yes | ❌ No | 🔴 Missing | Password hashing |
| python-multipart | ✅ Yes | ❌ No | 🔴 Missing | Form data parsing |
| **Frontend** |
| Login page | ✅ Yes | ❌ No | 🔴 Missing | Need `pages/Login.tsx` |
| Register page | ✅ Yes | ❌ No | 🔴 Missing | Need `pages/Register.tsx` |
| Auth Zustand store | ✅ Yes | ❌ No | 🔴 Missing | Need `stores/authStore.ts` |
| Protected routes | ✅ Yes | ❌ No | 🔴 Missing | Auth guard component |
| Auth API service | ✅ Yes | ❌ No | 🔴 Missing | login/register/refresh functions |
| Token storage | ✅ Yes | ⚠️ Mock | 🟡 Replace | Replace mock user ID with token |
| Axios interceptor | ✅ Yes | ⚠️ Ready | 🟡 Implement | Uncomment and implement |
| Token refresh logic | ✅ Yes | ❌ No | 🔴 Missing | Auto-refresh before expiry |

**Legend**:
- 🔴 Missing: Does not exist, needs full implementation
- 🟡 Replace/Implement: Prepared infrastructure exists, needs real implementation
- 🟢 Ready/Exists: Already implemented and ready to use

**Summary**:
- **Total Components**: 38
- **Complete (🟢)**: 4 (11%)
- **Partial (🟡)**: 4 (11%)
- **Missing (🔴)**: 30 (78%)

---

## Implementation Recommendation

### Status: **0-25% Complete → Implement Full Architecture**

Based on the gap analysis, Phase 3b authentication is **0% implemented** (only 11% infrastructure preparation exists). The codebase has:

**What's Prepared** (11%):
1. ✅ Portfolio.user_id field exists with index
2. ✅ CurrentUserDep dependency injection pattern ready
3. ✅ Axios interceptor prepared for token injection
4. ✅ Zustand state management library installed

**What's Missing** (89%):
- All domain entities and exceptions
- All application use cases
- All API endpoints
- All database models and migrations
- All security libraries
- All frontend auth pages and logic

### Recommended Approach: **Full Implementation**

**Follow architecture specification exactly**:
- 📐 **Architecture Plan**: `architecture_plans/phase3-refined/phase3b-authentication.md`
- 📊 **Estimated Effort**: 2-3 weeks (per architecture plan)
- 🎯 **Implementation Strategy**: Bottom-up (Domain → Application → Adapters → Infrastructure → Frontend)

### Implementation Order (as per Clean Architecture)

**Week 1: Backend Core (Domain + Application)**
1. Add dependencies to `backend/pyproject.toml`
2. Create domain layer:
   - User entity
   - Auth exceptions
   - Password value object/service
3. Create application layer:
   - UserRepository port
   - RegisterUserCommand/Handler
   - LoginUserCommand/Handler
   - JWT service
   - Password service
4. Write comprehensive tests for domain and application

**Week 2: Backend Infrastructure (Adapters + Database)**
5. Create database layer:
   - UserModel
   - SQLModelUserRepository
   - Migration: create users table
   - Migration: add FK constraint to portfolios
6. Create API layer:
   - Auth router (`/auth/register`, `/auth/login`, `/auth/refresh`)
   - Replace `get_current_user_id` with JWT validation
   - Add 401 error handlers
7. Integration tests for API endpoints

**Week 3: Frontend (UI + State Management)**
8. Create auth state management:
   - Auth Zustand store
   - Auth API service
9. Create auth pages:
   - Login page
   - Register page
10. Implement protected routes
11. Update axios interceptor for JWT injection
12. Add token refresh logic
13. E2E tests for auth flow

---

## Security Considerations

### Current Security Risks (Production Blockers)

1. **🚨 CRITICAL: No Authentication**
   - Anyone can access any portfolio by guessing/generating UUIDs
   - X-User-Id header can be spoofed trivially
   - **Impact**: Complete data privacy violation

2. **🚨 CRITICAL: No Authorization**
   - No validation of user ownership
   - Anyone can modify/delete any portfolio
   - **Impact**: Data integrity violation, potential data loss

3. **⚠️ HIGH: Mock User ID in localStorage**
   - User IDs stored client-side can be manipulated
   - No cryptographic verification
   - **Impact**: User impersonation

4. **⚠️ MEDIUM: No Audit Trail**
   - Cannot track who performed which action
   - No compliance with data protection regulations
   - **Impact**: Legal/compliance risk

### Post-Implementation Security Requirements

When implementing Phase 3b, **must include**:

1. **Password Security**:
   - ✅ Use bcrypt with salt rounds ≥ 12
   - ✅ Never store plaintext passwords
   - ✅ Password strength validation (min 8 chars, complexity)

2. **JWT Security**:
   - ✅ Use RS256 (asymmetric) not HS256 (symmetric)
   - ✅ Short access token expiry (15 minutes)
   - ✅ Longer refresh token expiry (7 days)
   - ✅ Store refresh tokens server-side (Redis) for revocation
   - ✅ Rotate refresh tokens on use

3. **API Security**:
   - ✅ HTTPS only in production
   - ✅ CORS configuration
   - ✅ Rate limiting on auth endpoints
   - ✅ Account lockout after failed login attempts

4. **Frontend Security**:
   - ✅ HttpOnly cookies for refresh tokens (not localStorage)
   - ✅ Memory-only storage for access tokens
   - ✅ Clear tokens on logout/window close
   - ✅ CSRF protection

---

## Next Steps

### Immediate Actions (This Week)

1. **Create Backend Implementation Task** (#050):
   ```markdown
   # Task 050: Implement Phase 3b Authentication - Backend
   
   **Agent**: backend-swe
   **Effort**: 1.5-2 weeks
   **Architecture**: architecture_plans/phase3-refined/phase3b-authentication.md
   
   ## Implementation Order
   1. Add dependencies (python-jose, passlib)
   2. Domain layer (User entity, exceptions)
   3. Application layer (Use cases, repositories)
   4. Database layer (Models, migrations)
   5. API layer (Auth endpoints, JWT middleware)
   6. Tests (domain, application, integration)
   ```

2. **Create Frontend Implementation Task** (#051):
   ```markdown
   # Task 051: Implement Phase 3b Authentication - Frontend
   
   **Agent**: frontend-swe
   **Effort**: 1 week
   **Dependencies**: Task #050 (backend must be complete first)
   **Architecture**: architecture_plans/phase3-refined/phase3b-authentication.md
   
   ## Implementation Order
   1. Auth Zustand store
   2. Auth API service
   3. Login page
   4. Register page
   5. Protected routes
   6. Token refresh logic
   7. E2E tests
   ```

3. **Update Project Plan**:
   - Mark Phase 3b as "IN PROGRESS"
   - Update BACKLOG.md with tasks #050, #051
   - Update PROGRESS.md with discovery findings

### Follow-Up Tasks (After Phase 3b)

1. **Security Audit**:
   - Penetration testing
   - OWASP top 10 review
   - Dependency vulnerability scan

2. **Data Migration**:
   - Create default admin user
   - Assign existing portfolios to users (if any in production)
   - Clean up orphaned data

3. **Documentation**:
   - User guide for login/register
   - API documentation update (authentication section)
   - Deployment guide (JWT secret management)

---

## Lessons Learned

### From Phase 3a Discovery

Phase 3a (SELL orders) was discovered to be **100% complete** despite being marked as "not started" in project plan. This taught us to:

1. ✅ **Always check existing code before implementing**
2. ✅ **Run comprehensive discovery tasks**
3. ✅ **Document what already exists**

### For Phase 3b

This discovery confirms:

1. ✅ **Discovery task was valuable** - Found 0% complete (not 50% as might be assumed from user_id field)
2. ✅ **Architecture plan is accurate** - Matches what's actually needed
3. ✅ **Effort estimate is realistic** - 2-3 weeks for full implementation

---

## Appendix: Code Evidence

### A. Portfolio user_id Field

**File**: `backend/src/papertrade/domain/entities/portfolio.py`
```python
class Portfolio:
    """Portfolio entity representing a user's investment portfolio."""
    
    id: UUID
    user_id: UUID  # Owner of the portfolio (immutable)
    name: str
    created_at: datetime
```

### B. Mock Authentication

**File**: `backend/src/papertrade/adapters/inbound/api/dependencies.py` (lines 74-108)
```python
async def get_current_user_id(
    x_user_id: Annotated[str | None, Header()] = None,
) -> "UUID":
    """Get current user ID from request headers.

    This is a mock implementation for Phase 1. In production, this would:
    - Validate JWT token
    - Extract user ID from token
    - Raise 401 if unauthorized
    """
    if not x_user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header is required (authentication not yet implemented)",
        )
    try:
        return UUID(x_user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-User-Id header: must be a valid UUID, got '{x_user_id}'",
        ) from e

CurrentUserDep = Annotated[UUID, Depends(get_current_user_id)]
```

### C. Frontend Mock User ID

**File**: `frontend/src/services/api/client.ts` (lines 11-37)
```typescript
function getMockUserId(): string {
  const STORAGE_KEY = 'papertrade_mock_user_id'
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    return stored
  }
  const newId = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, newId)
  return newId
}

const MOCK_USER_ID = getMockUserId()

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-User-Id': MOCK_USER_ID, // Mock authentication header
  },
})
```

### D. Database Schema

**File**: `backend/src/papertrade/adapters/outbound/database/models.py` (lines 20-40)
```python
class PortfolioModel(SQLModel, table=True):
    """Database model for Portfolio entity."""
    
    __tablename__ = "portfolios"
    __table_args__ = (Index("idx_portfolio_user_id", "user_id"),)
    
    id: UUID = Field(primary_key=True)
    user_id: UUID = Field(index=True)  # No FK constraint (User table doesn't exist)
    name: str = Field(max_length=100)
    created_at: datetime
    updated_at: datetime
    version: int = Field(default=1)
```

**Evidence**: No `ForeignKey` relationship defined because User table doesn't exist.

---

## Summary

**Phase 3b Authentication Status**: **0% Complete**

**Recommendation**: Implement full architecture specification from `architecture_plans/phase3-refined/phase3b-authentication.md`

**Estimated Effort**: 2-3 weeks (Backend: 1.5-2 weeks, Frontend: 1 week)

**Critical Path**:
1. Backend domain + application (Week 1)
2. Backend database + API (Week 2)  
3. Frontend pages + state management (Week 3)

**Next Step**: Create implementation tasks #050 (backend) and #051 (frontend) referencing this discovery document.

---

**End of Discovery Report**
