# Security Audit — Phase B1

**Date**: 2026-05-09
**Auditor**: quality-infra
**Slug**: sec
**Scope**: API routers, auth adapters, DB query patterns, secret handling, frontend auth flow.

---

## Summary

| Priority | Count | Headline |
|---|---|---|
| **P0** | **2** | Two unauthenticated admin endpoints + cross-portfolio backfill bypass on a `CurrentUserDep`-protected endpoint |
| P1 | 4 | TODO admin gating on backfill; debug router (PII-adjacent) is fully open; in-memory auth fallback in prod-shaped path; uniform absence of API-key story for Phase C |
| P2 | 4 | No backend rate limiting on user endpoints; CORS allow_methods/headers `*`; sensitive identifiers logged at INFO; CI lacks `pip-audit`/secret scan; minor input/enum issues |
| P3 | 1 | `transaction_type` enum lookup raises `KeyError` (DX, low impact) |

**Total: 11 findings.**

**Top concern (P0-1)**: `POST /api/v1/analytics/prices/refresh` and `POST /api/v1/analytics/snapshots/daily` are publicly callable with no auth dependency at all. Anyone on the internet can trigger Alpha Vantage refreshes and global snapshot recompute. With Phase C agents (programmatic write access) this is the exact class of endpoint they will inherit/extend.

---

## P0 — Blockers

### P0-1 — Two admin endpoints have NO authentication at all

**File**: `backend/src/zebu/adapters/inbound/api/analytics.py`

Lines 350–388 (`trigger_price_refresh`) and 391–423 (`trigger_daily_snapshots`) are mounted on `admin_router` (`/api/v1/analytics/prices/refresh`, `/api/v1/analytics/snapshots/daily`). Both have:

- No `CurrentUserDep`
- No `Depends(...)` for auth at all
- A `# TODO: Add admin authentication check when auth is implemented` comment

These are reachable on production at `https://zebutrader.com` without a Bearer token. Concrete impact:

- Any unauthenticated caller can trigger `refresh_active_stocks(config)` — burns Alpha Vantage rate limit (5/min, 500/day on free tier) for the whole tenancy. Trivial DoS of paid market data.
- Any unauthenticated caller can trigger `snapshot_job.run_daily_snapshot()` — recomputes snapshots for **all portfolios across all users**, hits the DB hard, and on failure leaks stack traces (see P1-3).

**Reproduces with**: `curl -X POST https://zebutrader.com/api/v1/analytics/prices/refresh` — no headers required.

**Fix**: at minimum, add `current_user: CurrentUserDep` to both handlers. Then either (a) gate with an admin allowlist (env-driven `ADMIN_USER_IDS`) or (b) move them out of the public router into an internal-only path that the scheduler calls in-process. Note: `BACKLOG.md` lists this as "Priority: LOW — production app is currently single-user," but with Phase C agents shipping write access via API key, low-priority gating is the wrong call.

---

### P0-2 — Snapshot backfill missing ownership check

**File**: `backend/src/zebu/adapters/inbound/api/analytics.py:280–343`

`POST /api/v1/portfolios/{portfolio_id}/snapshots/backfill` injects `CurrentUserDep` (line 286) but never uses it:

```python
# TODO: Add admin authentication check
# TODO: Verify user owns the portfolio
```

…and then calls `snapshot_job.backfill_snapshots(portfolio_id, …)` for any `portfolio_id` the caller types. **User A can recompute snapshots for User B's portfolio** as long as A is authenticated (no admin check, no ownership check). The endpoint is documented as "Admin only" but enforces nothing.

The handler also raises `ValueError` for "Portfolio not found", but for an existing-but-not-owned portfolio it will happily run and generate snapshot rows. Snapshot rows are `(portfolio_id, date)` keyed — so this is also a write-side bypass on someone else's analytics history.

**Fix**: call the same pattern used in `portfolios.py::_verify_portfolio_ownership` (line 601) before invoking the job, OR gate the whole endpoint as admin-only.

**Phase C lens**: agents will get an API-key identity. If this endpoint stays as-is, an agent's key for User A's account can rewrite User B's snapshots. Cross-tenant write bleed = audit nightmare.

---

## P1 — Phase-C inheritors

### P1-1 — `/api/v1/debug/*` router is fully open

**File**: `backend/src/zebu/adapters/inbound/api/debug.py`

Three endpoints (`/debug`, `/debug/scheduler`, `/debug/price-cache/{ticker}`) have no auth dependency:

