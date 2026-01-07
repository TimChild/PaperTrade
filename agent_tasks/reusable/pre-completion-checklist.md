# Pre-Completion Checklist for Agents

**CRITICAL**: Run these commands BEFORE marking your work complete. Prevents CI failures.

## Required Steps

### 1. Format Code (Fixes 80% of lint errors)

**Backend**:
```bash
cd backend && uv run ruff format .
```

**Frontend**:
```bash
cd frontend && npm run format
```

### 2. Run Linters

**Backend** (ruff + pyright type checking):
```bash
task lint:backend
```

**Frontend** (eslint + TypeScript):
```bash
task lint:frontend
```

### 3. Run Tests

**Backend**:
```bash
task test:backend
```

**Frontend**:
```bash
task test:frontend
```

**E2E** (if UI changes):
```bash
task test:e2e
```

## Common Fixes

- **"Would reformat" error** → Run `uv run ruff format .` or `npm run format`
- **Type errors** → Read error message, fix types, re-run lint task
- **"Cannot find namespace 'JSX'"** → Add `import type { JSX } from 'react'` at top of file
- **Test failures** → Fix code or test, then re-run test task

## Quick Reference

| Task | When |
|------|------|
| `task ci` | Run ALL checks (recommended before finishing) |
| `task lint:backend` | After backend changes |
| `task lint:frontend` | After frontend changes |

**DO NOT mark work complete until all checks pass!**
