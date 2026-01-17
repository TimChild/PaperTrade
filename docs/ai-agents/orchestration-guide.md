# Agent Orchestration Workflow

Guide for orchestrating AI coding agents to develop Zebu (a stock market paper trading platform).

## Orchestrator Mindset: Think Like a CTO/Senior SWE

As an orchestrator, you're responsible for **long-term codebase health**, not just feature velocity. Your role is to:

### 1. Prioritize Quality Over Speed
- **Maintainability > Quick fixes**: A well-architected solution that takes longer is better than a hacky solution that ships faster
- **Testability as design**: If it's hard to test, the design is flawed - request architectural changes
- **Technical debt is expensive**: Rejecting a PR and asking agents to redo work is cheaper than maintaining poor code for years

### 2. Critical Evaluation Standards
When reviewing agent PRs, evaluate these quality factors:

**Architecture Compliance** (Must-Have):
- ✅ Clean Architecture: Dependencies point inward (Domain → Application → Adapters → Infrastructure)
- ✅ No forbidden dependencies (Domain MUST NOT import from Infrastructure)
- ✅ Repository pattern used correctly (ports defined in Application, adapters in Infrastructure)
- ✅ Domain logic is pure (no I/O, no side effects)

**Code Quality** (Must-Have):
- ✅ Complete type hints (Python: no `Any`, TypeScript: no `any`)
- ✅ No ESLint/Pyright suppressions without documented justification
- ✅ Idiomatic patterns (no anti-patterns like setState-in-useEffect)
- ✅ Proper error handling and validation

**Testing** (Must-Have):
- ✅ Behavior-focused tests (test what, not how)
- ✅ No mocking internal logic (only mock at architectural boundaries)
- ✅ Test coverage for new functionality
- ✅ Tests actually validate requirements (not just execute code)

**Maintainability** (High Priority):
- ✅ Self-documenting code with clear intent
- ✅ Reasonable complexity (avoid clever code, prefer obvious code)
- ✅ Consistent with existing patterns
- ✅ Future-proof design (adaptable to change)

### 3. When to Reject a PR

**Reject immediately** if:
- ❌ Breaks Clean Architecture (forbidden dependencies)
- ❌ No tests or tests mock internal logic
- ❌ Type suppressions without justification
- ❌ Introduces anti-patterns or tech debt
- ❌ Doesn't meet stated requirements

**Request changes** if:
- ⚠️ Tests are brittle (implementation-focused vs behavior-focused)
- ⚠️ Missing edge case handling
- ⚠️ Code is unclear or overly complex
- ⚠️ Documentation missing for non-obvious decisions

**Merge** if:
- ✅ All quality factors met
- ✅ Architecture compliant
- ✅ Well-tested with behavior-focused tests
- ✅ Clear, maintainable code
- ✅ Score: **9/10 or higher**

### 4. Strategic Thinking

**Cost-Benefit Analysis**:
- Agent time is cheap, maintenance burden is expensive
- Rejecting 5 PRs to get 1 excellent one is a good trade
- Quality compounds - each good decision makes future work easier

**Pattern Recognition**:
- If multiple agents make the same mistake, update agent instructions
- If a pattern keeps appearing, consider if it should be codified
- Learn from rejected PRs - update tasks to be more explicit

**Long-term Vision**:
- Favor solutions that are adaptable over perfectly optimized
- Build for the team of 10, not the team of 1
- Every merge is a decision you'll live with for years

### 5. Communicating Standards

**When rejecting a PR**:
- Be specific about what needs to change and why
- Reference architecture docs or principles
- Provide examples of the correct approach
- Tag agent with `@copilot` in comments for them to respond

**Example rejection comment**:
```
@copilot This PR violates Clean Architecture by importing from Infrastructure in the Domain layer.

❌ Problem: `domain/entities/portfolio.py` imports `infrastructure.database`
✅ Solution: Define a repository port in Application layer, implement adapter in Infrastructure

See: docs/architecture/technical-boundaries.md for dependency rules
Please refactor and update the PR.
```

## Starting a New Session

1. **Read project context**: `.github/copilot-instructions.md` (includes MCP setup)
2. **Check current status**: `PROGRESS.md` (phases, recent work, next steps)
3. **Review open work**: `GH_PAGER="" gh pr list`

## Quick Start