- `/debug` redacts API keys (good — `_redact_api_key`) but exposes `APP_ENV`, Python/FastAPI versions, DB URL with redacted password (still leaks user/host), Redis URL, and "configured" status of Clerk + Alpha Vantage. This is fingerprintable info that helps a targeted attacker.
- `/debug/scheduler` exposes job IDs, names, and next run times — useful for timing attacks.
- `/debug/price-cache/{ticker}` exposes raw price history rows from the DB. Not user PII, but still data the auth boundary should mediate.

The module docstring says "*Security: This endpoint redacts sensitive information*" — but never restricts who can call it. Redaction is necessary but not sufficient.

**Fix**: gate the whole router behind `CurrentUserDep` + admin allowlist, or include only when `APP_ENV != "production"`. The `include_router(debug_router, prefix="/api/v1")` in `main.py:124` is unconditional.

### P1-2 — In-memory auth adapter falls through in production

**File**: `backend/src/zebu/adapters/inbound/api/dependencies.py:100–119`

```python
clerk_secret_key = os.getenv("CLERK_SECRET_KEY", "")
if clerk_secret_key and clerk_secret_key != "test":
    return ClerkAuthAdapter(secret_key=clerk_secret_key)
return InMemoryAuthAdapter()
```

If `CLERK_SECRET_KEY` is unset or accidentally `""` (e.g., the `.env` line gets commented out, or the value happens to be `"test"`), every endpoint silently falls back to `InMemoryAuthAdapter()` with **no users registered**. Every `verify_token` call then raises `InvalidTokenError("Invalid token")` and returns a clean 401. So the failure mode is "no one can log in" rather than "anyone can" — but:

1. The fallback is implicit. A misconfig at deploy time produces an ambiguous "auth broken" symptom rather than a hard startup failure.
2. If anyone ever calls `InMemoryAuthAdapter.add_user(...)` from app code (as a "demo mode" or "test seed"), this becomes a bypass.

**Fix**: in production (`APP_ENV=production`), require a non-empty `CLERK_SECRET_KEY` at startup. Fail fast in `lifespan()` rather than swap to the test adapter.

### P1-3 — Error responses leak internal exception messages

**File**: `backend/src/zebu/adapters/inbound/api/analytics.py:340–343, 386–388, 419–423`

```python
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail=f"Backfill failed: {str(e)}",
) from e
```

The same pattern recurs. Generic `except Exception as e` blocks return `str(e)` to the client. For SQLAlchemy / asyncpg exceptions, that string can include table names, column names, and parts of the query. Same in `backtests.py` indirectly via 503 detail strings carrying `InsufficientHistoricalDataError` content.

`error_handlers.py` is well-structured for *known* domain exceptions (`InvalidPortfolioError` → 400 with safe `str(exc)`). The leaks are in route-local `except Exception` paths.

**Fix**: log the exception with `exc_info=True` and return a generic message. Keep the structured-error pattern from `error_handlers.py` consistent.

### P1-4 — No API-key issuance / rotation story scoped

This is a forward-looking note rather than a code finding: Phase C is going to introduce programmatic write-access for agents. The current `AuthPort` interface has only `verify_token` + `get_user`. There is no:

- API-key model / table
- Issuance endpoint
- Rotation / revocation endpoint
- Per-key scope (read-only vs write, allowed portfolios, rate limit class)
- Audit log of which key performed which write

If P0-1 / P0-2 ship with API-key extension as a follow-up, agents will inherit unauthenticated paths into production. Suggest scoping the API-key surface in the same task that lands the Phase B fixes, not in Phase C.

---

## P2 — Hardening

### P2-1 — No per-user rate limiting on backend endpoints

`RateLimiter` exists (`backend/src/zebu/infrastructure/rate_limiter.py`) but is *only* wired into the Alpha Vantage outbound adapter (`dependencies.py:232`). User-facing endpoints — including `POST /portfolios/{id}/trades`, `/backtests`, `/snapshots/backfill` — have no per-user or per-IP limit. With agents about to drive these endpoints in loops, a buggy agent can hammer the DB. Add a per-user limiter as middleware (or a `Depends`-based check) keyed on `current_user`.

### P2-2 — CORS `allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=True`

**File**: `backend/src/zebu/main.py:110–116`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,   # OK — env-driven, not "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins` is restrictive (good) but pairing `allow_credentials=True` with wildcards on methods/headers is loose. Tighten to `["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]` and explicit headers (`Authorization`, `Content-Type`, `Accept`). Also: `CORS_ORIGINS=http://localhost:3000,http://localhost:5173` in `.env.production.example` — production deploy needs this overridden to the real origin (`https://zebutrader.com`); not enforced.

