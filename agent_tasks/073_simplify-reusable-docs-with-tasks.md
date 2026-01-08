# Task 073: Simplify Reusable Agent Docs with Taskfile References

**Agent**: refactorer
**Priority**: High
**Estimated Effort**: 20 minutes
**Depends On**: Task 072 (quality tasks must exist in Taskfile first)

## Objective

Simplify the reusable agent guidance documents in `agent_tasks/reusable/` by replacing verbose command documentation with simple Taskfile task references.

## Background

The current reusable docs duplicate command knowledge that already exists in `Taskfile.yml`. By referencing tasks instead, we:
- Reduce documentation length (target: 20-30 lines max)
- Single source of truth (Taskfile)
- Easier maintenance (update task, docs automatically current)

## Files to Update

### 1. `backend-quality-checks.md` (~45 lines → ~20 lines)

**New content:**
```markdown
# Backend Quality Checks

Run `task setup:backend` first if dependencies aren't installed.

## Quick Reference

| Task | Description |
|------|-------------|
| `task format:backend` | Auto-format code (ruff) |
| `task lint:backend` | Lint + type check (ruff, pyright) |
| `task test:backend` | Run tests with coverage |
| `task quality:backend` | **All of the above** |

## Requirements

- Complete type hints (no `Any`)
- Docstrings for public APIs
- Tests for new functionality

## Common Fixes

| Error | Fix |
|-------|-----|
| "Would reformat" | Run `task format:backend` |
| Type error | Add explicit type hints |
| Import error | Check spelling, add import |
```

### 2. `frontend-quality-checks.md` (~45 lines → ~20 lines)

**New content:**
```markdown
# Frontend Quality Checks

Run `task setup:frontend` first if dependencies aren't installed.

## Quick Reference

| Task | Description |
|------|-------------|
| `task format:frontend` | Auto-format code (prettier) |
| `task lint:frontend` | Lint + type check (eslint, tsc) |
| `task test:frontend` | Run unit tests (vitest) |
| `task quality:frontend` | **All of the above** |

## Requirements

- TypeScript strict mode (no `any`)
- Explicit return types
- `data-testid` on interactive elements

## Common Fixes

| Error | Fix |
|-------|-----|
| "Code style issues" | Run `task format:frontend` |
| Type error | Add explicit types |
| JSX namespace error | `import type { JSX } from 'react'` |
```

### 3. `docker-commands.md` (~45 lines → ~25 lines)

**New content:**
```markdown
# Docker Commands

## Quick Reference

| Task | Description |
|------|-------------|
| `task docker:up` | Start PostgreSQL, Redis |
| `task docker:up:all` | Start full stack (db, redis, backend, frontend) |
| `task docker:down` | Stop all services |
| `task docker:logs` | Tail all service logs |
| `task docker:restart` | Restart all services |
| `task docker:clean` | Stop + remove volumes (**deletes data**) |

## Status & Debugging

```bash
docker compose ps              # Service status
task docker:logs               # All logs
task docker:logs:backend       # Backend only
```

## Common Issues

| Issue | Fix |
|-------|-----|
| Port in use | `lsof -ti:5432 \| xargs kill -9` |
| Container won't start | `task docker:logs` |
| Database issues | `task docker:clean && task docker:up` |
```

### 4. `pre-completion-checklist.md` (~45 lines → ~15 lines)

**New content:**
```markdown
# Pre-Completion Checklist

**Run before marking work complete to prevent CI failures.**

## Required

```bash
task quality:backend    # Backend: format + lint + test
task quality:frontend   # Frontend: format + lint + test
task test:e2e           # If UI changes (starts full stack)
```

Or run everything:
```bash
task ci                 # All CI checks
```

## Common Fixes

| Error | Fix |
|-------|-----|
| Format errors | `task format:backend` or `task format:frontend` |
| Type errors | Read error message, fix types |
| Test failures | Fix code/test, re-run |

**DO NOT mark work complete until all checks pass!**
```

## Success Criteria

- [ ] Each file is under 30 lines
- [ ] All referenced tasks exist in Taskfile.yml
- [ ] No raw `cd backend && uv run ...` commands (use task references)
- [ ] Tables are clear and scannable
- [ ] Critical requirements still documented

## Testing

After updates, verify:
1. Each task mentioned actually exists: `task --list | grep <task-name>`
2. File content is clear and actionable
3. No broken references
