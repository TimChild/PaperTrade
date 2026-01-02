# Orchestrator Procedure: Run QA Validation

**Last Updated**: January 2, 2026
**Purpose**: Guide orchestrator through initiating comprehensive E2E quality assurance testing

## Overview

This procedure outlines how the orchestrator should trigger and manage a comprehensive QA validation session using the QA agent. This is a high-level quality check to ensure the application works correctly from a user's perspective.

## When to Run QA Validation

### Regular Cadence
- **Weekly**: As part of routine quality maintenance
- **Pre-Release**: Before any production deployment
- **Post-Integration**: After merging 3+ significant PRs

### Event-Triggered
- After major refactoring or architecture changes
- When multiple features merged in short timespan
- After critical bug fixes (regression testing)
- When user-reported issues suggest broader problems
- Before demonstrating to stakeholders

### Signs QA is Needed
- Multiple recent PRs affecting same areas
- Unclear integration status between features
- Long time since last comprehensive test
- New deployment environment being validated

## Prerequisites

Before initiating QA validation, verify:
1. ✅ All services can start successfully
2. ✅ Recent changes merged to main branch
3. ✅ No known critical blockers in current build
4. ✅ Playwright MCP tools available
5. ✅ Database migrations up to date

## Procedure

### Step 1: Assess Current State

Check recent activity and open PRs:

```bash
# Check what's been merged recently
git log --oneline --since="7 days ago" | head -20

# Check open PRs
gh pr list --state open

# Check for known issues
cat BACKLOG.md | grep -A 3 "Critical\|High Priority"
```

**Decision Point**:
- If critical blockers exist → Fix them first
- If environment unstable → Stabilize before QA
- Otherwise → Proceed to Step 2

### Step 2: Prepare QA Task

The reusable QA task template is at: [`agent_tasks/reusable/e2e_qa_validation.md`](../agent_tasks/reusable/e2e_qa_validation.md)

**Option A: Use Template Directly** (simple QA run)
```bash
gh agent-task create --custom-agent qa -F agent_tasks/reusable/e2e_qa_validation.md
```

**Option B: Create Customized Task** (specific focus areas)

If you need to customize the QA scope, create a specific task file:

```bash
# Create dated task referencing reusable template
cat > agent_tasks/042_qa-validation-post-pr-merges.md << 'EOF'
# QA Validation - Post PR Merges #47-49

**Priority**: High
**Agent**: qa
**Context**: After merging Docker infrastructure (#47), $NaN fixes (#48), and SQLAlchemy deprecations (#49)

## Objective

Execute comprehensive E2E QA testing focusing on:
1. Docker containerization doesn't break functionality
2. Price display fallbacks working correctly
3. No regressions from SQLAlchemy migration

## Instructions

Follow the standard QA validation procedure: `agent_tasks/reusable/e2e_qa_validation.md`

**Additional Focus Areas**:
- Verify price fallbacks show asterisk and tooltip
- Test rate limiting scenarios (expect 503, should handle gracefully)
- Check for any new database-related errors

**Expected Issues**:
- Rate limiting may cause 503 errors (this is expected behavior)
- Cache source attribution test still failing (Task #041, low priority)

Report all findings in standard format.
EOF

# Create agent task
gh agent-task create --custom-agent qa -F agent_tasks/042_qa-validation-post-pr-merges.md
```

### Step 3: Monitor QA Execution

The QA agent will:
1. Start backend and frontend services
2. Execute all test scenarios via Playwright
3. Document findings in `agent_progress_docs/`
4. Create follow-up tasks for critical issues
5. Clean up services

**Typical Duration**: 30-45 minutes

**What to Watch For**:
- Agent getting stuck (may need help with Playwright refs)
- Rate limiting from Alpha Vantage (expected, should handle gracefully)
- Service startup failures (database/Redis not running)

### Step 4: Review QA Report

Once the QA agent completes, review the test report in `agent_progress_docs/`:

```bash
# Find the latest QA report
ls -lt agent_progress_docs/ | grep qa | head -1

# Read the report
cat agent_progress_docs/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md
```

