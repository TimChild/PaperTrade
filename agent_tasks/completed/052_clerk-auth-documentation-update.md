# Task 052: Update Documentation for Clerk Authentication

**Agent**: architect
**Status**: Not Started
**Created**: 2026-01-04
**Effort**: 3-4 hours
**Priority**: HIGH (blocks auth implementation)

## Objective

Update all project documentation to reflect the decision to use **Clerk** for authentication instead of custom JWT implementation. Documentation should be concise, focused on key decisions, and provide clear guidance for implementation.

## Context

### Strategic Decision (January 4, 2026)

After evaluation, we decided that **user authentication is commodity infrastructure** that doesn't add core product value. Using Clerk instead of custom JWT auth will:

- Save 3-4 weeks of development (login UI, profile pages, password reset, email verification, social login)
- Provide better security guarantees (managed by experts)
- Let development focus on core trading/backtesting features
- Still maintain Clean Architecture via adapter pattern

**Key Principles**:
1. **Focus on core value**: Our product value is trading simulation and backtesting, not auth
2. **Clean Architecture preserved**: Use `AuthPort` adapter to wrap Clerk
3. **Time-travel/backtesting is domain logic**: Auth just identifies users; simulated time is handled in domain layer
4. **Cost is acceptable**: Free tier (10,000 MAU) covers early development; scaling costs are acceptable

### Why Clerk Over Alternatives

| Factor | Clerk | Supabase | Custom JWT |
|--------|-------|----------|------------|
| React integration | ✅ Best | ⚠️ Good | ⚠️ Build yourself |
| Python SDK | ✅ Official | ⚠️ Exists | ✅ Full control |
| Pre-built UI | ✅ Complete | ❌ Basic | ❌ Build yourself |
| User profile pages | ✅ Included | ❌ Build | ❌ Build |
| Social login | ✅ Included | ✅ Included | ⏳ Later |
| Architecture coupling | ⚠️ Frontend | ❌ DB schemas | ✅ None |
| Time to implement | ✅ 2-3 days | ⚠️ 1 week | ❌ 3-4 weeks |

## Files to Update

### 1. REPLACE: `docs/architecture/phase3-refined/phase3b-authentication.md`

**Create new file** with Clerk-based architecture. Key sections:

```markdown
# Phase 3b: User Authentication with Clerk

**Duration**: 2-3 days
**Priority**: CRITICAL
**Approach**: Third-party auth (Clerk)

## Decision Summary

Use Clerk for authentication because:
- Auth is commodity infrastructure, not core product value
- Saves 3-4 weeks vs custom implementation
- Includes login UI, profile pages, password reset, social login
- Clean Architecture preserved via adapter pattern

## Architecture

### Backend Integration

AuthPort adapter wraps Clerk SDK:

\`\`\`python
class AuthPort(Protocol):
    async def verify_token(self, token: str) -> AuthenticatedUser: ...
    async def get_user(self, user_id: str) -> AuthenticatedUser | None: ...

class ClerkAuthAdapter(AuthPort):
    """Production: verifies Clerk JWT tokens"""
    ...

class InMemoryAuthAdapter(AuthPort):
    """Testing: no Clerk dependency"""
    ...
\`\`\`

### Frontend Integration

- Wrap app in `<ClerkProvider>`
- Use `<SignIn>`, `<SignUp>`, `<UserButton>` components
- Token automatically included in API requests

### Key Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| All `/api/v1/*` | Required | Clerk token in Authorization header |

## Implementation Tasks

1. Backend: Add `clerk-backend-api`, create `ClerkAuthAdapter`
2. Frontend: Add `@clerk/clerk-react`, wrap app, use components
3. Update existing endpoints to require auth
4. Update tests to use `InMemoryAuthAdapter`
```

### 2. UPDATE: `docs/architecture/phase3-refined/overview.md`

Update Phase 3b section to reflect Clerk approach. Change:
- "JWT-based authentication" → "Clerk-based authentication"
- "2-3 weeks" → "2-3 days"
- Add note about adapter pattern preserving Clean Architecture

### 3. UPDATE: `docs/architecture/phase4-refined/overview.md`

Update any JWT references to note Clerk tokens instead. The token flow is similar but managed by Clerk.

### 4. UPDATE: `project_plan.md`

In Phase 3 section, update authentication description:
- Remove detailed JWT implementation notes
- Add brief mention of Clerk as third-party auth solution
- Keep focus on what auth enables (multi-user, production deployment)

### 5. UPDATE: `project_strategy.md`

Review and update if needed:
- Remove any "educational value" framing around auth
- Ensure "focus on core product value" is emphasized
- Add section on "Build vs Buy" decisions if not present

### 6. DELETE or ARCHIVE

These files are now obsolete (already moved to `agent_tasks/archived/`):
- `agent_tasks/050_phase3b-authentication-backend.md`
- `agent_tasks/051_phase3b-authentication-frontend.md`

## Documentation Principles

**Be concise**:
- Remove lengthy JWT implementation details
- Focus on what (Clerk) and why (saves time, not core value)
- Keep architecture diagrams simple

**Focus on decisions**:
- What we chose and why
- What alternatives we considered
- Key trade-offs accepted

**Enable implementation**:
- Clear adapter interface for backend
- Clear component usage for frontend
- Testing approach with in-memory adapter

## Success Criteria

- [ ] `phase3b-authentication.md` replaced with Clerk-based architecture
- [ ] `overview.md` files updated with Clerk approach
- [ ] `project_plan.md` updated
- [ ] `project_strategy.md` reviewed for "build vs buy" clarity
- [ ] All docs emphasize Clerk as commodity infrastructure choice
- [ ] No orphaned references to custom JWT implementation
- [ ] Documentation is concise (half or less of original length)

## References

- Clerk React Quickstart: https://clerk.com/docs/react/getting-started/quickstart
- Clerk Python SDK: https://github.com/clerk/clerk-sdk-python
- Original analysis: `.tmp_auth_analysis.md` (temporary file in repo root)
