# Task 172: Dockerize E2E Tests

**Date**: January 24, 2026
**Agent**: quality-infra
**Branch**: fix/e2e-test-output-and-failures

## Objective

Refactor E2E tests to run inside a Docker container instead of on the host machine. This eliminates network proxy issues and creates a production-like testing environment.

## Context

**Current Problem**:
E2E tests run on host → access frontend via localhost:5173 → frontend uses Vite proxy to reach backend → **proxy forwards requests but responses never return**.

**Root Cause Analysis**:
- Vite dev server proxy is designed for local development, not container-to-host networking
- Requests successfully reach backend (confirmed in backend logs: `200 OK`)
- Responses get lost between container and host (curl returns empty)
- 379+ "Network error - no response from server" errors in browser console

**Architectural Decision**:
Move Playwright tests into a Docker container where they can access frontend/backend via Docker's internal DNS (`http://frontend:5173`, `http://backend:8000`). This is the canonical, production-grade approach used by mature projects.

## Requirements

### 1. Create E2E Test Dockerfile

**File**: `frontend/Dockerfile.e2e`

```dockerfile
# Playwright E2E test runner
FROM mcr.microsoft.com/playwright:v1.57.0-jammy

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy test files and configuration
COPY playwright.config.ts ./
COPY tests/ ./tests/
COPY tsconfig.json ./

# Install Playwright browsers (already included in base image, but ensure latest)
RUN npx playwright install --with-deps chromium

# Default command - run tests
CMD ["npx", "playwright", "test"]
```

### 2. Add E2E Service to Docker Compose

**File**: `docker-compose.yml` (ADD new service)

Add after the `frontend` service:

```yaml
  e2e-tests:
    build:
      context: ./frontend
      dockerfile: Dockerfile.e2e
    environment:
      # Playwright configuration
      PLAYWRIGHT_BASE_URL: http://frontend:5173
      CI: "true"  # Enable CI mode (no parallel, retries enabled)

      # API configuration (for frontend app)
      VITE_API_BASE_URL: http://backend:8000/api/v1
      VITE_CLERK_PUBLISHABLE_KEY: ${VITE_CLERK_PUBLISHABLE_KEY}

      # Clerk testing credentials
      CLERK_SECRET_KEY: ${CLERK_SECRET_KEY}
      E2E_CLERK_USER_EMAIL: ${E2E_CLERK_USER_EMAIL}
    volumes:
      # Mount test files for live updates during development
      - ./frontend/tests:/app/tests:ro
      - ./frontend/playwright.config.ts:/app/playwright.config.ts:ro

      # Mount output directory for test results/reports
      - ./frontend/playwright-report:/app/playwright-report
      - ./frontend/test-results:/app/test-results
      - ./temp:/app/temp
    depends_on:
      frontend:
        condition: service_healthy
      backend:
        condition: service_healthy
    networks:
      - zebu-network
    profiles:
      - e2e  # Don't start automatically, only with --profile e2e
```

### 3. Update Playwright Configuration

**File**: `frontend/playwright.config.ts` (MODIFY)

Update `baseURL` to use environment variable:

```typescript
export default defineConfig({
  testDir: './tests/e2e',
  globalSetup: path.resolve(__dirname, './tests/e2e/global-setup.ts'),
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],

  use: {
    // Use environment variable for base URL (defaults to localhost for local dev)
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Use saved auth state from setup
        storageState: path.resolve(__dirname, './playwright/.auth/user.json'),
      },
      dependencies: ['setup'],
    },
  ],
})
```

### 4. Update Taskfile Commands

**File**: `Taskfile.yml` (MODIFY)

Update E2E test tasks to use Docker:

```yaml
  test:e2e:
    desc: "Run E2E tests in Docker container (pass args after --: task test:e2e -- --grep 'test name')"
    dir: "{{.ROOT_DIR}}"
    env:
      CLERK_SECRET_KEY:
        sh: grep "^CLERK_SECRET_KEY=" .env | cut -d= -f2- || echo ""
      CLERK_PUBLISHABLE_KEY:
        sh: grep "^CLERK_PUBLISHABLE_KEY=" .env | cut -d= -f2- || echo ""
      VITE_CLERK_PUBLISHABLE_KEY:
        sh: grep "^VITE_CLERK_PUBLISHABLE_KEY=" .env | cut -d= -f2- || echo ""
      E2E_CLERK_USER_EMAIL:
        sh: grep "^E2E_CLERK_USER_EMAIL=" .env | cut -d= -f2- || echo ""
    cmds:
      - echo "Starting E2E test environment..."
      - docker compose --profile e2e up --build --abort-on-container-exit e2e-tests
      - echo "Cleaning up E2E containers..."
      - docker compose --profile e2e down
    preconditions:
      - sh: test -f .env
        msg: ".env file not found. Copy .env.example and configure."

  test:e2e:ui:
    desc: "Run E2E tests with Playwright UI (runs locally, not in Docker)"
    dir: "{{.FRONTEND_DIR}}"
    deps:
      - docker:up:all  # Need services running
    env:
      CLERK_SECRET_KEY:
        sh: grep "^CLERK_SECRET_KEY=" ../.env | cut -d= -f2- || echo ""
      CLERK_PUBLISHABLE_KEY:
        sh: grep "^CLERK_PUBLISHABLE_KEY=" ../.env | cut -d= -f2- || echo ""
      VITE_CLERK_PUBLISHABLE_KEY:
        sh: grep "^VITE_CLERK_PUBLISHABLE_KEY=" ../.env | cut -d= -f2- || echo ""
      E2E_CLERK_USER_EMAIL:
        sh: grep "^E2E_CLERK_USER_EMAIL=" ../.env | cut -d= -f2- || echo ""
    cmds:
      - echo "Running E2E tests in UI mode (localhost)..."
      - npm run test:e2e:ui
    preconditions:
      - sh: test -f package.json
        msg: "Frontend not found"
```

