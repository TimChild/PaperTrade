# Task 096: Fix Docker Test Environment Issues

**Status**: Not Started
**Agent**: quality-infra
**Priority**: High
**Estimated Effort**: Small
**Dependencies**: None

## Context

Frontend unit tests are failing when run inside Docker containers with errors like:
```
ReferenceError: document is not defined
TypeError: Cannot read properties of undefined (reading 'Symbol(Node prepared with document state workarounds)')
```

The tests pass perfectly when run locally (`npm run test:unit` on host), but fail when run in Docker (`docker compose exec frontend npm run test:unit`). This indicates a jsdom/test environment configuration issue specific to the Docker environment.

## Problem Analysis

**Error Pattern**:
- Tests: 128 failed | 39 passed (168 total)
- Primary errors: `document is not defined` and userEvent setup failures
- Affects tests using `render()` from `@testing-library/react`
- Works locally, fails in Docker

**Likely Causes**:
1. jsdom not properly initialized in Docker environment
2. Vitest environment configuration mismatch
3. Missing environment variables or setup in Docker
4. Node version differences between local and Docker

## Goals

Fix the test environment so that all 194 frontend tests pass when run inside Docker containers, ensuring CI/CD reliability and consistent test execution across environments.

## Success Criteria

- [ ] All 194 frontend unit tests pass in Docker
- [ ] Tests pass consistently across runs
- [ ] No "document is not defined" errors
- [ ] userEvent.setup() works correctly
- [ ] Same test results locally and in Docker

## Implementation Plan

### 1. Verify Vitest Environment Config (15 min)

Check `frontend/vitest.config.ts`:

```typescript
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom', // ← Ensure this is set
    setupFiles: ['./tests/setup.ts'],
    // Add if missing:
    environmentOptions: {
      jsdom: {
        resources: 'usable',
      },
    },
  },
});
```

### 2. Enhance Test Setup (20 min)

Update `frontend/tests/setup.ts`:

```typescript
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll } from 'vitest';
import '@testing-library/jest-dom/vitest';

// Ensure jsdom globals are available
beforeAll(() => {
  // Verify document is available
  if (typeof document === 'undefined') {
    throw new Error('jsdom not initialized - check vitest config');
  }
});

// Clean up after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia (already present)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver if needed
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;
```

### 3. Check Docker Node Version (10 min)

Verify `frontend/Dockerfile` uses same Node version as local:

```dockerfile
# Should match local node version
FROM node:20-alpine

# Ensure npm is up to date
RUN npm install -g npm@latest

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
CMD ["npm", "run", "dev"]
```

### 4. Add Happy-DOM Alternative (Optional, 15 min)

If jsdom continues to fail, try happy-dom which is faster and more reliable:

```bash
npm install -D happy-dom
```

Update `vitest.config.ts`:
```typescript
export default defineConfig({
  test: {
    environment: 'happy-dom', // Instead of jsdom
  },
});
```

### 5. Debug Docker Environment (20 min)

Create debug script `frontend/scripts/debug-test-env.js`:

```javascript
#!/usr/bin/env node

console.log('Node version:', process.version);
console.log('Platform:', process.platform);
console.log('Env vars:', {
  NODE_ENV: process.env.NODE_ENV,
  CI: process.env.CI,
});

// Test jsdom availability
try {
  const { JSDOM } = require('jsdom');
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
  console.log('✅ jsdom works');
  console.log('document:', typeof dom.window.document);
} catch (e) {
  console.log('❌ jsdom failed:', e.message);
}

// Test vitest
try {
  const vitest = require('vitest');
  console.log('✅ vitest available');
} catch (e) {
  console.log('❌ vitest failed:', e.message);
}
```

Run: `docker compose exec frontend node scripts/debug-test-env.js`

### 6. Verify Dependencies (10 min)

Ensure all test dependencies are installed in Docker:

```bash
docker compose exec frontend npm list jsdom
docker compose exec frontend npm list @testing-library/react
docker compose exec frontend npm list vitest
```

If any are missing, add to `package.json` dependencies (not devDependencies for Docker):

```json
{
  "dependencies": {
    "jsdom": "^24.0.0"
  }
}
```

## Testing Strategy

**After each fix**:
```bash
# Rebuild and test
docker compose down
docker compose build frontend
docker compose up -d
docker compose exec frontend npm run test:unit
```

**Verification**:
- All 194 tests pass
- No document errors
- Consistent results across multiple runs

## Expected Root Cause

Most likely: Vitest environment not set to 'jsdom' in config, or jsdom installed as devDependency which Docker build excludes in production mode.

## Files to Check/Modify

1. `frontend/vitest.config.ts` - Environment configuration
2. `frontend/tests/setup.ts` - Test setup enhancements
3. `frontend/Dockerfile` - Node version, build process
4. `frontend/package.json` - Dependencies classification
5. `frontend/.dockerignore` - Ensure not excluding test files

## Expected Outcomes

After completion:
- ✅ 194/194 tests passing in Docker
- ✅ Tests run reliably in CI/CD
- ✅ Consistent results local vs Docker
- ✅ Fast test execution
- ✅ No environment-specific failures

## Next Steps

Once Docker tests are fixed:
- Update CI workflow to run tests in Docker
- Document test execution commands
- Add health check for test environment

## References

- Vitest jsdom config: https://vitest.dev/config/#environment
- Testing Library setup: https://testing-library.com/docs/react-testing-library/setup
- Docker Node.js best practices: https://github.com/nodejs/docker-node/blob/main/docs/BestPractices.md
