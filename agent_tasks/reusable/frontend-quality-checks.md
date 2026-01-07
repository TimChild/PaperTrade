# Frontend Quality Checks

**Run these checks before completing frontend work to catch issues early.**

## Format Code

```bash
cd frontend && npm run format
```

This auto-formats TypeScript/JavaScript code using Prettier.

## Linting & Type Checking

Run the CI validation task:
```bash
task lint:frontend
```

This runs:
- **ESLint**: JavaScript/TypeScript linting
- **TypeScript compiler**: Type checking (strict mode)

## Testing

Run the unit test suite:
```bash
task test:frontend
```

This runs Vitest unit tests.

## Quick Validation

Run all frontend quality checks at once:
```bash
cd frontend && npm run format && task lint:frontend && task test:frontend
```

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "Code style issues found" | Run `npm run format` |
| Type error | Add explicit types, check return types |
| "Cannot find namespace 'JSX'" | Add `import type { JSX } from 'react'` |
| Test failures | Fix component or test, then re-run |

## Requirements

- **TypeScript**: All code in TypeScript (strict mode)
- **Explicit types**: Return types on all functions
- **No `any`**: No `any` type except documented exceptions
- **Accessibility**: Interactive elements must be keyboard accessible
- **Test IDs**: Add `data-testid` to interactive elements for E2E tests
