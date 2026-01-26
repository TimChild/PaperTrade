# Task 064: Add Debug Page for Runtime Environment Information

**Status**: Not Started
**Priority**: MEDIUM
**Depends On**: None
**Estimated Effort**: 2-3 hours

## Objective

Create a hidden debug page (`/debug`) that displays runtime environment information and API key status to help diagnose configuration issues like Clerk authentication problems, missing API keys, and environment variable propagation.

## Problem Statement

When debugging issues in deployed environments or during development, it's difficult to verify:
- Which environment variables are loaded
- Whether API keys are present (without exposing their full values)
- What configuration the application is using
- Whether services are properly configured

A debug page would provide immediate visibility into the runtime state.

## Requirements

### Frontend Debug Page (`/debug`)

#### Route & Access
- Path: `/debug` (not linked in main navigation)
- No authentication required initially (can add later)
- Should work in both development and production
- Add a note: "⚠️ This page will be removed/protected before production deployment"

#### Information to Display

**1. Environment Detection**
```typescript
- NODE_ENV: development | production
- Build timestamp: <timestamp>
- React version: <version>
- Vite version: <version>
```

**2. API Configuration**
```typescript
- Backend API URL: http://localhost:8000 (from VITE_API_URL or default)
- WebSocket URL: ws://localhost:8000 (if configured)
```

**3. Authentication Status**
```typescript
- Clerk loaded: Yes/No
- Clerk publishable key present: Yes/No
- Clerk publishable key (first 20 chars): pk_test_xxx...
- Current user signed in: Yes/No
- User ID: <user_id> or "Not signed in"
```

**4. Feature Flags (if any)**
```typescript
- Any VITE_FEATURE_* environment variables
- Example: VITE_FEATURE_ANALYTICS: true
```

**5. Browser/Client Information**
```typescript
- User Agent: <user_agent>
- Window size: 1920x1080
- LocalStorage keys: [list of keys, not values]
```

### Backend Debug Endpoint (`GET /api/v1/debug`)

#### Route & Access
- Path: `/api/v1/debug`
- No authentication required initially (can add later)
- Should return JSON with runtime status

#### Information to Return

**1. Environment**
```json
{
  "environment": "development",
  "python_version": "3.13.1",
  "fastapi_version": "0.x.x"
}
```

**2. Database Status**
```json
{
  "database": {
    "connected": true,
    "url": "postgresql://localhost:5432/zebu",
    "pool_size": 10,
    "active_connections": 2
  }
}
```

**3. Redis Status**
```json
{
  "redis": {
    "connected": true,
    "url": "redis://localhost:6379/0",
    "ping": "OK"
  }
}
```

**4. API Keys Status (Redacted)**
```json
{
  "api_keys": {
    "clerk_secret_key": {
      "present": true,
      "prefix": "sk_test_",
      "length": 64
    },
    "alpha_vantage_api_key": {
      "present": true,
      "prefix": "DEMO",
      "length": 16
    }
  }
}
```

**5. External Services Health**
```json
{
  "services": {
    "clerk": {
      "reachable": true,
      "last_check": "2026-01-06T10:30:00Z"
    },
    "alpha_vantage": {
      "reachable": true,
      "rate_limit_remaining": 487,
      "last_check": "2026-01-06T10:30:00Z"
    }
  }
}
```

**6. Scheduler Status (if applicable)**
```json
{
  "scheduler": {
    "running": true,
    "jobs": [
      {
        "name": "refresh_prices",
        "next_run": "2026-01-07T00:00:00Z",
        "last_run": "2026-01-06T00:00:00Z",
        "status": "success"
      }
    ]
  }
}
```

## Security Considerations

### What to NEVER expose:
- Full API key values
- Database passwords
- Any secret tokens
- User data (PII)

### What IS safe to expose:
- Key prefixes (e.g., "sk_test_", "DEMO")
- Key presence (yes/no)
- Key length
- Service URLs (in dev mode)
- Connection status

### Redaction Pattern
```python
def redact_key(key: str) -> dict:
    """Return safe information about an API key."""
    return {
        "present": True,
        "prefix": key[:8] if len(key) >= 8 else key[:4],
        "length": len(key)
    }
```

## Implementation Details

### Frontend Structure

**1. Create Debug Page Component**
```typescript
// frontend/src/pages/Debug.tsx
export function Debug() {
  const { data, isLoading } = useQuery({
    queryKey: ['debug'],
    queryFn: () => api.getDebugInfo(),
  })

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">🔧 Debug Information</h1>
      <div className="bg-yellow-100 border border-yellow-400 p-4 mb-4">
        ⚠️ This page is for development/debugging only
      </div>

      {/* Environment Info */}
      {/* API Configuration */}
      {/* Backend Status */}
    </div>
  )
}
```

