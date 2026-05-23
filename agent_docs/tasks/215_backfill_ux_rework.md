# Task 215 — Backfill UX rework ("Catch up" model)

**Status**: Ready for implementation
**Owner**: backend-swe (single agent, backend + frontend)
**Author**: Tim Child (with Claude Opus 4.7)
**Created**: 2026-05-23
**Estimated effort**: ~1 day

---

## Overview

Replace the current operator-driven backfill UX (date-range picker per ticker, opaque progress) with a single "Catch up" action that fills `[ZEBU_HISTORY_EPOCH, today]` and surfaces real `BackfillTask` state on the page.

## Context

PR #279 (Phase J Layer 4) shipped the `/admin/data-coverage` page. Smoke-testing exposed three concrete issues:

1. **The date-range picker exposes a knob with no real effect.** Alpha Vantage's `TIME_SERIES_DAILY` is binary: `compact` (~100 bars, 1 call) or `full` (~20 years, 1 call). The adapter at `alpha_vantage_adapter.py:1246` already auto-picks `full` whenever the request spans > 90 days OR reaches > 90 days back. So picking `[2024-01-01 → today]` vs `[2010-01-01 → today]` costs the same one API call and returns the same `full` payload. The picker is friction for no reason.
2. **`gap_days_count` only counts *interior* gaps** — trading days inside `[coverage_start, coverage_end]` with no bar. Pre-`coverage_start` history doesn't count. So if a ticker's earliest bar is 2024-01-01 and the operator backfills back to 2010, the count stays the same (0 interior gaps). The page gives no signal that 14 years of new data just landed.
3. **No `BackfillTask` state surfaced on the page.** The page polls `/admin/data-coverage`, which only reads `price_history` aggregates. A `PENDING` / `RUNNING` task is invisible. Only `last_refresh` ticks on the 30s poll.

The mental model we want:

- **Operator-driven backfill = one-off per new ticker.** After it lands, the scheduled `refresh_active_stocks` job keeps it warm by fetching new daily bars.
- **L3 lazy backfill** (PR #277) already auto-enqueues when a backtest hits incomplete history.
- So this page is really for first-time setup of a new ticker or recovering after a scheduler outage.

## Architecture

### New env variable

`ZEBU_HISTORY_EPOCH` — ISO date (`YYYY-MM-DD`) that defines the earliest target date for backfills. Default `2015-01-01`.

Plumbed through the dependency layer at `backend/src/zebu/adapters/inbound/api/dependencies.py` next to the existing `ALPHA_VANTAGE_DAILY_CAP` knob (line ~580). Invalid value → app startup error with the standard config-validation pattern.

### Endpoint changes

**`POST /admin/data-coverage/backfill`** — request body becomes:

```json
{ "ticker": "AAPL" }
```

The `start_date` field is gone; the handler computes `start_date = ZEBU_HISTORY_EPOCH` and `end_date = today_utc()`. `priority` stays as a server default (`HIGH` for operator-driven). Idempotency on `(ticker, ZEBU_HISTORY_EPOCH, today)` still works via `find_existing`.

If existing operator code calls this endpoint with a `start_date` / `end_date` body, **return 422 with a clear message** — there is no live consumer (the only caller is the admin page in this repo) so the explicit break is correct.

**`GET /admin/data-coverage`** — per-ticker entries gain a `backfill_status` field:

```python
class TickerCoverageEntry(BaseModel):
    ticker: str
    coverage_start: str | None
    coverage_end: str | None
    last_refresh: str | None
    gap_days_count: int          # redefined (see below)
    target_epoch: str            # NEW — ISO date of ZEBU_HISTORY_EPOCH
    is_active: bool
    backfill_status: BackfillStatusInfo | None  # NEW
```

`BackfillStatusInfo` shape:

```python
class BackfillStatusInfo(BaseModel):
    task_id: UUID
    status: BackfillTaskStatus     # "pending" | "running" | "succeeded" | "failed"
    enqueued_at: str               # ISO timestamp
    error_message: str | None      # populated for FAILED
```

Populated by joining the most-recent `BackfillTask` row per ticker (terminal AND non-terminal). When the most-recent task is `SUCCEEDED` and older than 60 seconds, omit the field (treat as steady state). When non-terminal, always include. When `FAILED`, include for 24 hours so the operator can act.

Pure SQL — DataCoverageQueryHandler reads from both `price_history` aggregates and `backfill_task` table. Don't break the existing query's `O(distinct tickers)` complexity.

### `gap_days_count` redefinition

Current definition: trading days inside `[coverage_start, coverage_end]` with no bar.

New definition: trading days inside `[ZEBU_HISTORY_EPOCH, today_utc()]` with no bar.

So:

- Ticker with no data → `gap_days_count` = trading days from epoch through today (large number)
- Ticker covered from epoch contiguously → `gap_days_count` = 0
- Ticker covered 2024-01-01 → today with no interior gaps → `gap_days_count` = trading days from epoch through 2023-12-31

The metric now actually moves when a backfill lands.

The `_missing_calendar_days` helper in the AV adapter already does the head-gap/tail-gap math — same approach should work in the query handler, just bounded to `[epoch, today]` instead of `[requested_start, requested_end]`.

### Frontend changes

`frontend/src/pages/AdminDataCoverage.tsx`:

- **Remove the `BackfillForm` component entirely.** No date inputs, no submit button.
- **Replace the per-row "Backfill" button** with a "Catch up" button that POSTs `{ ticker }` directly. Use the same `useBackfillTicker` mutation but drop the date payload.
- **Add a status pill column** (or augment the existing Status column) so each row reflects `backfill_status` from the response. Mapping:
  - `null` → existing healthy/stale/gaps/no-data pill (unchanged)
  - `pending` → "Queued" pill (amber-soft)
  - `running` → "Catching up…" pill with subtle pulse (amber)
  - `succeeded` (within 60s window if backend keeps surfacing it) → "Caught up" pill (success-soft) — fades on next poll
  - `failed` → "Failed" pill (loss) with title-attr or expandable row showing `error_message`
- **Disable the Catch up button** while `backfill_status.status in {pending, running}` — it's already idempotent server-side but the UX should signal that.
- **Surface the epoch** on the page header so operators know what "catch up" means: `Target epoch: 2015-01-01` rendered as a `Caption` next to the existing copy.

### TypeScript types

`frontend/src/services/api/types.ts` — extend `TickerCoverageEntry`:

```typescript
export type BackfillTaskStatus = 'pending' | 'running' | 'succeeded' | 'failed'

export interface BackfillStatusInfo {
  task_id: string
  status: BackfillTaskStatus
  enqueued_at: string
  error_message: string | null
}

export interface TickerCoverageEntry {
  ticker: string
  coverage_start: string | null
  coverage_end: string | null
  last_refresh: string | null
  gap_days_count: number
  target_epoch: string
  is_active: boolean
  backfill_status: BackfillStatusInfo | null
}
```

`frontend/src/hooks/useDataCoverage.ts` — `useBackfillTicker` mutation payload becomes `{ ticker: string }`. Drop `start_date` / `end_date`.

## Implementation plan

### Phase 1 — Backend (single agent dispatch, ~half day)

1. Add `ZEBU_HISTORY_EPOCH` env (default `2015-01-01`) to dependencies module. Validate on read.
2. Update `BackfillRequest` model — remove `start_date` / `end_date`, keep `ticker`. Default `priority` server-side.
3. Update `admin_data_coverage_backfill` handler — compute `[epoch, today]` from the env. Update logging fields.
4. Extend `DataCoverageQueryHandler` to join most-recent `BackfillTask` per ticker. Return the `BackfillStatusInfo` payload when applicable per the rules above.
5. Redefine `gap_days_count` to count trading-day gaps inside `[epoch, today]`. Use `market_calendar` helper.
6. Update unit + integration tests:
   - `backend/tests/unit/application/queries/test_data_coverage.py` — new gap definition, new backfill_status payload
   - `backend/tests/integration/test_admin_data_coverage.py` — endpoint shape change, request shape change

### Phase 2 — Frontend (same agent, ~quarter day)

1. Update `types.ts` per above.
2. Update `useBackfillTicker` mutation signature.
3. Rip out `BackfillForm` component; replace per-row dialog with direct mutation call.
4. Add status-pill logic for the new `backfill_status` field.
5. Surface `target_epoch` on the page header.
6. Update `AdminDataCoverage.test.tsx` for the new shape.

### Phase 3 — E2E (same agent, light)

If an existing E2E spec touches the backfill flow (`backfill.spec.ts` or similar), update it. Otherwise no new E2E — the unit + integration coverage is enough.

## Testing strategy

- **Unit**: query handler with synthetic `price_history` and `backfill_task` rows; verify `gap_days_count` against a known calendar; verify `backfill_status` selection rules (most-recent, terminal vs non-terminal).
- **Integration**: end-to-end POST → check `BackfillTask` created with `[epoch, today]`; GET → check `backfill_status` populated when a task exists.
- **Frontend unit**: `AdminDataCoverage.test.tsx` covers Catch-up button click → mutation invocation, status pill rendering for each `BackfillTaskStatus`, button disabled while running.
- **No new E2E** required unless updating an existing spec.

## Success criteria

- [ ] `ZEBU_HISTORY_EPOCH` env wired through with a sensible default.
- [ ] `POST /admin/data-coverage/backfill` accepts `{ ticker }` only; rejects bodies with `start_date` / `end_date` as 422.
- [ ] `GET /admin/data-coverage` returns `backfill_status` per the rules.
- [ ] `gap_days_count` reflects gaps inside `[epoch, today]`.
- [ ] Frontend has no date-range picker; Catch up button posts directly.
- [ ] Status pill reflects backfill task state in real time (next 30s poll).
- [ ] All existing tests pass; new tests cover the new behaviour.
- [ ] `task ci` green.

## Non-goals

- **Don't** add cancellation for in-flight backfill tasks — out of scope.
- **Don't** add a per-day quota visualisation — operator can read the existing `ALPHA_VANTAGE_DAILY_CAP` from logs.
- **Don't** auto-trigger Catch up for tickers with gaps — operator action stays explicit.
- **Don't** touch the L3 lazy-backfill machinery — it already does the right thing on its own.

## References

- `docs/planning/agent-platform-next-steps.md` §1.2 — original backfill carry-over
- PR #279 — admin data-coverage page (current state)
- PR #277 — L3 lazy backfill
- PR #275 — L2 activation-time pre-warm (uses the same `BackfillTask` machinery)
- `backend/src/zebu/adapters/outbound/market_data/alpha_vantage_adapter.py:1246` — `_select_daily_history_outputsize` (proves `full` is one call)
- `backend/src/zebu/adapters/inbound/api/admin_data_coverage.py` — current router
- `backend/src/zebu/application/queries/data_coverage.py` — current query handler
- `frontend/src/pages/AdminDataCoverage.tsx` — current page

## Agent assignment

Single `backend-swe` agent. The frontend portion is small, mechanical, and tightly coupled to the backend response shape — splitting between two agents would introduce coordination overhead for no benefit.