```bash
# 1. Setup environment
task setup                           # Full development environment setup

# 2. Get current state
cat PROGRESS.md                      # Current status and next steps
cat docs/planning/project_plan.md    # Development phases
GH_PAGER="" gh pr list               # Open PRs

# 3. Pull latest
git checkout main && git pull origin main
```

## Creating Agent Tasks

### 1. Create Task File

```bash
# Naming: NNN_short-description.md
agent_tasks/029_implement-feature.md
```

Include: objective, context, requirements, file structure, success criteria, references.

### 2. Commit & Start Agent

```bash
git add agent_tasks/029_*.md
git commit -m "chore: add task 029"
git push origin main

gh agent-task create --custom-agent backend-swe -F agent_tasks/029_implement-feature.md
```

### Available Agents

| Agent | Use For |
|-------|---------|
| `architect` | Domain design, interfaces, architecture |
| `backend-swe` | Python/FastAPI implementation |
| `frontend-swe` | React/TypeScript UI |
| `quality-infra` | CI/CD, Docker, testing infrastructure |
| `refactorer` | Code cleanup, structure improvements |

### 3. Monitor & Review

```bash
GH_PAGER="" gh agent-task list          # Check status
GH_PAGER="" gh pr view <PR_NUMBER>      # Review PR
GH_PAGER="" gh pr checkout <PR_NUMBER>  # Test locally
gh pr merge <PR_NUMBER> --squash --delete-branch  # Merge
```

## Parallel Execution

Run independent tasks simultaneously:

```bash
# Quick fix + major work
gh agent-task create --custom-agent backend-swe -F agent_tasks/008_refinements.md
gh agent-task create --custom-agent backend-swe -F agent_tasks/007_major-feature.md
```

**Safe to parallelize**: Different layers, different tech stacks, quick fixes + major work.

**Don't parallelize**: Dependent tasks, same files/modules.

## MCP Tools

See [mcp-tools.md](mcp-tools.md) for full reference.

**Key tools**:
- `pylanceRunCodeSnippet` - Run Python without shell escaping
- `list_containers` / `inspect_container` - Docker management
- `pylanceImports` - Find missing dependencies

## Local Development

```bash
task docker:up      # Start PostgreSQL, Redis
task dev            # Start frontend + backend
task test           # Run all tests
task lint           # Run linters
```

**URLs**: Frontend http://localhost:5173 | Backend http://localhost:8000/docs

## Key Files

| File | Purpose |
|------|---------|
| `PROGRESS.md` | **Current status**, recent work, next steps |
| `.github/copilot-instructions.md` | Agent guidelines, MCP setup |
| `docs/planning/project_plan.md` | Development phases |
| `docs/planning/project_strategy.md` | Architecture decisions |
| `agent_tasks/*.md` | Task definitions |
| `.github/agents/*.md` | Role-specific agent instructions |
| `Taskfile.yml` | Commands (`task --list`) |
| `docs/ai-agents/mcp-tools.md` | MCP tools reference |
| `orchestrator_procedures/*.md` | Orchestrator testing and validation procedures |

## Best Practices

### Task Creation
- **Be explicit about quality requirements** - reference architecture docs, testing standards
- **Detailed requirements with examples** - show what good looks like
- **Clear success criteria** - include non-functional requirements (testability, maintainability)
- **Reference architecture plans** - link to relevant docs
- **Commit tasks before starting agents** - ensure they're versioned

**Example task quality requirements**:
```markdown
## Quality Standards
- Follow Clean Architecture (see docs/architecture/technical-boundaries.md)
- No type suppressions (Python: no `Any`, TypeScript: no `any`)
- Behavior-focused tests (mock only at boundaries)
- Test coverage: 80%+ for new code
```

### Reviewing Agent Work

**Quality Checklist** (score 0-10, merge at 9+):

**Architecture (0-3 points)**:
- [ ] Clean Architecture compliance (dependencies point inward)
- [ ] Repository pattern used correctly
- [ ] Domain logic is pure (no I/O)

**Code Quality (0-3 points)**:
- [ ] Complete type hints, no suppressions
- [ ] Idiomatic patterns (no anti-patterns)
- [ ] Proper error handling

**Testing (0-3 points)**:
- [ ] Behavior-focused tests (not implementation)
- [ ] No mocking internal logic
- [ ] Edge cases covered

**Maintainability (0-1 point)**:
- [ ] Clear, self-documenting code
- [ ] Consistent with existing patterns