**2. Add Route**
```typescript
// frontend/src/App.tsx
import { Debug } from './pages/Debug'

<Route path="/debug" element={<Debug />} />
```

**3. Add API Method**
```typescript
// frontend/src/services/api/debug.ts
export async function getDebugInfo() {
  const response = await client.get('/debug')
  return response.data
}
```

### Backend Structure

**1. Create Debug Router**
```python
# backend/src/zebu/adapters/inbound/api/debug.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("")
async def get_debug_info(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """Return runtime environment information for debugging."""
    return {
        "environment": get_environment_info(),
        "database": await get_database_status(db),
        "redis": await get_redis_status(redis),
        "api_keys": get_api_keys_status(),
        "services": await get_services_health(),
    }
```

**2. Implement Helper Functions**
```python
def get_api_keys_status() -> dict:
    """Return redacted API key information."""
    keys = {}

    clerk_key = settings.CLERK_SECRET_KEY
    if clerk_key:
        keys["clerk_secret_key"] = {
            "present": True,
            "prefix": clerk_key[:8],
            "length": len(clerk_key)
        }
    else:
        keys["clerk_secret_key"] = {"present": False}

    # Similar for other API keys...
    return keys
```

**3. Register Router**
```python
# backend/src/zebu/adapters/inbound/api/main.py
from .debug import router as debug_router

app.include_router(debug_router, prefix="/api/v1")
```

## UI Design (Simple)

Use a clean, information-dense layout:

```
┌─────────────────────────────────────────┐
│ 🔧 Debug Information                    │
├─────────────────────────────────────────┤
│ ⚠️ Development only - not for production│
├─────────────────────────────────────────┤
│                                         │
│ Frontend Environment                    │
│ ├─ Environment: development             │
│ ├─ React: 18.x.x                        │
│ └─ Backend URL: http://localhost:8000   │
│                                         │
│ Authentication                          │
│ ├─ Clerk loaded: ✅                     │
│ ├─ Publishable key: pk_test_xxx...     │
│ └─ Signed in: Yes (user_2xxx)          │
│                                         │
│ Backend Status                          │
│ ├─ Database: ✅ Connected               │
│ ├─ Redis: ✅ Connected                  │
│ └─ API Keys:                            │
│    ├─ Clerk: ✅ sk_test_*** (64 chars)  │
│    └─ Alpha Vantage: ✅ DEMO (16 chars) │
│                                         │
│ External Services                       │
│ ├─ Clerk API: ✅ Reachable              │
│ └─ Alpha Vantage: ✅ 487/500 remaining  │
└─────────────────────────────────────────┘
```

## Testing

### Manual Testing
1. Navigate to `/debug`
2. Verify all sections display correctly
3. Check that API keys show redacted values
4. Verify backend endpoint returns JSON
5. Test with and without authentication

### Unit Tests
```python
# backend/tests/unit/api/test_debug.py
def test_debug_endpoint_redacts_secrets():
    """Verify secrets are never exposed in full."""
    response = client.get("/api/v1/debug")
    assert "sk_test_" in response.json()["api_keys"]["clerk_secret_key"]["prefix"]
    # Full key should NOT be present
    assert settings.CLERK_SECRET_KEY not in str(response.json())
```

## Success Criteria

- [ ] Frontend debug page accessible at `/debug`
- [ ] Backend debug endpoint accessible at `/api/v1/debug`
- [ ] All environment information displays correctly
- [ ] API keys are properly redacted (prefix only)
- [ ] No sensitive information exposed (full keys, passwords)
- [ ] Database and Redis connection status shown
- [ ] External service health checks working
- [ ] Page works in both development and production modes
- [ ] Tests verify no secrets leak

## Files to Create/Modify

### Frontend
- `frontend/src/pages/Debug.tsx` (create)
- `frontend/src/services/api/debug.ts` (create)
- `frontend/src/App.tsx` (add route)

### Backend
- `backend/src/zebu/adapters/inbound/api/debug.py` (create)
- `backend/src/zebu/adapters/inbound/api/main.py` (register router)
- `backend/tests/unit/api/test_debug.py` (create)

## Future Enhancements

- Add authentication requirement (admin-only access)
- Add request tracing/logging
- Add performance metrics
- Add cache statistics
- Export debug info as JSON download
- Add real-time WebSocket status

## Commands

```bash
# Run in dev mode
task dev

# Test backend endpoint
curl http://localhost:8000/api/v1/debug

# Navigate to frontend page
open http://localhost:5173/debug
```

## Notes

- This is a temporary debugging tool - should be removed or protected before public production
- Useful for diagnosing environment-specific issues
- Helps verify configuration in CI/CD pipelines
- Can leave enabled in development/staging, disable in production