**Look for**:
- Summary table with pass/fail/warning counts
- Severity assessment of failures
- Evidence (screenshots, logs, console errors)
- Recommended action items

### Step 5: Triage Findings

Categorize findings by severity and plan responses:

#### Critical Issues (Application Unusable)
- **Action**: Stop all other work, create P0 task immediately
- **Example**: Cannot create portfolios, all trades fail
- **Timeline**: Fix within hours

```bash
# Example: Create critical fix task
gh agent-task create --custom-agent backend-swe \
  --title "P0: Fix trade execution 503 error" \
  -F agent_tasks/043_fix-trading-503-error.md
```

#### High Issues (Major Feature Impaired)
- **Action**: Create high-priority task, address before next release
- **Example**: Some trades fail, intermittent errors
- **Timeline**: Fix within 1-2 days

#### Medium Issues (UX Affected)
- **Action**: Add to backlog or create task if simple fix
- **Example**: Confusing error messages, slow loading
- **Timeline**: Fix in next sprint

#### Low Issues (Cosmetic)
- **Action**: Add to BACKLOG.md for future improvement
- **Example**: Minor layout issues, color inconsistencies
- **Timeline**: When convenient

### Step 6: Create Follow-up Tasks

For each critical/high issue, the QA agent should have created a task. Verify and assign:

```bash
# Check tasks created by QA agent
ls -lt agent_tasks/ | head -10

# Assign to appropriate agent
# (QA agent should suggest which agent in the task)
gh agent-task create --custom-agent backend-swe -F agent_tasks/043_fix-issue.md
```

### Step 7: Update Project Tracking

Document the QA session:

```markdown
# In PROGRESS.md

## Quality Assurance - [DATE]

**QA Report**: agent_progress_docs/YYYY-MM-DD_HH-MM-SS_e2e-qa-report.md

**Summary**: Comprehensive E2E testing after PRs #47, #48, #49

**Results**:
- 7 scenarios tested
- 5 passed, 1 failed (critical), 1 warning (medium)
- Created Task #043 (trading 503 error) - P0
- Created Task #044 (improve error messages) - Medium

**Next Steps**:
- Fix critical trading issue (Task #043)
- Rerun QA after fix to verify
- Schedule next QA session for [DATE]
```

### Step 8: Schedule Next QA

Determine when to run QA again:
- **After Critical Fix**: Immediately (regression test)
- **Regular Cadence**: Weekly or bi-weekly
- **Before Release**: Always

```markdown
# Add to TODO or calendar
- [ ] Run QA validation on [DATE] (weekly check)
- [ ] Run QA validation after Task #043 complete (regression test)
```

## Example Workflow

### Scenario: Post-Integration QA

**Context**: Just merged PRs #47 (Docker), #48 ($NaN fixes), #49 (SQLAlchemy migration)

**Steps**:

1. **Assess**: Review what changed
   ```bash
   gh pr view 47 48 49 --json title,body
   ```

2. **Decide**: These are significant infrastructure and bug fixes → QA needed

3. **Customize Task**:
   ```bash
   # Create specific task highlighting these PRs
   cat > agent_tasks/042_qa-post-infrastructure-changes.md << 'EOF'
   # QA Validation: Post-Infrastructure Changes

   **Agent**: qa
   **Priority**: High
   **Context**: After Docker (#47), $NaN fixes (#48), SQLAlchemy (#49)

   Execute standard QA: agent_tasks/reusable/e2e_qa_validation.md

   Focus areas:
   - Docker doesn't break anything
   - Price fallbacks working
   - No DB migration issues
   EOF
   ```

4. **Execute**:
   ```bash
   gh agent-task create --custom-agent qa -F agent_tasks/042_qa-post-infrastructure-changes.md
   ```

5. **Wait**: Agent runs tests (30-45 min)

6. **Review**: Check report
   ```bash
   cat agent_progress_docs/2026-01-02_14-30-00_qa-report.md
   ```

7. **Triage**:
   - Found: Trading returns 503 (critical)
   - Found: $NaN still appears sometimes (warning, may be fixed)
   - Action: Create Task #043 for 503 error
   - Action: Verify $NaN issue separately

