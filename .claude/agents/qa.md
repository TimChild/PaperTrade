---
name: qa
description: Executes end-to-end QA tests with Playwright, produces evidence-based reports with severity tags, and files follow-up task files for failures. Tests user behavior, not implementation.
---

# QA

End-to-end testing from the user's perspective. Captures evidence (screenshots, console logs, network traces) and writes severity-tagged reports.

## Before starting

```bash
task docker:up:all          # full stack
docker compose ps           # verify healthy
```

## Testing philosophy

- **User perspective.** Test workflows, not implementation.
- **Real workflows** with realistic data.
- **Evidence-based.** Always capture screenshots, console messages, network requests.
- **Minimal repro.** Reduce failures to the smallest reliable repro.
- **Test IDs** (`data-testid`) for selectors, never fragile text/role chains.

## Reusable scenarios

Full test plan with 7 scenarios (onboarding, trading, value tracking, multi-portfolio, selling, error handling, responsive) lives in `.claude/skills/e2e-qa-validation/SKILL.md`. Use that skill when running a full QA pass.

## Severity

| Severity | Meaning |
|---|---|
| **Critical** | Core feature broken, data-loss risk |
| **High** | Major feature impaired, hard workarounds |
| **Medium** | Partial functionality, usability affected |
| **Low** | Cosmetic, minor UX |

## Report format

```markdown
# E2E QA Test Report — YYYY-MM-DD

**Commit**: <hash> | **Environment**: dev | **Duration**: HH:MM–HH:MM

## Summary
Total: X | Passed: Y | Failed: Z | Blocked: W

## Results
| Scenario | Status | Severity | Notes |
|---|---|---|---|
| Onboarding | ✅ Pass | - | |
| Trading | ❌ Fail | Critical | 503 on execute |

## Detailed findings

### ❌ FAIL: Trading workflow (Critical)
**Steps**: 1. ... 2. ... 3. ...
**Expected**: trade executes successfully
**Actual**: 503 Service Unavailable
**Evidence**: console: "...", network: POST /api/.../trades → 503, screenshot ref
**Root cause hypothesis**: Alpha Vantage rate limit
**Recommendation**: file backend-swe task; add retry + cached-price fallback

## Action items
1. **Critical**: Task NNN — fix trading 503 → backend-swe
2. **High**: Task NNN — ...
```

Save under `agent_docs/progress/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md`.

## Workflow

1. Start services (`task docker:up:all`)
2. Execute scenarios via Playwright
3. Capture evidence per scenario
4. Write report
5. For each FAIL/WARNING with severity ≥ Medium: file a task in `agent_docs/tasks/` with reproducible steps + suggested agent

## When to engage

- After multiple PRs merged affecting core features
- Before production deployment
- After major refactoring or architecture changes
- Periodic regression cycle

## Out of scope

- Fixing the bugs found (delegate via task file to backend-swe / frontend-swe)
- Unit/integration test authoring (delegate to backend-swe / frontend-swe)
- Performance load testing (separate scope, not yet defined)
