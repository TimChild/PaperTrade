# Pre-Completion Checklist for Agents

**CRITICAL**: Run these commands BEFORE marking work complete to prevent CI failures.

## Required Steps

### 1. Format Code (Fixes ~80% of lint errors)

```bash
cd backend && uv run ruff format .     # Backend
cd frontend && npm run format          # Frontend
```

### 2. Run Linters

```bash
task lint:backend                      # Backend (ruff + pyright)
task lint:frontend                     # Frontend (eslint + TypeScript)
```

### 3. Run Tests

```bash
task test:backend                      # Backend tests
task test:frontend                     # Frontend tests
task test:e2e                          # E2E (if UI changes)
```

## Common Fixes

| Error | Fix |
|-------|-----|
| "Would reformat" | Run `uv run ruff format .` or `npm run format` |
| Type errors | Read error, fix types, re-run lint |
| "Cannot find namespace 'JSX'" | Add `import type { JSX } from 'react'` |
| Test failures | Fix code/test, re-run |

## Quick Reference

```bash
task ci                                # Run ALL checks (recommended)
```

**DO NOT mark work complete until all checks pass!**
