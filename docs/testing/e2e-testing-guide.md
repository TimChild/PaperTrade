# E2E Testing Infrastructure Guide

**Date**: 2026-01-18  
**Purpose**: Document the E2E testing strategy and infrastructure

---

## Overview

E2E tests use a **dedicated test mode** that bypasses Clerk authentication complexity. Instead of managing real Clerk sessions, tests use static authentication tokens.

**Benefits**:
- ✅ Reliable (no Clerk session persistence issues)
- ✅ Fast (no real Clerk session creation)
- ✅ Simple (static tokens, deterministic)
- ✅ Maintainable (clear test/production separation)

---

## Quick Start

```bash
# Run all E2E tests
task test:e2e

# Run with UI
task test:e2e:ui

# Run specific test
task test:e2e -- tests/e2e/portfolio-creation.spec.ts
```

---

## How It Works

### E2E Mode Architecture

**Frontend**: Detects `VITE_E2E_TEST_MODE=true` → Sends static token  
**Backend**: Detects `E2E_TEST_MODE=true` → Accepts any token

```
Test → Frontend (static token) → Backend (permissive auth) → Success
```

### Environment Variables

- `E2E_TEST_MODE=true` - Backend uses InMemoryAuthAdapter (permissive mode)
- `VITE_E2E_TEST_MODE=true` - Frontend uses static test token
- `E2E_CLERK_USER_EMAIL` - Test user email (default: test-e2e@papertrade.dev)

---

## Troubleshooting

**401 errors?**
1. Check backend: `docker compose logs backend | grep E2E_TEST_MODE`
2. Restart services: `task docker:down && task docker:up:all`

**Tests timeout?**
1. Check browser console for: `[API Client] E2E mode: Using static test token`
2. Verify Playwright config has `env: { VITE_E2E_TEST_MODE: 'true' }`

---

## See Also

- Original investigation: `agent_progress_docs/2026-01-18_22-33-28_portfolio-creation-timeout-investigation.md`
- Integration tests: `backend/tests/conftest.py` (strict auth mode)
- Playwright config: `frontend/playwright.config.ts`
