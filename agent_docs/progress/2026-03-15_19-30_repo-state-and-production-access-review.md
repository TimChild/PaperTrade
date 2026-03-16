# Repo State and Production Access Review

**Date**: 2026-03-15
**Session Type**: Orchestrator investigation / handoff note
**Status**: In progress

## Purpose

Capture the current repository state, recent project progress, and findings from initial
production-access checks so a future session can resume quickly without redoing discovery.

## Current Repo State

- `main` is clean locally; no uncommitted changes before this note was added.
- GitHub CLI showed **no open PRs**.
- Recent merged PR wave on **2026-03-08** covered Phase 4 completion:
  - PR #202: backtesting entities, migrations, repositories
  - PR #203: backtest execution engine and CRUD endpoints
  - PR #204: DCA + MA crossover strategies
  - PR #206: ticker validation, 503 handling, integration tests
  - PR #207: frontend backtesting and comparison UI
  - PR #208: milestone docs cleanup
- Latest commit on `main` after that wave:
  - `4d7b313` - `fix: support async DB driver in alembic + add migrations to CD pipeline`

## What Is Implemented

- Strategy CRUD API exists in `backend/src/zebu/adapters/inbound/api/strategies.py`.
- Backtest execution API exists in `backend/src/zebu/adapters/inbound/api/backtests.py`.
- Scheduler currently runs:
  - `refresh_active_stocks`
  - `calculate_daily_snapshots`
- Live strategy activation/execution is **not** implemented yet.
- The next major feature is already scoped in:
  - `agent_docs/tasks/210_live_strategy_execution.md`

## Production Checks Performed

Verified on 2026-03-15:

- `https://zebutrader.com/` returned HTTP 200.
- `https://zebutrader.com/api/v1/` returned the API welcome payload.
- `https://api.zebutrader.com/health` returned `{"status":"healthy"}`.
- Unauthenticated `GET /api/v1/portfolios` returned HTTP 401 as expected.
- Public market data endpoint responded:
  - `GET /api/v1/prices/batch?tickers=AAPL,MSFT`

## Authenticated Production Access Findings

Attempted a **read-only** authenticated production probe using the existing Clerk Playwright
test flow (`clerkSetup()` + `setupClerkTestingToken()` + `clerk.signIn({ emailAddress })`).

Result:

- Production sign-in ticket was rejected as invalid.
- Most likely explanation: the local Clerk test credentials/environment are for a different
  Clerk instance than the production frontend/backend.
- This means:
  - public health and auth enforcement are verified
  - authenticated production API access is **not yet operational from this local setup**

## Authenticated Local Access Findings

Validated successfully on 2026-03-15 using the local Docker app stack plus the existing
Clerk Playwright flow:

- Started stack with `task docker:up:all`
- Waited for readiness with `task health:wait`
- Signed in via Clerk using:
  - `clerkSetup()`
  - `setupClerkTestingToken({ page })`
  - `clerk.signIn({ page, emailAddress })`
- Extracted a real session token from the browser session
- Performed read-only authenticated API checks:
  - `GET http://localhost:8000/api/v1/portfolios` → 200
  - `GET http://localhost:8000/api/v1/portfolios/{id}/balance` → 200

Conclusion:

- The **local** authenticated smoke-test path is already viable with the current stack.
- This should be the baseline implementation to formalize first.
- Production should reuse the same flow with environment-specific base URLs and matching
  Clerk credentials.

## CI/CD Findings

- Latest GitHub Actions runs on 2026-03-09:
  - **CI**: success
  - **CD**: success
- Latest CI counts observed:
  - 831 backend tests passed
  - 311 frontend tests passed
  - 20 E2E tests passed, 1 skipped
- CD now runs Alembic migrations during deploy in `.github/workflows/cd.yml`.

## Documentation Drift / Maintenance Findings

- `resume-from-here.md` still lists “Alembic in CD pipeline” as a future step, but CD now
  runs migrations.
- `BACKLOG.md` still lists Alembic-in-CD as pending for the same reason.
- `PROGRESS.md` has inconsistent backend test counts (one section says 835, another says 831).
- Version references are a little confusing:
  - historical docs mention `v1.2.0`
  - current code version source is `1.0.0`
