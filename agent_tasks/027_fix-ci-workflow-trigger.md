# Task 027: Fix CI Workflow Trigger on Draft PR Transition

**Created**: 2026-01-01
**Agent**: quality-infra
**Estimated Effort**: 1-2 hours
**Dependencies**: None
**Phase**: Quality Improvement

## Objective

Fix the CI workflow so that it runs when PRs transition from draft to ready-for-review status, not just on initial PR creation.

## Context

When PRs are created by agents, they start in draft mode. When the orchestrator marks them as ready (`gh pr ready <number>`), only GitGuardian security checks run - the main CI workflow (lint, test, build) does not trigger.

This prevents the orchestrator from seeing full CI results before merging, requiring local test runs instead.

### Current Behavior

```bash
# Agent creates PR in draft mode
gh agent-task create --custom-agent backend-swe -F task.md
# PR created in draft state

# Orchestrator marks as ready
gh pr ready 33
# ❌ Only GitGuardian runs, not full CI
```

### Expected Behavior

```bash
# Orchestrator marks as ready
gh pr ready 33
# ✅ Full CI workflow runs (lint, test, build, e2e)
```

## Current CI Configuration

**File**: `.github/workflows/ci.yml`

The workflow likely has a trigger like:
```yaml
on:
  pull_request:
    types: [opened, synchronize]
```

This doesn't include the `ready_for_review` event type.

**File**: `.github/workflows/pr.yml`

May have similar issues.

## Success Criteria

- [ ] CI workflow triggers when PR transitions from draft to ready
- [ ] CI still triggers on PR open and new commits
- [ ] Both `ci.yml` and `pr.yml` workflows updated (if both exist)
- [ ] Verified with a test PR (create draft, mark ready, check CI runs)
- [ ] Documentation updated if needed

## Implementation Details

### 1. Update Workflow Triggers

**Files to Modify**:
- `.github/workflows/ci.yml`
- `.github/workflows/pr.yml` (if exists)

**Add `ready_for_review` Event**:

```yaml
on:
  pull_request:
    types:
      - opened
      - synchronize
      - reopened
      - ready_for_review  # NEW: Trigger when draft → ready
```

**Optionally Exclude Draft PRs**:

If you want to avoid running CI on draft PRs entirely:

```yaml
on:
  pull_request:
    types:
      - opened
      - synchronize
      - reopened
      - ready_for_review

jobs:
  backend-checks:
    # Skip draft PRs
    if: github.event.pull_request.draft == false
    runs-on: ubuntu-latest
    # ... rest of job
```

### 2. Review All Workflow Files

Check all workflows in `.github/workflows/` for consistency:

```bash
ls -la .github/workflows/
```

Ensure all PR-triggered workflows have consistent event types.

### 3. Test the Fix

Create a test PR to verify:

```bash
# 1. Create a draft PR
gh pr create --draft --title "Test CI trigger" --body "Testing ready_for_review event"

# 2. Mark as ready
gh pr ready <PR_NUMBER>

# 3. Check CI runs
gh pr checks <PR_NUMBER>
# Should see: lint, test, build, e2e checks (not just GitGuardian)

# 4. Clean up
gh pr close <PR_NUMBER>
gh pr delete <PR_NUMBER>
```

### 4. Document the Behavior

Update documentation to reflect the workflow:

**File to Update**: `AGENT_ORCHESTRATION.md`

Add a note in the "Review and Merge" section about CI triggering when marking as ready.

## Architecture Considerations

**Clean Separation**: This is purely CI/CD configuration, no production code changes needed.

**Backward Compatibility**: Adding event types is non-breaking - existing workflows continue to work.

**Performance**: No impact - just triggers existing workflows at a different point.

## Testing Strategy

### Manual Testing

1. Create a draft PR manually
2. Mark it as ready
3. Verify all CI jobs run
4. Check job logs for correctness

### Validation

```bash
# Check workflow syntax
gh workflow list
gh workflow view ci.yml

# Test event trigger
gh api repos/TimChild/PaperTrade/actions/workflows/ci.yml
```

## Known Constraints

- GitHub Actions event types are documented here: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request
- Draft PRs can optionally be skipped using `if: github.event.pull_request.draft == false`

## Expected Outcome

After this fix, the orchestrator workflow becomes:

```bash
# 1. Agent creates PR (draft)
gh agent-task create --custom-agent backend-swe -F task.md

# 2. Orchestrator marks as ready (triggers full CI)
gh pr ready <PR_NUMBER>

# 3. Orchestrator reviews CI results
gh pr checks <PR_NUMBER>
# ✅ All checks visible

# 4. Orchestrator merges if passing
gh pr merge <PR_NUMBER> --squash --delete-branch
```

## References

- GitHub Actions PR events: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request
- Current workflow files: `.github/workflows/ci.yml`, `.github/workflows/pr.yml`
- Agent orchestration workflow: `AGENT_ORCHESTRATION.md`

## Definition of Done

- [ ] `ci.yml` updated with `ready_for_review` event type
- [ ] `pr.yml` updated (if exists)
- [ ] Tested with a draft→ready PR transition
- [ ] All CI jobs run successfully on ready transition
- [ ] Documentation updated
- [ ] Progress doc created
