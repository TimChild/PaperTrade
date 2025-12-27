# Copilot Code Review Instructions for PaperTrade

## Project Context

PaperTrade is a stock market emulation platform following **Modern Software Engineering** principles (Dave Farley) and **Clean Architecture** (Robert C. Martin).

## Architecture Rules (CRITICAL)

### Dependency Rule
Dependencies must point **inward only**:
- **Domain** (innermost): Pure Python, no external dependencies
- **Application**: Depends only on Domain
- **Adapters**: Implements interfaces defined by Application/Domain
- **Infrastructure** (outermost): External concerns, frameworks

**Flag violations:**
- Domain importing from adapters, infrastructure, or frameworks (FastAPI, SQLModel, etc.)
- Application layer importing from infrastructure
- Any `from papertrade.adapters` or `from papertrade.infrastructure` in domain code

### Layer Locations
- Domain: `backend/src/papertrade/domain/`
- Application: `backend/src/papertrade/application/`
- Adapters: `backend/src/papertrade/adapters/`
- Infrastructure: `backend/src/papertrade/infrastructure/`

## Code Quality Standards

### Python (Backend)
- **Type hints required** on all functions - flag missing type hints
- **No `Any` type** - flag uses of `Any` unless explicitly justified
- **Docstrings** for public APIs
- **Async/await** used correctly for I/O operations
- **No mutable default arguments**

### TypeScript (Frontend)
- **Strict TypeScript** - no `any` types
- **Explicit return types** on functions
- **React hooks rules** followed correctly
- **Proper error handling** in async operations

## Testing Philosophy

- Tests should test **behavior, not implementation**
- Flag tests that mock internal classes (only mock at architectural boundaries)
- Flag tests without assertions
- Domain logic tests should NOT require database setup

## Financial Domain Specifics

- **Decimal** for money calculations, never `float`
- Money should be represented as value objects with currency
- Transactions/ledger entries should be **immutable**
- Flag any direct mutation of transaction records

## Common Issues to Flag

### Security
- Hardcoded secrets or API keys
- SQL injection vulnerabilities
- Missing input validation

### Performance
- N+1 query patterns
- Missing database indexes on foreign keys
- Unbounded queries without pagination

### Code Smells
- Functions longer than 30 lines
- Classes with too many responsibilities
- Deep nesting (more than 3 levels)
- Duplicate code blocks

## What NOT to Flag

- Use of `# type: ignore` when properly justified with comment
- Test files with longer functions (test setup can be verbose)
- Mock usage in integration tests at adapter boundaries
- `Any` type in test fixtures when unavoidable

## Commit Message Format

Should follow conventional commits:
- `feat(scope):` - New features
- `fix(scope):` - Bug fixes
- `refactor(scope):` - Code refactoring
- `test(scope):` - Test additions/changes
- `docs(scope):` - Documentation
- `chore(scope):` - Maintenance tasks

## Review Tone

- Be constructive and educational
- Explain *why* something is an issue, not just *what*
- Suggest specific improvements with code examples when helpful
- Acknowledge good patterns when you see them