- GitHub Pages maintenance issue:
  - intended MkDocs workflow exists in `.github/workflows/docs.yml`
  - default `pages build and deployment` is also firing and failing because Jekyll tries to
    render archived/agent markdown with Liquid-like syntax
- CI coverage upload is noisy:
  - Codecov upload attempts fail but are non-blocking

## Known Product / Security Gaps

- Live strategy execution not built yet.
- Admin/ownership TODOs still exist on analytics admin endpoints in
  `backend/src/zebu/adapters/inbound/api/analytics.py`.
- There is currently no simple, documented, safe authenticated smoke-test path for production.

## Recommended Next Steps

1. Build a safe authenticated smoke-test path for local and production.
2. Decide what production auth setup is intended:
   - prod Clerk test user
   - prod-compatible Clerk secret/publishable keys
   - read-only smoke test only
3. Implement Task 210 for live strategy execution after smoke-test confidence improves.
4. Clean up docs drift (`PROGRESS.md`, `BACKLOG.md`, `resume-from-here.md`).
5. Fix Pages configuration conflict and Codecov upload noise.

## Proposed Smoke Test Shape

Recommended implementation:

1. Add a small Node/Playwright script under the frontend test tooling that:
   - loads env vars
   - signs in through Clerk
   - extracts a session token from the browser
   - performs **read-only** API requests
   - exits non-zero on failure
2. Support two modes:
   - local: `http://localhost:5173` + `http://localhost:8000`
   - production: `https://zebutrader.com` + `https://zebutrader.com/api/v1` (or
     `https://api.zebutrader.com/api/v1` if preferred)
3. Keep the check read-only:
   - `GET /api/v1/portfolios`
   - optional `GET /api/v1/portfolios/{id}/balance` if at least one portfolio exists
4. Wrap with Taskfile commands such as:
   - `task smoke:auth:local`
   - `task smoke:auth:prod`
5. Mask tokens and avoid printing sensitive values to logs.

## Information Still Needed For Production Smoke Tests

To make the **production** version work safely, we still need:

- Clerk credentials that match the production frontend/backend instance
  - production-compatible secret key
  - matching publishable key if needed by the script
- A dedicated production smoke-test user email in that same Clerk instance
- Confirmation of the preferred production API base URL:
  - proxied through `zebutrader.com`
  - or direct via `api.zebutrader.com`
- Confirmation that read-only queries are sufficient
  - recommended: yes
- If deeper checks are wanted, a stable portfolio in the smoke-test account

## Useful Commands

```bash
GH_PAGER="" gh pr list --state open
GH_PAGER="" gh pr list --state merged --limit 12
GH_PAGER="" gh run list --limit 8
task --list
task quality:backend
task quality:frontend
task proxmox-vm:status
```

---

## Update: Authenticated Smoke Tests and Deployment Findings

### What Was Added

- Added authenticated smoke tooling:
  - `frontend/scripts/authenticated-smoke.mjs`
  - `task smoke:auth:local`
  - `task smoke:auth:prod`
- Added a Docker migration helper:
  - `task db:migrate:docker`
- Updated `task docker:up:all` to run Docker-backed Alembic migrations automatically.

### Local Verification Results

Authenticated local read + mutation checks were run successfully after fixing local schema
drift in the dev database volume.

Successful local end-to-end flow:

- authenticate through Clerk using a browser ticket sign-in
- `GET /api/v1/portfolios`
- create a specifically named smoke portfolio
- create a specifically named buy-and-hold strategy
- resolve a recent price-history window that actually exists in the database
- run a backtest
- verify the resulting backtest portfolio transactions

Observed successful local run:

- smoke portfolio created successfully
- smoke strategy created successfully
- smoke backtest completed successfully
- resulting transactions matched the expected simple buy-and-hold shape
  - 1 `DEPOSIT`
  - 1 `BUY`
  - 0 `SELL`

### Production Verification Results

Using a real production Clerk session, the same smoke flow was executed successfully
against:

