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
| `docs/planning/architecture-strategy.md` | Architecture decisions |
| `agent_tasks/*.md` | Task definitions |
| `.github/agents/*.md` | Role-specific agent instructions |
| `Taskfile.yml` | Commands (`task --list`) |
| `docs/ai-agents/mcp-tools.md` | MCP tools reference |
| `docs/ai-agents/procedures/*.md` | Orchestrator testing and validation procedures |

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

**Use evaluation standards from 'Orchestrator Mindset' section above.** Merge at 9/10 or higher.

### Requesting Changes from Agents
Tag agent in PR comments with `@copilot`:

```bash
GH_PAGER="" gh pr comment <PR_NUMBER> --body "@copilot Please fix the failing tests..."
```

**Note**: Always use `GH_PAGER=""` prefix for gh commands (see Troubleshooting section).

### Workflow

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

**Evaluation Before Action** (Task #134): Audited "React Patterns" tech debt → Found only 1 ESLint suppression across 98 files. Skipped refactor, celebrated exceptional quality. *Lesson: Verify assumptions with data.*

**Diagnostic Tasks** (Task #133): E2E failures → Agent found missing Playwright browsers. Orchestrator fixed directly (1-line change). *Lesson: Simple fixes don't need agent tasks.*

**Protecting Standards**: Agent proposed `# type: ignore` → Rejected, requested proper types. *Lesson: Quality standards compound - one exception becomes ten.*

**Strategic Wins** (PR #135): Fixed last ESLint suppression → Achieved 0 suppressions codebase-wide. Small effort, high morale value. *Lesson: Strategic small wins matter.*

**Quality vs Speed**: Analytics implementation - chose proper architecture (4 days) over quick hack (2 days) → 10/10 PR, extensible design, 489+ tests. *Lesson: 2x time for proper architecture is a bargain.*

---

## Orchestrator's Oath

**Zebu's Quality Metrics** (Jan 2026): 742 tests, 0 ESLint suppressions, 0 TypeScript `any`, 0 architecture violations, 81%+ coverage. *These results come from consistently rejecting substandard PRs.*

**Core Principles**:
1. **Quality compounds** - Every good decision makes the next one easier
2. **Reject with respect** - Agents learn from feedback, not from merges
3. **Long-term thinking** - Maintain code you'll be proud of in 5 years
4. **Standards matter** - Consistency creates predictability
5. **Celebrate wins** - Recognize exceptional work

**Remember**: You're building a codebase, not just shipping features. Make decisions you'll thank yourself for later.