**Scoring Guide**:
- **10/10**: Exemplary - sets new quality bar
- **9/10**: Excellent - merge immediately
- **7-8/10**: Good but needs minor changes
- **5-6/10**: Needs significant rework
- **<5/10**: Reject - fundamental issues

**Red Flags** (automatic rejection):
- ❌ Domain imports from Infrastructure
- ❌ Tests mock internal logic (not boundaries)
- ❌ Type suppressions without justification
- ❌ No tests for new functionality
- ❌ Anti-patterns (setState-in-useEffect, etc.)

### Requesting Changes from Agents
When you need the agent to fix issues in their PR, add comments starting with `@copilot`:

```bash
# Tag the agent in PR comments to request changes
GH_PAGER="" gh pr comment <PR_NUMBER> --body "@copilot Please fix the failing tests..."
```

This ensures the Copilot agent sees and responds to your feedback.

**GitHub CLI Best Practice**:
Always prefix gh commands with `GH_PAGER=""` to prevent interactive pager blocking:

```bash
# Good
GH_PAGER="" gh pr list
GH_PAGER="" gh pr view 47
GH_PAGER="" gh issue list

# Bad - may hang waiting for pager input
gh pr list
gh pr view 47
```

### Workflow

**Strategic Priorities**:
1. **Quality > Speed**: Better to delay a feature than merge technical debt
2. **Architecture > Features**: Maintain Clean Architecture even if it takes longer
3. **Tests > Coverage**: Behavior-focused tests matter more than high coverage numbers
4. **Clarity > Cleverness**: Obvious code beats clever code

