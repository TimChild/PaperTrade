# Task 037: Fix Backend Type Safety Issues

**Agent**: backend-swe
**Priority**: HIGH
**Created**: 2026-01-03
**Status**: Not Started
**Estimated Effort**: 2-3 hours

## Objective

Achieve 100% type safety in the backend codebase by fixing all 25 pyright errors and removing or properly justifying all `# type: ignore` comments. This ensures maintainability, reduces bugs, and maintains code quality standards.

## Context

**Current State** (as of 2026-01-03):
- 25 pyright errors detected
- 8 files with `# type: ignore` comments
- Type checking runs in CI but errors not failing builds (needs verification)

**Example Errors**:
```
backend/src/papertrade/infrastructure/database.py:27:5
  - error: Argument of type "dict[str, bool]" cannot be assigned to parameter "value" of type "bool"

backend/src/papertrade/infrastructure/scheduler.py:119:27
  - error: Argument missing for parameter "session"
```

**Files with type: ignore**:
1. `adapters/inbound/api/error_handlers.py`
2. `adapters/inbound/api/dependencies.py`
3. `adapters/outbound/database/models.py`
4. `adapters/outbound/models/price_history.py`
5. `adapters/outbound/models/ticker_watchlist.py`
6. `main.py`
7. `infrastructure/cache/price_cache.py`
8. `infrastructure/rate_limiter.py`

## Requirements

### 1. Fix All Pyright Errors

**Run diagnostics first**:
```bash
cd backend
uv run pyright --stats
```

**Fix each error**:
- Understand the root cause
- Prefer fixing the actual issue over adding type: ignore
- If generic types are needed, add them properly
- Ensure fixes don't break tests

**Common patterns to fix**:
- Missing type hints on function parameters/returns
- Incorrect generic type parameters
- Missing await on async functions
- Dictionary type mismatches

### 2. Review and Justify `# type: ignore` Comments

**For each `# type: ignore` comment**:

**Option A: Remove it** (preferred):
- Fix the underlying type issue
- Add proper type hints
- Use Protocol or TypeVar if needed

**Option B: Keep with justification**:
- Add comment explaining WHY it's needed
- Reference issue/limitation (e.g., "# type: ignore - SQLModel limitation, see issue #123")
- Only for genuinely unfixable third-party library issues

**Format for justified ignores**:
```python
# type: ignore[error-code]  # Reason: SQLModel doesn't support X, workaround for Y
```

### 3. Ensure Complete Type Coverage

**Check each function/method**:
- [ ] All parameters have type hints
- [ ] Return types specified
- [ ] No use of `Any` type (except documented cases)
- [ ] Generic types properly parameterized

**Example of complete typing**:
```python
# ✅ Good
async def get_portfolio(
    portfolio_id: UUID,
    session: AsyncSession,
) -> Portfolio:
    ...

# ❌ Bad
async def get_portfolio(portfolio_id, session):  # type: ignore
    ...
```

### 4. Add Type Checking to Pre-commit (if not already)

**Update `.pre-commit-config.yaml`** if needed:
```yaml
- repo: local
  hooks:
    - id: pyright
      name: Pyright type check
      entry: bash -c 'cd backend && uv run pyright'
      language: system
      types: [python]
      pass_filenames: false
```

## Specific Issues to Address

### Issue 1: database.py:27 - Dict Type Mismatch

**Current code**:
```python
if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
```

**Problem**: `connect_args` expects specific type, not generic dict

**Solution**: Properly type `engine_kwargs` or use TypedDict

### Issue 2: scheduler.py:119 - Missing Session Parameter

**Current code**:
```python
# Likely calling a function without required parameter
await some_function()
```

**Problem**: Function signature requires `session` parameter

**Solution**: Pass the session parameter or fix function signature

### Issue 3: `# type: ignore` in models.py

**Review**: SQLModel models often have legitimate type ignore needs

**Action**:
- Check if SQLModel has been updated to fix issues
- Justify remaining ignores with comments
- Consider using SQLModel type stubs if available