- `https://zebutrader.com/api/v1`

Successful production checks:

- authenticated portfolio listing
- smoke portfolio create + balance read
- smoke strategy create
- smoke backtest create + detail read
- smoke backtest portfolio transaction read

Conclusion:

- the deployed backend behind `https://zebutrader.com/api/v1` is working
- authenticated integration behavior is substantially healthier than the live browser
  console errors suggest

### Deployment / Browser Issue Clarified

The current browser-facing production problem appears to be a deployment/configuration issue,
not a core backend-behavior issue.

Important observations:

- the deployed frontend bundle currently hardcodes:
  - `https://api.zebutrader.com/api/v1`
- authenticated smoke requests to `https://zebutrader.com/api/v1` work
- authenticated smoke requests to `https://api.zebutrader.com/api/v1` also work when sent
  directly from Node without browser CORS/preflight behavior
- but public `curl` checks to `https://api.zebutrader.com/health` and browser-style
  `OPTIONS` preflight requests still return generic `500` HTML responses

Interpretation:

- the API subdomain path is still misbehaving for browser/CORS/preflight traffic
- the frontend is currently pointing at the problematic subdomain
- switching production frontend API traffic back to same-origin `/api/v1` is likely the
  fastest user-visible fix, assuming the deployed frontend is rebuilt/redeployed correctly

### Fresh-DB Migration Follow-up

After PR #209 was opened, CI exposed one more important issue in the new Docker migration
flow:

- a brand-new PostgreSQL database could fail during Alembic upgrade because part of the
  historical migration chain still assumes core tables already exist
- specifically, the `a6a5412b5d02` migration tries to alter `portfolio_snapshots` before
  Alembic has ever created that table from scratch

Follow-up fix applied:

- `init_db()` now uses SQLModel `create_all()` for PostgreSQL only when the database does
  **not** yet have an `alembic_version` table
- this preserves the fresh-database bootstrap behavior older migrations still depend on,
  while still keeping migrated PostgreSQL databases on the Alembic path

This is a pragmatic compatibility fix, not the final ideal state. Long term, the
migration history should be normalized so a blank PostgreSQL database can be built purely
from Alembic without any startup bootstrap behavior.

### Additional Root Causes Found

#### 1. Local/Postgres schema drift risk

The repo was allowing SQLModel `create_all()` to run on startup for PostgreSQL-backed app
runs. That created a dangerous partial-schema state:

- old existing tables were not altered
- newly added tables were created
- Alembic history table could still be missing
- later `alembic upgrade head` could then fail trying to recreate earlier tables

Concrete local failure observed before fixes:

- `GET /api/v1/portfolios` failed with:
  - `column portfolios.portfolio_type does not exist`

Repo changes made:

- PostgreSQL startup now skips `create_all()` unless explicitly opted in
- local Docker dev flow now runs Alembic migrations

Note:

- any pre-existing local Docker DB volume created before this fix may still need a manual
  reset or repair/stamp

#### 2. Historical backtest data fetch limitation

The historical-fetch path for Alpha Vantage daily data was using the `compact` response mode
for all requests, which is only suitable for recent windows.

Repo changes made:

- historical fetches now select `full` output size for older backtest windows
- regression coverage added in unit tests

Remaining caveat:

- some older-range Alpha Vantage requests can still fail depending on the external API
  response or account limits
- the smoke test now avoids this by choosing a recent price-history window that is already
  available

### Recommended Next Steps From Here

1. Fix the production frontend deployment/config so the browser uses same-origin `/api/v1`
   instead of the problematic `api.zebutrader.com` path, then redeploy.
2. Inspect the `api.zebutrader.com` proxy/CORS behavior separately:
   - public `GET /health`
   - browser `OPTIONS` preflight handling
3. Update stale docs in:
   - `PROGRESS.md`
   - `BACKLOG.md`
   - `resume-from-here.md`
4. Decide whether to add a CI or scheduled smoke run for:
   - local/dev
   - production
5. Continue deeper backtest validation if desired:
   - DCA
   - moving-average crossover
   - compare expected transaction shapes against live API results
