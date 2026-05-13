# Task 212 — Data warmth subsystem (Phase J — fix-and-stabilize)

**Status**: Scoped, not started
**Branch (per layer)**: `feat/j-data-warmth-L1-job-health`, `feat/j-data-warmth-L2-prewarm`, `feat/j-data-warmth-L3-lazy-backfill`, `feat/j-data-warmth-L4-freshness-ui`
**Agent**: `backend-swe` (L1–L3) + `frontend-swe` (L4)

## Overview

Replace the current "manual `POST /analytics/prices/refresh` when a backtest 404s on AAPL" flow with a real subsystem that:

1. **Detects when scheduled data jobs fail or fall behind** (Layer 1 — job-health observability)
2. **Pre-fetches historical bars the moment we know a user needs them** (Layer 2 — activation-time pre-warm)
3. **Returns actionable errors + heals the data on partial-miss** (Layer 3 — lazy backfill at the API boundary)
4. **Surfaces per-ticker coverage to the operator** (Layer 4 — data freshness UI)

Origin: §1.2 ("AAPL OHLC historical data missing on prod") and §1.3 ("the backfill job has lapsed") of `docs/planning/agent-platform-next-steps.md`. The 2026-05-10 smoke-test `ExplorationTask 450cb185` exposed that we have no way to detect the cron lapsing, no way to recover at backtest-time, and no operator view of data coverage. This task closes all three gaps as one subsystem because the four layers share the same domain model (`JobExecution`, `BackfillTask`) and reading them as independent tickets risks inconsistent design.

## Architecture

### Layer 1 — Job-health observability

**Goal**: Every scheduled job emits an audit row on each run. Endpoint exposes the latest status per job. Operator can detect lapsed jobs before downstream failures.

**New domain**:

- `JobExecution` value object — `job_name: str`, `started_at: datetime`, `finished_at: datetime | None`, `status: JobExecutionStatus`, `error_message: str | None`, `metadata: dict[str, str]` (free-form, e.g., `{"tickers_refreshed": "12"}`).
- `JobExecutionStatus = RUNNING | SUCCEEDED | FAILED`.

**New port**:

- `JobExecutionRepositoryPort` in `application/ports/`: `record_start(job_name, metadata) -> JobExecution`, `record_finish(job_execution, status, error_message?, metadata?)`, `latest(job_name) -> JobExecution | None`, `list_recent(job_name?, limit) -> list[JobExecution]`.

**New adapter**:

- `SQLModelJobExecutionRepository` in `adapters/outbound/database/`.
- New table `job_executions` via migration `j001_job_executions`.

**Wiring** — `infrastructure/scheduler.py` gets a small `@with_job_audit("refresh_active_stocks")` decorator (in `infrastructure/job_audit.py`) that wraps each of the four scheduler job handlers (`refresh_active_stocks`, `calculate_daily_snapshots`, `execute_active_strategies`, `evaluate_triggers`). The decorator:

1. Opens a session, instantiates the repo, calls `record_start`.
2. Runs the wrapped coroutine inside a `try/except`.
3. On success: `record_finish(SUCCEEDED, metadata={duration_seconds, ...})`.
4. On exception: `record_finish(FAILED, error_message=str(exc)[:500])` then `raise`.

