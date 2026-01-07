# Frontend Quality Checks

**Run these checks before completing frontend work.**

## Format Code

```bash
cd frontend && npm run format
```

## Linting & Type Checking

```bash
task lint:frontend
```

Runs:
- **ESLint**: JavaScript/TypeScript linting
- **TypeScript**: Type checking (strict mode)

## Testing

```bash
task test:frontend
```

Runs Vitest unit tests.

## Quick Validation

```bash
cd frontend && npm run format && task lint:frontend && task test:frontend
```

## Common Issues

| Issue | Fix |
|-------|-----|
| "Code style issues" | Run `npm run format` |
| Type error | Add explicit types, check return types |
| "Cannot find namespace 'JSX'" | Add `import type { JSX } from 'react'` |
| Test failures | Fix component/test, re-run |

## Requirements

- TypeScript strict mode (no `any`)
- Explicit return types on functions
- Keyboard accessibility for interactive elements
- `data-testid` on interactive elements for E2E tests