8. **Follow-up**:
   ```bash
   # Assign critical fix
   gh agent-task create --custom-agent backend-swe -F agent_tasks/043_fix-trading-503.md

   # Update PROGRESS.md
   # Schedule regression test after fix
   ```

## Common Issues

### Issue: QA Agent Can't Start Services

**Symptom**: Backend or frontend fails to start

**Debug**:
```bash
# Check Docker services
docker ps

# Check logs
tail -100 temp/backend.log
tail -100 temp/frontend.log

# Try manually
task dev:backend
task dev:frontend
```

**Resolution**: Fix environment issues before retrying QA

### Issue: Playwright Tools Not Available

**Symptom**: QA agent can't use browser automation

**Debug**:
Check `.vscode/mcp.json` for Playwright MCP configuration

**Resolution**:
1. Verify MCP server configured
2. Restart VS Code if needed
3. Run `mcp_microsoft_pla_browser_install` if browser not installed

### Issue: All Tests Timing Out

**Symptom**: QA can't connect to services

**Debug**:
```bash
curl http://localhost:8000/health
curl http://localhost:5173/
```

**Resolution**: Services not running, check startup logs

### Issue: Rate Limiting Blocking Tests

**Symptom**: All trades return 503

**Expected**: This is normal with Alpha Vantage free tier (5 calls/min)

**Resolution**:
- Wait between tests
- Use known cached tickers (IBM)
- Note in QA report as expected behavior
- May want to implement better retry logic (create task)

## Best Practices

### 1. Don't Over-Test
- Focus on critical user paths
- Skip low-priority scenarios if time-constrained
- Depth over breadth for important features

### 2. Context is Key
- Tell QA agent what changed recently
- Highlight areas of concern
- Reference related PRs and tasks

### 3. Trust but Verify
- QA agent should create tasks for issues
- Orchestrator should verify severity assessment
- Don't blindly merge fixes without understanding

### 4. Regression Testing
- After fixing critical bugs, rerun QA
- Verify fix works AND didn't break other things
- Document regression test results

### 5. Continuous Improvement
- If QA finds same issues repeatedly → improve tests
- If scenarios missing → update reusable template
- If environment setup tedious → automate more

## Integration with CI/CD

**Current State**: Manual QA via agent

**Future Enhancement**: Automated Playwright tests in CI
- Convert QA scenarios to automated test suite
- Run on every PR
- QA agent focuses on exploratory testing
- See: `orchestrator_procedures/e2e_validation.py` (WIP)

## Metrics to Track

Over time, track these QA metrics:

| Metric | Target | Purpose |
|--------|--------|---------|
| Pass Rate | > 90% | Overall quality health |
| Critical Failures | 0 | Release readiness |
| Time to Fix Critical | < 24 hrs | Response capability |
| Regression Rate | < 5% | Code stability |
| QA Session Duration | 30-45 min | Efficiency |

## References

- [agent_tasks/reusable/e2e_qa_validation.md](../agent_tasks/reusable/e2e_qa_validation.md) - Reusable QA task template
- [.github/agents/qa.md](../.github/agents/qa.md) - QA Agent definition
- [orchestrator_procedures/playwright_e2e_testing.md](playwright_e2e_testing.md) - Technical Playwright guide
- [AGENT_ORCHESTRATION.md](../AGENT_ORCHESTRATION.md) - Agent coordination guide

## Checklist

Use this checklist when running QA:

```markdown
- [ ] Assessed recent changes and current state
- [ ] Verified prerequisites (services, MCP tools)
- [ ] Created or referenced QA task with context
- [ ] Initiated QA agent via gh agent-task
- [ ] Monitored execution (30-45 min)
- [ ] Reviewed QA report in agent_progress_docs/
- [ ] Triaged findings by severity
- [ ] Created follow-up tasks for critical/high issues
- [ ] Updated PROGRESS.md with QA summary
- [ ] Scheduled next QA session or regression test
- [ ] Documented lessons learned (if any)
```