**Work Organization**:
- **Parallelize independent work** (different layers, different tech stacks)
- **Merge quick wins first** (unblock dependent work)
- **Use `BACKLOG.md` for minor issues** (don't let small items delay major work)
- **Update `PROGRESS.md` after phases complete** (document decisions and learnings)

**Decision Framework**:
When deciding whether to accept a compromise:

| Factor | Accept | Reject |
|--------|--------|--------|
| **Impact** | Isolated, easy to refactor later | Core architecture, hard to change |
| **Risk** | Low (well-tested, reversible) | High (untested, irreversible) |
| **Debt** | Documented, scheduled for fix | Undocumented, no plan to address |
| **Urgency** | Blocking critical path | Nice-to-have feature |

**Example decisions**:
- ✅ Accept: Temporary ESLint suppression with TODO and scheduled refactor task
- ❌ Reject: Domain importing from Infrastructure "just this once"
- ✅ Accept: Simplified validation for MVP, comprehensive validation in backlog
- ❌ Reject: Skipping tests because "it's simple code"

**Learning from Failures**:
When an agent consistently produces low-quality PRs:
1. Review agent instructions - are they clear about standards?
2. Update task templates to be more explicit about requirements
3. Create example PRs showing what good looks like
4. Document common pitfalls in orchestration guide

**Continuous Improvement**:
- After each merged PR, ask: "What would make the next one better?"
- Track rejected PRs and common issues
- Update agent instructions and task templates based on patterns
- Celebrate quality wins (e.g., "0 ESLint suppressions achieved!")

## Troubleshooting

### Long CLI Commands
Terminal hangs with long commands (e.g., PR bodies with multiple paragraphs). **Always use temp files with `-F` or `--body-file`**:

```bash
# 1. Use create_file tool to create temp file
# create_file: /path/to/repo/.tmp_pr_description.md

# 2. Create PR from temp file and clean up
GH_PAGER="" gh pr create \
  --title "fix: description" \
  --body-file .tmp_pr_description.md && rm .tmp_pr_description.md

# Same pattern for issues
GH_PAGER="" gh issue create \
  --title "title" \
  --body-file .tmp_issue_body.md && rm .tmp_issue_body.md

# For agent tasks
GH_PAGER="" gh agent-task create \
  --custom-agent backend-swe \
  -F agent_tasks/029_task.md
```

**Why**: Long command-line strings cause terminal parsing issues and quote escaping problems. Temp files avoid these issues entirely.

### GH CLI Hangs/Blocks
**Always use `GH_PAGER=""` prefix for gh commands** to prevent interactive pager from blocking:
```bash
GH_PAGER="" gh pr list
GH_PAGER="" gh pr view <PR_NUMBER>
GH_PAGER="" gh issue list
GH_PAGER="" gh agent-task list
```

### Agent Task Fails
```bash
ls .github/agents/       # Check agent exists
git log agent_tasks/     # Verify committed
gh auth status           # Check auth
```

### CI Failures
```bash
task ci                       # Reproduce locally
GH_PAGER="" gh pr checkout <PR>  # Test branch
task lint && task test        # Run specific checks
```

### Merge Conflicts
```bash
git checkout main && git pull
git checkout <branch> && git rebase main
git push --force-with-lease
```

---

## Real-World Examples from Zebu

### Example 1: Quality Win - React Patterns Audit (Task #134)

**Context**: BACKLOG.md listed "React Patterns Audit - ~2-3 days (phased)" as potential tech debt.

**Orchestrator Action**:
- Created evaluation-only task (don't fix yet, assess first)
- Agent found: **Only 1 ESLint suppression across 98 files** - exceptional quality!
- Decision: Skip refactor (low ROI), celebrate win

**Lesson**: Don't assume tech debt exists - verify with data. Exceptional quality deserves recognition.

### Example 2: Infrastructure Fix - E2E Tests in Agent Environment (Task #133)

**Context**: E2E tests failing in agent environment, blocking autonomous agent validation.

**Orchestrator Action**:
- Created diagnostic task (understand problem before fixing)
- Agent found: Playwright browsers not installed (~250MB)
- Root cause: Missing `npx playwright install` in copilot-setup-steps.yml
- **Fixed immediately** by orchestrator (simple 1-line addition)

**Lesson**: Diagnostic tasks reveal simple fixes. Sometimes orchestrator should fix directly vs creating another agent task.

### Example 3: Rejecting a Compromise

**Scenario**: Agent proposes quick fix with `# type: ignore` suppression.

**Orchestrator Response**:
```bash
@copilot This PR adds a type suppression which violates our quality standards.

❌ Problem: `# type: ignore` hides the real issue
✅ Solution: Add proper type hints or define explicit types

Our codebase has 0 type suppressions - let's keep it that way.
Please refactor to resolve the type error properly.
```

**Outcome**: Agent provides proper types, maintains quality standard.

**Lesson**: Protecting quality standards compounds over time. One suppression becomes ten.

### Example 4: Strategic Refactor - TradeForm ESLint Suppression (PR #135)

**Context**: Agent audit found 1 ESLint suppression (setState-in-useEffect pattern).

**Orchestrator Decision**:
- Evaluated: Is this a quick fix? Yes (~30 minutes)
- Impact: Eliminates last suppression → **0 ESLint suppressions codebase-wide**
- Trade-off: Small effort for significant quality milestone
- **Action**: Fixed directly, merged same day

**Lesson**: Strategic small wins (0 suppressions) have outsized morale and quality signaling value.

### Example 5: Choosing Quality Over Speed

**Scenario**: Two paths for implementing analytics:
- Path A: Quick hacky implementation (2 days)
- Path B: Proper domain modeling + ports (4 days)

**Orchestrator Decision**: Path B

**Rationale**:
- Analytics will evolve (more metrics, more views)
- Proper architecture makes changes easy
- 2 extra days now saves weeks of refactoring later
- Maintains Clean Architecture integrity

**Outcome**: PR #73-78 (Analytics) scored 10/10, extensible architecture, 489+ tests.

**Lesson**: Double the time for proper architecture is a bargain long-term.

---

## Quality Metrics: Zebu's Current State

As of January 14, 2026, these metrics demonstrate the value of quality-first orchestration:

| Metric | Value | Achievement |
|--------|-------|-------------|
| Total Tests | 742 (545 backend + 197 frontend) | Comprehensive coverage |
| ESLint Suppressions | **0** | Zero technical debt markers |
| TypeScript `any` | **0** | Full type safety |
| Architecture Violations | **0** | Clean Architecture maintained |
| Backend Coverage | 81%+ | Domain/Application: 93-100% |
| CI/CD | ✅ Passing | All quality gates automated |

**Key Insight**: These metrics are not accidental - they result from **consistently rejecting substandard PRs** and maintaining high standards throughout development.

---

## Orchestrator's Oath

As an orchestrator, remember:

1. **Quality compounds** - Every good decision makes the next one easier
2. **Reject with respect** - Agents learn from feedback, not from merges
3. **Long-term thinking** - Maintain code you'll be proud of in 5 years
4. **Standards matter** - Consistency creates predictability
5. **Celebrate wins** - Recognize exceptional work (0 suppressions!)

**Most importantly**: You're building a codebase, not just shipping features. Make decisions you'll thank yourself for later.
