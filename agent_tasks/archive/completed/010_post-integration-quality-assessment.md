# Task 010: Post-Integration Code Quality Assessment

## Objective
Conduct a comprehensive code quality assessment after completing the vertical integration (Database → Domain → Application → Adapters → API → Frontend). Identify refactoring opportunities, architectural improvements, and developer experience enhancements to ensure a maintainable foundation before scaling.

## Context
This task runs **after task 009** (Frontend-Backend Integration) completes. At this point we have:
- ✅ Complete vertical slice working end-to-end
- ✅ All three backend layers (Domain, Application, Adapters)
- ✅ Frontend integrated with live API
- ✅ Real workflows tested

**Goal**: Identify and prioritize improvements while the codebase is still small and manageable.

## Assessment Areas

### 1. Code Quality Analysis

#### Backend (Python)
Analyze `backend/src/zebu/`:

**Domain Layer** (`domain/`):
- [ ] No duplication across entities, value objects, services
- [ ] Complex logic properly encapsulated
- [ ] All edge cases covered in tests
- [ ] No `Any` types (strict mode passing)
- [ ] Consistent naming conventions
- [ ] Proper docstrings on public APIs

**Application Layer** (`application/`):
- [ ] Commands and Queries follow consistent patterns
- [ ] DTOs properly isolate domain from API
- [ ] Repository ports cleanly defined
- [ ] No business logic leaked into handlers
- [ ] Error handling consistent across use cases
- [ ] Validation logic not duplicated

**Adapters Layer** (`adapters/`):
- [ ] FastAPI routes are thin (no business logic)
- [ ] SQLModel repositories implement ports correctly
- [ ] Database queries optimized (N+1 checks)
- [ ] Proper dependency injection
- [ ] Request/response validation working
- [ ] CORS, middleware properly configured

**Cross-Cutting Concerns**:
- [ ] Exception hierarchy well-designed
- [ ] Logging strategy consistent
- [ ] Configuration management clean
- [ ] No hardcoded values (use environment variables)

#### Frontend (TypeScript/React)
Analyze `frontend/src/`:

**Components**:
- [ ] Single Responsibility Principle followed
- [ ] No prop drilling (use context where appropriate)
- [ ] Consistent component structure
- [ ] Proper TypeScript types (no `any`)
- [ ] Accessibility basics covered
- [ ] Responsive design patterns

**Hooks/Services**:
- [ ] TanStack Query hooks follow consistent patterns
- [ ] API client properly typed
- [ ] Error handling consistent
- [ ] Cache invalidation strategy correct
- [ ] No duplicate API calls

**State Management**:
- [ ] Zustand stores well-organized
- [ ] No unnecessary global state
- [ ] Local state used appropriately

### 2. Architecture Compliance

**Clean Architecture Rules**:
- [ ] Domain has ZERO external dependencies
- [ ] Application only imports Domain
- [ ] Adapters only imports Application and Domain
- [ ] No circular dependencies
- [ ] Repository pattern properly implemented

**Verification Commands**:
```bash
# Check for forbidden imports
grep -r "from zebu.adapters" backend/src/zebu/domain/
grep -r "from zebu.adapters" backend/src/zebu/application/
grep -r "from fastapi" backend/src/zebu/domain/
grep -r "from sqlmodel" backend/src/zebu/domain/
```

### 3. Test Quality

**Coverage Analysis**:
```bash
cd backend
uv run pytest --cov=src/zebu --cov-report=html --cov-report=term
```

Check for:
- [ ] Domain: >95% coverage (pure logic, easy to test)
- [ ] Application: >90% coverage (use cases critical)
- [ ] Adapters: >80% coverage (integration tests)
- [ ] Frontend: >70% coverage (components, hooks)

**Test Organization**:
- [ ] Unit tests isolated (no database, no network)
- [ ] Integration tests separated
- [ ] Test names descriptive
- [ ] No test duplication
- [ ] Fixtures/factories well-organized

**Test Quality**:
- [ ] Tests verify behavior, not implementation
- [ ] Edge cases covered
- [ ] Error cases tested
- [ ] No brittle tests (timing, order dependency)

