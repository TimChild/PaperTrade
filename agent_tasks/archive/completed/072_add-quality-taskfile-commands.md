# Task 072: Add Combined Quality Tasks to Taskfile

**Agent**: quality-infra
**Priority**: High
**Estimated Effort**: 15 minutes

## Objective

Add combined quality-check tasks to `Taskfile.yml` that run format + lint + test in one command, enabling simpler agent documentation.

## Background

The Taskfile has individual tasks (`format:backend`, `lint:backend`, `test:backend`) but agents need to remember multiple commands. Adding combined tasks simplifies documentation and improves consistency.

## Requirements

### Add These Tasks to Taskfile.yml

**1. `quality:backend`** - Run all backend quality checks
```yaml
quality:backend:
  desc: "Run all backend quality checks (format, lint, test)"
  cmds:
    - task: format:backend
    - task: lint:backend
    - task: test:backend
    - echo "✓ All backend quality checks passed"
```

**2. `quality:frontend`** - Run all frontend quality checks
```yaml
quality:frontend:
  desc: "Run all frontend quality checks (format, lint, test)"
  cmds:
    - task: format:frontend
    - task: lint:frontend
    - task: test:frontend
    - echo "✓ All frontend quality checks passed"
```

**3. `quality`** - Run all quality checks
```yaml
quality:
  desc: "Run all quality checks (backend and frontend)"
  cmds:
    - task: quality:backend
    - task: quality:frontend
    - echo "✓ All quality checks passed"
```

### Placement

Add these tasks in a new section after the existing `ci:` tasks (around line 400):

```yaml
# =========================================================================
# Quality Checks (combined format + lint + test)
# =========================================================================
```

## Success Criteria

- [ ] `task quality:backend` runs format, lint, test sequentially
- [ ] `task quality:frontend` runs format, lint, test sequentially
- [ ] `task quality` runs both backend and frontend quality checks
- [ ] `task --list` shows the new tasks with descriptions
- [ ] All new tasks work when run manually

## Testing

```bash
# Test each new task
task quality:backend
task quality:frontend
task quality

# Verify they appear in task list
task --list | grep quality
```

## Notes

- These tasks enable simplifying agent documentation to single-command references
- Keep individual tasks (`format:backend`, etc.) for when agents only need one check
- The combined tasks are for "pre-completion" validation