The decorator MUST use its OWN session (not share with the wrapped job's session) so a job's rollback doesn't drop the audit row.

**Endpoint**:

- `GET /api/v1/admin/jobs/health` (admin-gated — same auth pattern as `/admin/triggers`). Returns:

  ```json
  {
    "jobs": [
      {
        "job_name": "refresh_active_stocks",
        "last_run": "2026-05-11T00:00:03Z",
        "last_status": "succeeded",
        "duration_seconds": 47,
        "expected_cadence_seconds": 86400,
        "is_stale": false,
        "stale_threshold_seconds": 172800
      },
      ...
    ]
  }
  ```

- "Stale" is computed: `now - last_run > stale_threshold_seconds`. The thresholds default to `2× expected_cadence` per job (so a daily job is stale at 48h, a 15-minute job stale at 30 min) and are encoded in a `JOB_HEALTH_THRESHOLDS` constant.

**Out of scope for L1**: paging this to Slack / email. Operator polls the endpoint or visits the admin UI (Layer 4).

### Layer 2 — Activation-time pre-warm

**Goal**: When a user calls `POST /api/v1/activations`, the strategy's tickers' historical bars are eagerly fetched for the window the strategy will need. The first backtest after activation cannot 404 because the data is already in Postgres.

**Required window** — computed from strategy params:

- For DCA / MA strategies: `end = today`, `start = today - (lookback_days + indicator_window_days + 30 buffer)`.
- For other strategy types: pessimistic default of 5 years.

**New service** — `application/services/historical_data_prewarmer.py`:

- `prewarm(tickers, start_date, end_date, priority="low") -> PrewarmResult` with `succeeded: list[Ticker]`, `failed: list[tuple[Ticker, str]]`, `skipped: list[Ticker]` (skipped = already complete in DB).
- Internally calls `market_data.get_price_history` for each ticker in series, respecting the existing rate limiter. `priority="high"` requests pre-empt the daily cap (relevant for paid AV); `priority="low"` defers if the daily cap is hit.

**New port + adapter**:

- `BackfillTaskRepositoryPort` — persists `BackfillTask(id, ticker, start_date, end_date, priority, status, created_at, finished_at, error_message)` so we can audit + retry. Status: `PENDING | RUNNING | SUCCEEDED | FAILED`.
- `SQLModelBackfillTaskRepository`.
- Migration `j002_backfill_tasks`.

**Wiring**:

- `ActivateStrategyCommand` handler — after the activation is persisted, fires a background `asyncio.create_task(prewarmer.prewarm(...))`. Failure is logged but does NOT fail the activation request. The activation returns 201 immediately; the prewarm runs out-of-band.
- The scheduler also picks up `BackfillTask(status=PENDING)` rows on each `refresh_active_stocks` cycle and runs them, so any prewarms that failed transiently get retried.

**Configuration**:

- `ALPHA_VANTAGE_DAILY_CAP` (default `25`). Set higher (or `0` = unbounded) when on paid AV. Plumbed into the existing token-bucket rate limiter's day window.
- `PREWARM_DEFAULT_PRIORITY` (default `low`). Activation-driven prewarms use this.

### Layer 3 — Lazy backfill at the API boundary

**Goal**: When `get_price_history` returns incomplete data, the API gives the caller something actionable instead of 404, and we kick off a fetch.

**New domain exception**:

- `IncompleteHistoricalDataError(ticker, requested_range, available_range, missing_days_count)` in `application/exceptions.py`.

**Adapter change** — `alpha_vantage_adapter.py:654` (`get_price_history`):

After all three tiers (Redis → Postgres → API) are exhausted, if the result set covers a strict subset of `[start, end]` and the ticker IS valid (we did get *some* data back), raise `IncompleteHistoricalDataError` instead of returning partial data silently.

The decision tree:

| Cache+DB+API result | Action |
|---|---|
| Complete range | Return list normally |
| Ticker valid, partial range | Enqueue `BackfillTask` for missing range, raise `IncompleteHistoricalDataError` |
| Ticker not found (AV said so) | `TickerNotFoundError` (unchanged) |
| Rate limit + no cache | `MarketDataUnavailableError` (unchanged) |

**API layer** — `backtests.py` catch-all already maps unknown exceptions to 5xx; add an explicit branch for `IncompleteHistoricalDataError` → `503 Service Unavailable` with:

```json
{
  "status": "fetching",
  "ticker": "AAPL",
  "missing_range": {"start": "2024-01-01", "end": "2024-04-30"},
  "eta_seconds": 60,
  "retry_after_seconds": 60
}
```

And `Retry-After: 60` header.

**Frontend handling**: `useBacktestRun` mutation surfaces the 503-fetching response as a distinct state with a "loading historical data" indicator + auto-retry after `retry_after_seconds`. Add a `useBacktestPolling` hook variant if the existing query infra doesn't already auto-retry on 503.

### Layer 4 — Data freshness UI

**Goal**: Operator (you) can see at a glance which tickers have data coverage, when the last refresh was, what the gaps are, and trigger a backfill from the UI.

**Endpoint** — `GET /api/v1/admin/data-coverage`:

```json
{
  "tickers": [
    {
      "ticker": "AAPL",
      "coverage_start": "2019-01-02",
      "coverage_end": "2026-05-10",
      "last_refresh": "2026-05-10T00:00:47Z",
      "gap_days_count": 0,
      "is_active": true
    },
    {
      "ticker": "MSFT",
      "coverage_start": "2023-06-01",
      "coverage_end": "2026-05-09",
      "last_refresh": "2026-05-09T00:00:51Z",
      "gap_days_count": 12,
      "is_active": false
    }
  ]
}
```

`is_active = ticker ∈ (watchlist ∪ recent trades)`. `gap_days_count = number of trading days missing inside [coverage_start, coverage_end]` — distinct from missing-from-start (we don't count "we just don't have pre-2019 data" as a gap).

**Endpoint** — `POST /api/v1/admin/data-coverage/backfill`:

Request: `{ ticker, start_date, end_date, priority }`. Creates a `BackfillTask(status=PENDING)`. Returns the task ID. Idempotent on `(ticker, start_date, end_date)` — if a PENDING/RUNNING task already exists for the same range, return the existing one.

**Admin UI**:

- New route `/admin/data-coverage` (admin-only).
- Table: ticker, coverage range, last refresh (relative time), gap count, status pill, "Backfill" button.
- Row click → modal with date-range picker → POST to backfill endpoint.
- Live status: poll `/admin/jobs/health` and the backfill task list every 30 seconds while page open.
- Add a sidebar entry in `<AdminLayout>` for "Data coverage" alongside the existing "Triggers" / "API keys" entries.

## Implementation plan

### Layer 1 (1 PR, ~1 day) — `backend-swe`

1. Add domain VO `JobExecution` + status enum.
2. Port + SQL adapter + migration `j001_job_executions`.
3. `@with_job_audit` decorator (new file `infrastructure/job_audit.py`).
4. Apply decorator to all four scheduler job handlers.
5. `GET /api/v1/admin/jobs/health` endpoint + `JOB_HEALTH_THRESHOLDS`.
6. Unit tests for the decorator (success path, exception path, decorator session isolation).
7. Integration tests for the endpoint (auth gating, stale flag computation, succeeded vs failed rows).

**Done when**: `task ci` green; running `task dev:backend`, hitting any scheduler job, and reading `/admin/jobs/health` shows the audit row.

### Layer 2 (1 PR, ~1.5 days) — `backend-swe`

1. Domain entity `BackfillTask` + status enum.
2. Port + SQL adapter + migration `j002_backfill_tasks`.
3. `HistoricalDataPrewarmer` service.
4. `ALPHA_VANTAGE_DAILY_CAP` env wired into `RateLimiter` (currently hardcoded; needs the constructor signature updated and the bootstrap in `dependencies.py` reading the env).
5. `ActivateStrategyCommandHandler` fires `asyncio.create_task(prewarmer.prewarm(...))` post-persist.
6. `refresh_active_stocks` cron extended to pick up pending `BackfillTask` rows after its primary refresh loop.
7. Unit tests for the prewarmer (success, partial failure, skip-when-complete).
8. Integration test: activate a strategy, assert `BackfillTask` row appears, assert prewarm runs and updates status.

**Done when**: activating a strategy on a fresh ticker triggers a visible BackfillTask that completes within the cycle.

### Layer 3 (1 PR, ~1 day) — `backend-swe`

1. `IncompleteHistoricalDataError` exception.
2. `alpha_vantage_adapter.get_price_history` updated to detect partial coverage and raise.
3. Adapter enqueues a `BackfillTask` for the missing range BEFORE raising.
4. `backtests.py` (and `prices.py` if it surfaces `get_price_history`) catches the exception → 503 with the structured body.
5. Frontend: `useBacktestRun` recognises 503-fetching, retries after `retry_after_seconds` (max 3 attempts), exposes a `dataFetching: boolean` state for the UI.
6. Component test for the loading affordance.
7. Integration test: backtest a ticker with no coverage → first call gets 503 → poll → eventually 200.

**Done when**: a fresh ticker backtest no longer 404s; instead it shows "loading historical data…" and succeeds when the backfill completes.

### Layer 4 (1 PR, ~1.5 days) — `frontend-swe` (+ small backend additions)

1. Backend: `GET /api/v1/admin/data-coverage` endpoint backed by a new `DataCoverageQueryHandler` that joins `price_history` rows with watchlist/transaction tickers.
2. Backend: `POST /api/v1/admin/data-coverage/backfill` (delegates to `BackfillTask` port from L2).
3. Frontend: new route + page + table component + backfill modal + sidebar entry.
4. Component tests + Playwright happy-path test.

**Done when**: visiting `/admin/data-coverage` shows the table, clicking "Backfill" on a ticker with a known gap creates a task that completes and the gap disappears.

## Testing strategy

**Unit (`tests/unit/`)**:

- `JobExecution` value object semantics (status transitions, stale calculation).
- `HistoricalDataPrewarmer` behavior — mock the `MarketDataPort` at the port boundary.
- Decorator behavior — verify session isolation, exception propagation, status mapping.
- `IncompleteHistoricalDataError` raise conditions in the AV adapter (mock the API client at the HTTP boundary, not internal helpers).

**Integration (`tests/integration/`)**:

- End-to-end scheduler job → audit row written → endpoint returns it.
- End-to-end activation → BackfillTask row → prewarm completes → coverage visible.
- End-to-end backtest → 503-fetching → retry → 200 (using the in-memory adapter pre-seeded with a partial range).
- Admin endpoint auth: 401 for unauth, 403 for Clerk non-admin, 200 for admin.

**E2E (Playwright)**:

- Admin data-coverage page renders.
- "Backfill" button click → status pill flips → row updates (smoke only; deep coverage is in integration).

## Success criteria

- All four endpoints (`/admin/jobs/health`, `/admin/data-coverage`, the backfill POST, and the existing `/analytics/prices/refresh` already in place) are documented in the OpenAPI schema.
- Operating manual gets a new section: "Recovering from a lapsed data refresh" — references `/admin/jobs/health` as the first stop, the data-coverage page as the second, the backfill button as the third.
- `task ci` green across all four PRs.
- Zero new `Any` / `any`. No type-checker suppressions.
- The 2026-05-10 failure mode (smoke test 404 on AAPL backtest with no recovery path) is impossible: activation pre-warms or, failing that, the 503-with-Retry-After heals on retry.

## Out of scope / future

- Slack/email paging on `is_stale=true`. Deferred until we have a real alerting layer.
- `EarningsCalendarPort` real adapter — blocked on paid AV (the AV `EARNINGS` endpoint is premium-gated).
- Bulk backfill of multi-decade data for backtest research — current design is per-ticker per-window. A future "warm the universe" job can layer on top of `BackfillTask`.
- Intraday data — daily-only; intraday is a separate Phase if/when product needs it (also paid-AV-gated).

## References

- `docs/planning/agent-platform-next-steps.md` §1.2, §1.3 (problem statement)
- `docs/architecture/principles.md` (Clean Architecture rules)
- `backend/src/zebu/infrastructure/scheduler.py:162` — the cron that *should* keep data fresh
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py:654` — current `get_price_history` flow
- `backend/src/zebu/application/services/historical_data_preparer.py` — existing pre-fetch for backtests; do not confuse with the new prewarmer (preparer = at-backtest-time; prewarmer = at-activation-time)
- `backend/src/zebu/infrastructure/rate_limiter.py:41` — token-bucket with minute + day windows; L2 makes the day window configurable