**Frontend Testing** (CRITICAL from PR #16):
- [ ] **MSW (Mock Service Worker) setup** - Required to fix 3 failing App.test.tsx tests
  - Install MSW: `npm install -D msw@latest`
  - Create `frontend/src/mocks/handlers.ts` for API mocking
  - Configure MSW in test setup
  - Update App.test.tsx to work with mocked API responses
  - Verify all frontend tests passing (should go from 20/23 → 23/23)

### 4. Developer Experience

**Documentation**:
- [ ] README has clear setup instructions
- [ ] Architecture documented (diagrams?)
- [ ] API documented (OpenAPI/Swagger)
- [ ] ADRs capture key decisions
- [ ] Inline comments where needed (not obvious code)

**Tooling**:
- [ ] Linting rules appropriate
- [ ] Formatting automatic (pre-commit hooks)
- [ ] Type checking enforced
- [ ] Git hooks working properly

**Development Workflow**:
- [ ] Local environment easy to setup
- [ ] Docker Compose working
- [ ] Database migrations clear
- [ ] Seed data available
- [ ] Hot reload working

**Scripts/Automation**:
- [ ] Taskfile.yml commands documented
- [ ] Common operations scripted
- [ ] Test running simple
- [ ] Build process clear

### 5. Performance & Scalability

**Backend**:
- [ ] Database queries indexed properly
- [ ] No N+1 query problems
- [ ] Pagination implemented where needed
- [ ] Response times acceptable (<200ms for simple queries)

**Frontend**:
- [ ] Bundle size reasonable
- [ ] Code splitting implemented
- [ ] Images optimized
- [ ] TanStack Query caching effective

### 6. Security Basics

**Backend**:
- [ ] No secrets in code
- [ ] Environment variables for config
- [ ] Input validation on all endpoints
- [ ] SQL injection protection (ORMs help)
- [ ] CORS configured correctly

**Frontend**:
- [ ] No API keys in client code
- [ ] XSS protection basics
- [ ] HTTPS only in production

## Deliverables

### 1. Assessment Report
Create `agent_tasks/progress/YYYY-MM-DD_HH-MM-SS_quality-assessment.md`:

```markdown
# Code Quality Assessment Report

## Executive Summary
- Overall Health: [Score/10]
- Critical Issues: [Count]
- Recommended Actions: [Count]

## Findings by Category

### Code Quality
#### Strengths
- [List 3-5 things done well]

#### Areas for Improvement
- [Issue 1]: [Description]
  - Impact: [High/Medium/Low]
  - Effort: [Hours estimate]
  - Priority: [1-5]

### Architecture
[Same format]

### Testing
[Same format]

### Developer Experience
[Same format]

## Priority Matrix

| Issue | Impact | Effort | Priority | Recommendation |
|-------|--------|--------|----------|----------------|
| [Description] | High | 2h | P1 | Fix before Phase 2 |

## Recommended Action Plan

### Phase 1: Critical (Do Before Adding Features)
1. [Issue 1] - [Time estimate]
2. [Issue 2] - [Time estimate]

### Phase 2: Important (Next Sprint)
[Issues that improve quality but not blocking]

### Phase 3: Nice-to-Have (Backlog)
[Lower priority improvements]

## Metrics

### Before Assessment
- Test Coverage: X%
- Linting Errors: X
- Type Errors: X
- LOC: X

### Code Complexity
- Average Cyclomatic Complexity: X
- Functions > 50 LOC: X
- Max Nesting Depth: X
```

### 2. Refactoring Tasks
Create individual task files for top improvements:
- `agent_tasks/011_[specific-refactoring].md`
- `agent_tasks/012_[specific-refactoring].md`
- etc.

### 3. Updated BACKLOG.md
Add identified issues to backlog with priorities.

## Analysis Tools

### Python Backend
```bash
# Complexity analysis
uv run radon cc backend/src/zebu/ -a -nb

# Maintainability index
uv run radon mi backend/src/zebu/ -nb

# Type coverage
uv run pyright --stats backend/src/zebu/

# Security scan
uv run bandit -r backend/src/zebu/

# Dependency vulnerabilities
uv run pip-audit
```

### TypeScript Frontend
```bash
# Bundle analysis
cd frontend
npm run build -- --stats
npx vite-bundle-visualizer

# Type coverage
npx type-coverage

# Complexity
npx complexity-report -f src/**/*.{ts,tsx}

# Unused exports
npx ts-prune
```

### Cross-Cutting
```bash
# Dependency graphs
npx madge --circular backend/src/
npx madge --circular frontend/src/

# Dead code
npx deadfile
```

## Specific Areas to Investigate

### 1. Transaction Handling Patterns
Check if transaction creation is consistent across all commands:
- CreatePortfolio, Deposit, Withdraw, Buy, Sell
- Is there duplication that could be extracted?
- Could we have a TransactionFactory?

### 2. DTO Conversion
Look at entity → DTO conversions:
- Are patterns consistent?
- Too much boilerplate?
- Could we use a library (Pydantic, TypeScript mappers)?

### 3. Error Messages
Audit all error messages:
- User-friendly?
- Consistent format?
- Include enough context?
- Localization ready?

### 4. Money/Decimal Handling
Check Money value object usage:
- Consistently used everywhere?
- Frontend converts properly?
- No floating-point arithmetic?

### 5. Query Optimization
Check all database queries:
- Proper indexes?
- N+1 queries?
- Eager vs lazy loading appropriate?

### 6. Frontend Data Flow
Trace a transaction from UI to DB and back:
- How many layers?
- Any unnecessary transformations?
- Cache invalidation working?

## Success Criteria

### Assessment Complete
- [ ] All 6 assessment areas analyzed
- [ ] Report generated with findings
- [ ] Priority matrix created
- [ ] Top 10 issues identified
- [ ] Effort estimates provided

### Quality Standards
- [ ] No architectural violations found
- [ ] Test coverage targets met or improvement plan exists
- [ ] No critical security issues
- [ ] Performance acceptable for MVP

### Documentation
- [ ] Assessment report committed
- [ ] Refactoring tasks created
- [ ] BACKLOG.md updated
- [ ] README improvements identified

## Constraints

### Do NOT Refactor Yet
This task is **assessment only**. Don't make code changes except:
- Adding comments/documentation
- Creating task specifications
- Updating BACKLOG.md

Actual refactoring will be separate tasks.

### Focus on Impact
Prioritize issues by:
1. **Blocking** - Will prevent Phase 2 features
2. **Painful** - Currently causing developer friction
3. **Risky** - Could cause bugs or security issues
4. **Wasteful** - Significant duplication or inefficiency

### Be Pragmatic
Remember this is an MVP. Some "imperfections" are acceptable:
- No need for 100% test coverage
- Some duplication is OK if isolated
- Optimization can wait until needed
- Perfect architecture isn't the goal

## Timeline
**Estimated: 3-4 hours**
- Analysis: 2 hours
- Report Writing: 1 hour
- Task Creation: 1 hour

## Next Steps After This Task
1. Review assessment report with team
2. Prioritize refactoring tasks
3. Execute P1 improvements before Phase 2
4. Schedule P2/P3 improvements in future sprints

## References
- Clean Architecture (Robert Martin)
- Refactoring (Martin Fowler)
- Modern Software Engineering (Dave Farley)
- Domain-Driven Design (Eric Evans)