### P2-3 — User IDs and portfolio IDs logged at INFO

**Files**: `transactions.py:76–82, 89–92, 99–104`, `portfolios.py:614–615`, `analytics.py:320–323`, `clerk_adapter.py:100`

Examples:

```python
logger.info(f"Authenticated user ID: {user_id}")
logger.info(f"Verifying portfolio ownership: portfolio_id={portfolio_id}, user_id={user_id}")
```

Clerk user IDs and portfolio UUIDs aren't classical PII, but they're stable user identifiers in production logs. Combined with `logger.warning("Unauthorized portfolio access attempt", … owner_id=portfolio.user_id)` (transactions.py:99), these logs become a relationship graph. Keep at DEBUG, not INFO. Also the `f"Authenticated user ID: {user_id}"` line should go away — the structured-logging middleware already binds `user_id` if needed.

### P2-4 — CI runs `npm audit` (advisory) but no `pip-audit`, no secret scan

**File**: `.github/workflows/ci.yml:101–104`

`npm audit --audit-level=moderate` runs `continue-on-error: true`. Backend has zero dependency scan. No `gitleaks` / `trufflehog` / `detect-secrets` step on pre-commit either (just `detect-private-key`). For Phase C, adding `pip-audit` and a secret scanner is cheap insurance.

### P2-5 — `trigger_price_refresh` instantiates a default `SchedulerConfig()` and runs a global job

`analytics.py:373–377` — even gated for admin, this lets an admin trigger a global refresh on demand with default config. Combined with no rate limit (P2-1), it's a foot-gun. Consider locking to a max-frequency on the endpoint itself.

---

## P3 — Defer

### P3-1 — `transaction_type` query param raises `KeyError`

**File**: `transactions.py:115`

`tx_type_filter = TransactionType[transaction_type]` — if the caller passes an invalid string, `KeyError` bubbles up to the generic `except Exception` block (line 169) and gets logged + reraised as a 500. Should be a 400 / 422 with a friendly message. Low-impact — the input is already arbitrary.

---

## What was checked and is OK

- `.gitignore` covers `.env`, `.env.local`, `.env.production`, `.env.proxmox` — no secrets committed (verified with `git ls-files | grep .env` returning only `.env.development` and `.env.production` under `frontend/`, both containing only `VITE_API_BASE_URL`).
- No raw SQL with f-strings anywhere in `backend/src/zebu/`. All DB access uses SQLModel `select(...).where(Model.column == value)` — parameterized.
- No `dangerouslySetInnerHTML` in `frontend/src/`.
- No backend HTML responses; all routes return JSON via Pydantic.
- `_redact_api_key` in `debug.py` correctly truncates secrets — the issue is *where* the endpoint is exposed, not redaction quality.
- Clerk JWT verification properly extracts `sub` from payload (not from `request_state.user_id`, which can be wrong) — `clerk_adapter.py:90–98`.
- Pydantic schemas cover all request bodies in `portfolios.py`, `backtests.py`, `strategies.py`, `prices.py`. No raw `dict` request parameters except `strategy.parameters` (intentionally polymorphic, validated per `strategy_type` at `strategies.py:96–186`).
- Ownership is correctly enforced on all `/portfolios/{id}/*` endpoints under `portfolios.py` and `transactions.py` (404 on not-owned, 403 elsewhere). Backtest and strategy endpoints also verify `user_id` match.
- Pre-commit hook `detect-private-key` runs on commit (catches PEM-formatted keys).

---

## Recommended Phase B2 fix order

1. **P0-1**: Add auth + admin gate to the two `admin_router` endpoints in `analytics.py`. (~30 min)
2. **P0-2**: Add ownership verification in `backfill_portfolio_snapshots`. (~15 min)
3. **P1-1**: Gate `/debug/*` behind admin (or env-conditional include). (~15 min)
4. **P1-2**: Fail-fast on missing `CLERK_SECRET_KEY` when `APP_ENV=production`. (~10 min)
5. **P1-3**: Replace `f"...: {str(e)}"` patterns with logged + generic responses. (~30 min)
6. **P1-4**: Scope an API-key auth task spec under `agent_docs/tasks/2NN_api_key_auth.md` *before* Phase C work begins.
7. P2 items: bundle into a single hardening PR; pre-commit `gitleaks` is a one-line add, `pip-audit` is a 3-line CI step.

P0 + P1 fixes together are roughly ~2–3 hours of focused work and unblock Phase C cleanly.
