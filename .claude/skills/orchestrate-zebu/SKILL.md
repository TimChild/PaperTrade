---
name: orchestrate-zebu
description: Orchestrator playbook for Zebu — PR review criteria, parallel-execution safety rules, task scoping, fix-forward pattern. Use when coordinating multi-agent work or reviewing PRs against the project's quality bar.
---

# Orchestrate Zebu

The CTO-mindset playbook. Use when reviewing PRs, scoping tasks for specialist agents, or coordinating parallel work.

## Mindset

You're responsible for **long-term codebase health**, not just shipping speed. Quality compounds — each good decision makes the next one easier; each compromise makes the next worse.

- **Maintainability beats velocity.** A well-designed solution that takes longer wins over a hack that ships sooner.
- **Testability is a design property.** Hard to test = flawed design. Push back.
- **Tech debt is expensive.** Rejecting 5 PRs to merge 1 excellent one is a good trade.

## PR review criteria

### Must-have (any failure = reject or request-changes)

**Architecture compliance** (see `docs/architecture/principles.md`):

- Dependencies point inward (Domain → Application → Adapters → Infrastructure)
- No forbidden imports (Domain MUST NOT import Infrastructure)
- Repository ports defined in Application; adapters in Infrastructure
- Domain logic is pure — no I/O, no side effects

**Code quality**:

- Complete type hints (Python: no `Any`; TypeScript: no `any`)
- No type-checker / lint suppressions without a documented justification
- Idiomatic patterns (no anti-patterns like setState-in-useEffect)
- Proper error handling

**Testing**:

- Behavior-focused (test what, not how)
- Mock at architectural boundaries only — never internal logic
- Test coverage for new functionality
- Tests actually validate requirements (not just execute the code path)

### Nice-to-have (request changes if missing)

- Self-documenting names; minimal comments (only for non-obvious WHY)
- Consistent with existing patterns
- Adaptable to change (not over-engineered)

## Decision matrix

| Outcome | Trigger |
|---|---|
| **Reject** | Breaks Clean Architecture; tests mock internal logic; type suppressions without justification; introduces anti-patterns; doesn't meet stated requirements |
| **Request changes** | Brittle (implementation-focused) tests; missing edge cases; unclear/complex code; missing docs for non-obvious decisions |
| **Merge** | All must-haves met; behavior-focused tests; clear, maintainable; **9/10 or higher** |

## Communicating rejection

Be specific, reference docs, give the correct approach. Example:

> This PR violates Clean Architecture by importing from Infrastructure in the Domain layer.
>
> ❌ Problem: `domain/entities/portfolio.py` imports `infrastructure.database`
> ✅ Fix: Define a repository port in `application/ports/`, implement in `adapters/outbound/`
>
> See `docs/architecture/principles.md` for the dependency rule.

## Parallel execution — safety rules

Safe to run in parallel:

- Different layers (backend agent + frontend local agent)
- Different tech stacks
- Independent features that don't touch the same files

Don't parallelize:

- Sequential phases where later work depends on earlier decisions
- Tasks touching the same modules (merge conflicts guaranteed)
- Tasks sharing domain concepts being designed for the first time

Pattern: dispatch a remote agent for the larger backend task; use a local specialist agent for a small parallel visual fix.

## Task scoping

**Prefer fewer, larger, coherent tasks over many micro-tasks.** Agents handle 500–2000-line PRs with multiple files; PR management overhead is real.

Anti-pattern (too granular):

```
Task A: Create Strategy entity
Task B: Create BacktestRun entity
Task C: Add migrations
```

Right-sized:

```
Task: Domain entities, migrations, and repositories for backtesting
```

Rules of thumb:

- **Scope by functional area**, not file or function
- Work that **shares context** (entities that reference each other) goes to one agent
- Each agent task spec should include: quality requirements, success criteria, references

## Fix-forward pattern

When a review reveals small quality issues that don't warrant rejection:

1. Fix trivial issues (lint, formatting) on the branch yourself; push
2. For design issues, document them as **Priority 1** in the next agent task
3. The next agent fixes them before adding new functionality

Example: PR #203 used `self._snapshot_service._snapshot_repo` (private attribute access). Rather than rejecting an otherwise excellent PR, this was made Priority 1 in Phase 4.3's task. Next agent fixed it before adding new strategies.

**Don't let small issues accumulate.** Every task should leave the code slightly better.

## Operational reflexes

When evaluating an issue:

- **Verify with data before action.** Task #134 audited "React Patterns" tech debt → found only 1 ESLint suppression across 98 files. Skipped refactor, celebrated quality. *Verify assumptions before scheduling work.*
- **Diagnose before delegating.** Task #133 (E2E failures): found missing Playwright browsers — orchestrator fixed in 1 line, no agent task needed. *Simple fixes don't need agent tasks.*
- **Don't accept tech-debt creep.** Agent proposes `# type: ignore` → reject, request proper types. *One exception becomes ten.*

## Lessons compounded

- Quality compounds — every good decision makes the next easier
- Reject with respect — agents learn from feedback, not from forced merges
- Long-term thinking — maintain code you'll be proud of in 5 years
- Standards matter — consistency creates predictability
- Celebrate wins — recognize exceptional work (e.g., "0 ESLint suppressions" milestone)