## Testing Methodology

### 1. Baseline Check
```bash
cd backend

# Get current error count
uv run pyright --stats > /tmp/pyright_before.txt
echo "Errors before: $(grep 'errors,' /tmp/pyright_before.txt)"
```

### 2. Fix and Verify
```bash
# After each fix
uv run pyright src/papertrade/<changed_file>.py

# Ensure tests still pass
uv run pytest tests/

# Check for regressions
uv run pyright --stats
```

### 3. Final Validation
```bash
# Should show: 0 errors, 0 warnings
uv run pyright --stats

# All tests pass
task test:backend

# Linting clean
task lint:backend
```

## Success Criteria

- [ ] `uv run pyright --stats` shows **0 errors, 0 warnings**
- [ ] All `# type: ignore` comments have justifications or are removed
- [ ] All tests pass: `task test:backend`
- [ ] No new linting issues: `task lint:backend`
- [ ] Type coverage at 100% (no `Any` types except justified)
- [ ] CI passes on the PR
- [ ] Documentation updated if type patterns changed significantly

## Files Likely to Change

1. `backend/src/papertrade/infrastructure/database.py`
2. `backend/src/papertrade/infrastructure/scheduler.py`
3. `backend/src/papertrade/adapters/inbound/api/error_handlers.py`
4. `backend/src/papertrade/adapters/inbound/api/dependencies.py`
5. `backend/src/papertrade/adapters/outbound/database/models.py`
6. `backend/src/papertrade/adapters/outbound/models/price_history.py`
7. `backend/src/papertrade/adapters/outbound/models/ticker_watchlist.py`
8. `backend/src/papertrade/main.py`
9. `backend/src/papertrade/infrastructure/cache/price_cache.py`
10. `backend/src/papertrade/infrastructure/rate_limiter.py`
11. `.pre-commit-config.yaml` (if adding pyright hook)

## Non-Goals

- ❌ Rewriting code for performance (focus on type safety only)
- ❌ Adding new features
- ❌ Refactoring unrelated to type issues
- ❌ Changing architecture or design patterns

## Common Patterns & Solutions

### Pattern 1: FastAPI Dependency Type Hints

**Problem**:
```python
async def get_db(request: Request):  # Missing return type
    ...
```

**Solution**:
```python
from collections.abc import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    ...
```

### Pattern 2: SQLModel Model Fields

**Problem**:
```python
class PortfolioModel(SQLModel, table=True):
    id: UUID  # type: ignore  # SQLModel doesn't understand UUID
```

**Solution**:
```python
from sqlmodel import Field

class PortfolioModel(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
```

### Pattern 3: Generic Repository Methods

**Problem**:
```python
async def get(self, id: UUID):  # Missing return type
    return await session.get(Model, id)
```

**Solution**:
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    async def get(self, id: UUID) -> T | None:
        return await session.get(self.model, id)
```

### Pattern 4: Redis Client Protocols

**Problem**:
```python
def __init__(self, redis):  # No type
    self.redis = redis
```

**Solution**:
```python
from typing import Protocol

class RedisClient(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...

def __init__(self, redis: RedisClient) -> None:
    self.redis = redis
```

## References

- Pyright documentation: https://github.com/microsoft/pyright/blob/main/docs/configuration.md
- SQLModel typing: https://sqlmodel.tiangolo.com/
- FastAPI typing: https://fastapi.tiangolo.com/python-types/
- Python typing docs: https://docs.python.org/3/library/typing.html
- Copilot instructions: `.github/copilot-instructions.md` (type safety requirements)

## Notes for Agent

- Take time to understand each error before fixing
- Don't rush - type safety prevents future bugs
- If unsure about a fix, leave a TODO comment and move on
- Tests must pass after all changes
- Some SQLModel/FastAPI quirks may require legitimate `# type: ignore`
- Prioritize correctness over perfection
- Document any architectural insights discovered during fixes