### 5. Remove Vite Proxy Configuration

**File**: `frontend/vite.config.ts` (MODIFY)

Remove the proxy configuration since tests will access backend directly:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // Proxy removed - frontend uses VITE_API_BASE_URL directly
  },
})
```

### 6. Update Frontend API Client

**File**: `frontend/src/lib/api.ts` (VERIFY)

Ensure API client uses environment variable (should already be configured):

```typescript
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})
```

### 7. Update .gitignore

**File**: `.gitignore` (VERIFY)

Ensure test artifacts are ignored:

```gitignore
# Playwright
frontend/playwright-report/
frontend/test-results/
frontend/playwright/.auth/
temp/
```

### 8. Update CI Workflow (Optional)

**File**: `.github/workflows/ci.yml` (OPTIONAL - for future)

E2E tests in CI can use the same Docker approach:

```yaml
  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-checks, frontend-checks]
    steps:
      - uses: actions/checkout@v4

      - name: Create .env file
        run: |
          echo "CLERK_SECRET_KEY=${{ secrets.CLERK_SECRET_KEY }}" >> .env
          echo "VITE_CLERK_PUBLISHABLE_KEY=${{ secrets.CLERK_PUBLISHABLE_KEY }}" >> .env
          echo "E2E_CLERK_USER_EMAIL=${{ vars.E2E_CLERK_USER_EMAIL }}" >> .env

      - name: Run E2E tests
        run: docker compose --profile e2e up --build --abort-on-container-exit e2e-tests

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## Success Criteria

- [ ] `Dockerfile.e2e` created and builds successfully
- [ ] `e2e-tests` service added to `docker-compose.yml`
- [ ] `task test:e2e` runs tests in Docker container
- [ ] E2E tests can access frontend at `http://frontend:5173`
- [ ] E2E tests can access backend at `http://backend:8000`
- [ ] All 22 E2E tests pass (no network errors)
- [ ] Test reports saved to host via volume mount
- [ ] Vite proxy configuration removed
- [ ] Test output visible in terminal
- [ ] Can filter tests: `task test:e2e -- --grep "portfolio"`
- [ ] Changes committed with clear messages

## Testing Plan

```bash
# 1. Build and test E2E service
docker compose --profile e2e build e2e-tests

# 2. Run full E2E suite
task test:e2e

# Expected: All 22 tests pass
# Expected: No "Network error - no response from server"
# Expected: Test report in frontend/playwright-report/

# 3. Run filtered tests
task test:e2e -- --grep "portfolio"

# Expected: Only portfolio tests run

# 4. Verify test reports
ls -la frontend/playwright-report/
ls -la temp/

# 5. Check logs for any errors
docker compose --profile e2e logs e2e-tests
```

## References

- **Architecture Decision**: This task implements Option 1 from the E2E testing investigation
- **Investigation Context**: Branch `fix/e2e-test-output-and-failures` contains full debugging history
- **Original Issue**: Vite proxy forwarding requests but not returning responses
- **Playwright Docker Docs**: https://playwright.dev/docs/docker
- **Docker Compose Profiles**: https://docs.docker.com/compose/profiles/

## Notes

- **Why Docker profiles?** E2E tests shouldn't run on every `docker compose up`, only when explicitly requested
- **Why `--abort-on-container-exit`?** Tests should exit after completion, not keep running
- **Why keep `test:e2e:ui`?** UI mode is useful for debugging and should run locally (can't display UI in container)
- **Volume mounts**: Read-only (`:ro`) for test files prevents accidental modification, read-write for reports

## Definition of Done

- [ ] All E2E tests passing in Docker container
- [ ] No proxy configuration needed
- [ ] Test reports accessible on host machine
- [ ] Taskfile commands updated and tested
- [ ] CI workflow updated (optional but recommended)
- [ ] Progress documentation created
- [ ] PR created with clear description
- [ ] Branch merged to main

## Impact

**Risk**: MEDIUM - Significant infrastructure change, but isolated to testing
**Priority**: HIGH - Blocking E2E test functionality
**Effort**: 2-3 hours (Docker setup, configuration, testing)
