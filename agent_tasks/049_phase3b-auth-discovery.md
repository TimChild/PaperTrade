# Task 049: Phase 3b Authentication - Discovery & Gap Analysis

**Agent**: architect (or backend-swe)
**Priority**: HIGH
**Estimated Effort**: 1-2 hours (analysis only)
**Type**: Discovery Task

---

## Objective

**Before implementing Phase 3b (Authentication)**, conduct comprehensive analysis to determine what authentication/authorization infrastructure already exists in the codebase.

**Lesson Learned**: Phase 3a (SELL orders) was fully implemented but documented as "not started". We must check for existing code before implementing to avoid duplicate work.

## Context

**Phase 3b Requirements** (from architecture spec):
- User authentication (JWT-based)
- User registration and login endpoints
- Password hashing (bcrypt)
- User entity in domain model
- Portfolio ownership (user_id foreign key)
- Protected API endpoints
- Session management

**Critical**: **DO NOT implement anything yet**. Only analyze and report findings.

## Discovery Checklist

### 1. Domain Layer

**Search For**:
- [ ] User entity: `backend/src/papertrade/domain/entities/user.py`
- [ ] User-related exceptions: `UserNotFoundError`, `InvalidCredentialsError`
- [ ] Value objects: Email, Password, etc.

**Check**:
```bash
find backend/src/papertrade/domain -name "*user*" -o -name "*auth*"
grep -r "class User" backend/src/papertrade/domain/
```

### 2. Application Layer

**Search For**:
- [ ] Auth use cases/commands: `RegisterUser`, `LoginUser`, `ValidateToken`
- [ ] Password hashing service
- [ ] Token generation logic

**Check**:
```bash
find backend/src/papertrade/application -name "*user*" -o -name "*auth*"
grep -r "bcrypt\|hash_password\|verify_password" backend/src/papertrade/
```

### 3. API Layer

**Search For**:
- [ ] Auth endpoints: `/api/v1/auth/register`, `/api/v1/auth/login`
- [ ] JWT middleware/dependencies
- [ ] Protected route decorators

**Check**:
```bash
find backend/src/papertrade/adapters/inbound/api -name "*auth*"
grep -r "/auth/\|jwt\|JWT" backend/src/papertrade/adapters/
grep -r "get_current_user" backend/src/papertrade/
```

**Existing Mock Implementation**:
We know from `dependencies.py` line 80 that there's a comment about JWT validation:
```python
async def get_current_user_id(
    x_user_id: Annotated[str | None, Header()] = None,
) -> "UUID":
    """Get current user ID from request headers.

    This is a mock implementation for Phase 1. In production, this would:
    - Validate JWT token
    - Extract user ID from token
    - Raise 401 if unauthorized
```

**Action**: Check if this is still a mock or has been implemented.

### 4. Database Models

**Search For**:
- [ ] User table/model
- [ ] Portfolio.owner_id foreign key
- [ ] Migration files for user/auth tables

**Check**:
```bash
grep -r "owner_id" backend/src/papertrade/
ls backend/migrations/versions/ | grep -i user
```

### 5. Dependencies

**Search For**:
- [ ] `python-jose` or `pyjwt` (JWT libraries)
- [ ] `passlib` or `bcrypt` (password hashing)
- [ ] `python-multipart` (form data)

**Check**:
```bash
grep -E "python-jose|pyjwt|passlib|bcrypt" backend/pyproject.toml
```

### 6. Frontend

**Search For**:
- [ ] Login/Register pages
- [ ] Auth state management (Zustand store?)
- [ ] Token storage logic
- [ ] Protected routes

**Check**:
```bash
find frontend/src -name "*auth*" -o -name "*login*" -o -name "*register*"
grep -r "localStorage.*token\|authToken" frontend/src/
```

## Expected Deliverables

### Analysis Document

Create: `agent_progress_docs/2026-01-04_HH-MM-SS_phase3b-auth-discovery.md`

**Required Sections**:

1. **Executive Summary**
   - What exists (percentage complete: 0%, 25%, 50%, 75%, 100%)
   - What's missing
   - Recommended approach (implement from scratch vs complete gaps)

2. **Detailed Findings**
   - Domain layer status
   - Application layer status
   - API layer status
   - Database schema status
   - Frontend status
   - Dependencies status

3. **Gap Analysis Table**

| Component | Required | Exists | Status | Notes |
|-----------|----------|--------|--------|-------|
| User entity | Yes | No/Yes | ❌/✅ | Location or needed |
| Register endpoint | Yes | No/Yes | ❌/✅ | ... |
| ... | ... | ... | ... | ... |

4. **Implementation Recommendation**

**If 0-25% complete**:
- Implement full Phase 3b architecture spec
- Estimated effort: 2-3 weeks

**If 25-75% complete**:
- List specific gaps to fill
- Estimated effort: proportional

**If 75-100% complete**:
- Document existing implementation
- Create focused tasks for remaining gaps
- Estimated effort: < 1 week

5. **Next Steps**

Clear action items based on findings.

## Success Criteria

- [ ] All 6 discovery areas checked
- [ ] Comprehensive analysis document created
- [ ] Gap analysis table complete
- [ ] Implementation recommendation provided
- [ ] No code changes made (analysis only)
- [ ] Clear next steps documented

## Commands to Run

```bash
# Domain layer
find backend/src/papertrade/domain -name "*user*" -o -name "*auth*"
grep -r "class User" backend/src/papertrade/domain/

# Application layer
find backend/src/papertrade/application -name "*user*" -o -name "*auth*"
grep -r "bcrypt\|hash_password" backend/src/papertrade/

# API layer
grep -r "/auth/\|register\|login" backend/src/papertrade/adapters/inbound/api/
grep -r "JWT\|jwt\|Bearer" backend/src/papertrade/

# Database
grep -r "owner_id\|user_id" backend/src/papertrade/
ls -la backend/migrations/versions/

# Dependencies
grep -E "jose|jwt|passlib|bcrypt" backend/pyproject.toml

# Frontend
find frontend/src -name "*auth*" -o -name "*login*"
grep -r "token\|auth" frontend/src/services/
```

## Autonomy

**You Have Full Autonomy To**:
- Choose analysis methodology
- Organize findings document
- Add additional discovery areas
- Recommend alternative approaches

**You Must Follow**:
- NO code implementation (analysis only)
- Create comprehensive documentation
- Provide evidence for findings (file paths, line numbers)
- Give percentage completion estimate

## References

- **Architecture Spec**: `architecture_plans/phase3-refined/phase3b-authentication.md`
- **Lesson Learned**: `agent_progress_docs/2026-01-04_06-00-00_phase3a-already-complete-discovery.md`
- **Mock Implementation**: `backend/src/papertrade/adapters/inbound/api/dependencies.py` line 75-80

---

**Ready to Start**: Once committed, use `gh agent-task create --custom-agent architect -F agent_tasks/049_phase3b-auth-discovery.md`
