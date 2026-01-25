# E2E Testing with Docker

## Overview

E2E tests run inside a Docker container using Playwright. This eliminates network proxy issues and creates a production-like testing environment where tests can access services via Docker's internal DNS.

## Prerequisites

```bash
# Install dependencies (if not already done)
npm ci
```

## Running Tests

### In Docker (Recommended)

Run all E2E tests in a Docker container:

```bash
task test:e2e
```

Run specific tests by pattern:

```bash
task test:e2e -- --grep "portfolio"
task test:e2e -- --grep "trading"
```

### With UI Mode (Local Debugging)

For debugging tests with Playwright UI:

```bash
task test:e2e:ui
```

**Note**: UI mode runs on the host machine (not in Docker) and requires the full stack to be running via `docker compose up -d`.

## How It Works

### Architecture

```
┌─────────────────────────────────────────────┐
│ Docker Container: e2e-tests                 │
│                                             │
│  Playwright Tests                           │
│    ↓                                        │
│  http://frontend:5173 ──→ Frontend Service  │
│                              ↓              │
│                    http://backend:8000 ──→  │
│                          Backend Service    │
└─────────────────────────────────────────────┘
```

### Key Components

1. **Dockerfile.e2e**: Defines the Playwright test runner container
2. **docker-compose.yml**: Configures the `e2e-tests` service with `e2e` profile
3. **playwright.config.ts**: Uses `PLAYWRIGHT_BASE_URL` environment variable
4. **Taskfile.yml**: Provides convenient commands for running tests

### Environment Variables

Tests require these environment variables (loaded from `.env`):

- `CLERK_SECRET_KEY`: Clerk authentication key
- `VITE_CLERK_PUBLISHABLE_KEY`: Clerk publishable key
- `E2E_CLERK_USER_EMAIL`: Test user email

## Test Results

Test results are saved to your local machine:

- **HTML Report**: `playwright-report/` - Open `index.html` in a browser
- **Test Results**: `test-results/` - Detailed test artifacts
- **Temporary Files**: `temp/` - Screenshots, traces

## Debugging Failed Tests

### View HTML Report

```bash
npx playwright show-report
```

### Check Test Logs

```bash
# During test run, logs are visible in terminal

# After test run, check Docker logs
docker compose --profile e2e logs e2e-tests
```

### Run Tests with Headed Browser

For debugging in UI mode:

```bash
task test:e2e:ui
```

## Writing Tests

### Test ID Conventions

Use `data-testid` attributes for stable element targeting:

```typescript
// ✅ Good - using test ID
await page.getByTestId('portfolio-create-button').click()

// ❌ Avoid - fragile selectors
await page.getByText('Create Portfolio').click()
```

**Naming Pattern**: `{component}-{element}-{variant?}`

Examples:
- `portfolio-create-button`
- `trade-buy-modal`
- `analytics-chart-container`

See `docs/reference/testing-conventions.md` for complete guidelines.

### Example Test

```typescript
import { test, expect } from '@playwright/test'

test('should create a new portfolio', async ({ page }) => {
  await page.goto('/')
  
  // Wait for page to load
  await expect(page.getByTestId('portfolio-list')).toBeVisible()
  
  // Click create button
  await page.getByTestId('portfolio-create-button').click()
  
  // Fill form
  await page.getByTestId('portfolio-name-input').fill('My Test Portfolio')
  await page.getByTestId('portfolio-submit-button').click()
  
  // Verify success
  await expect(page.getByText('My Test Portfolio')).toBeVisible()
})
```

## Troubleshooting

### Tests Timing Out

If tests timeout waiting for services:

```bash
# Check service health
docker compose ps

# View service logs
docker compose logs backend
docker compose logs frontend
```

### Network Errors

If tests report network errors:

1. Verify all services are healthy: `docker compose ps`
2. Check service health endpoints:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:5173/
   ```

### Authentication Errors

If tests fail with authentication errors:

1. Verify environment variables are set in `.env`:
   ```bash
   grep CLERK .env
   grep E2E_CLERK .env
   ```

2. Verify test user exists in Clerk dashboard

### "Module not found" Errors

Ensure node_modules is installed:

```bash
cd frontend
npm ci
```

## CI/CD Integration

### GitHub Actions

The E2E tests can be integrated into CI workflows:

```yaml
- name: Run E2E tests
  run: docker compose --profile e2e up --build --abort-on-container-exit e2e-tests

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: playwright-report
    path: frontend/playwright-report/
```

## Performance

- **Build Time**: ~2 seconds (using mounted node_modules)
- **Test Execution**: Varies by test suite (typically 1-5 minutes for full suite)
- **Parallel Execution**: Disabled in CI mode for stability

## References

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Playwright Docker Guide](https://playwright.dev/docs/docker)
- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)
- [Project Testing Conventions](../../docs/reference/testing-conventions.md)
