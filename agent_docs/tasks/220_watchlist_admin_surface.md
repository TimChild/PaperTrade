# Task 220 — Watchlist admin surface (Pin / Unpin from data-coverage page)

**Status**: Ready for implementation
**Owner**: backend-swe (single agent, backend + frontend — same pattern as Task 215)
**Author**: Tim Child (with Claude Opus 4.7)
**Created**: 2026-05-24
**Estimated effort**: ~1 day

---

## Overview

Expose `ticker_watchlist` editing to admins via the existing `/admin/data-coverage` page. Operators currently have no way to keep a ticker refreshed — the active-tickers set is computed as `union(watchlist_active, recently_traded_30d)`, but `WatchlistManager.add_ticker` is never called from production code. So in practice, the watchlist is empty and tickers only stay refreshed for 30 days after the last trade. This task closes that gap.

## Context

`backend/src/zebu/adapters/outbound/repositories/watchlist_manager.py` has the manager primitives — `add_ticker(ticker, priority=...)`, `remove_ticker(ticker)`, `get_all_active_tickers()`. They're consumed by `refresh_active_stocks` in `backend/src/zebu/infrastructure/scheduler.py:207` but **NOT exposed via any API or UI**.

The `/admin/data-coverage` page (Task 215, PR #296) already shows every ticker the system knows about, with an `is_active: bool` derived from the union above. Operators can see WHICH tickers are active but not HOW each one got there or how to add new ones.

Tim's call (2026-05-24): integrate watchlist editing into the existing data-coverage page rather than a separate admin page. One mental model.

## Design decisions (resolved 2026-05-24)

1. **Pin is additive, not authoritative.** Adding a ticker to the watchlist does NOT change the union semantic — the scheduler still refreshes anything in `watchlist_active ∪ recently_traded_30d`. Pinning just ensures the ticker stays in the set after the 30-day trade window lapses. Unpinning doesn't remove a recently-traded ticker from the refresh set.

2. **`priority` field is hidden from v1 UI.** The watchlist's `priority` column exists in the schema but `refresh_active_stocks` doesn't currently consult it — it's dead weight until the scheduler's logic uses it. UI hides; API accepts the default (100). Spec'd as a follow-up if/when the scheduler uses priority.

3. **Response field shape**: extend `TickerCoverageEntry` with `is_watchlisted: bool` (new) alongside the existing `is_active: bool`. A discriminated `source` enum would have been ambiguous because a ticker can be simultaneously watchlisted + traded; two orthogonal booleans is cleaner.

## Architecture

### New endpoints

**`POST /admin/watchlist`** — body `{ticker: string}`. Calls `WatchlistManager(session).add_ticker(Ticker(symbol), priority=100)`. Returns 201 with `{ticker, is_watchlisted: true}` on add. Idempotent — POSTing an already-pinned ticker returns the existing state without raising.

**`DELETE /admin/watchlist/{ticker}`** — calls `WatchlistManager(session).remove_ticker(Ticker(symbol))`. Returns 204 on success. 404 if the ticker isn't in the watchlist (idempotency cost — operator can tell if their action did anything).

Both endpoints are admin-gated via the existing `AdminUserDep` (Clerk allowlist), matching `/admin/data-coverage` and `/admin/jobs`. Both routes log a structured `admin_watchlist_added` / `admin_watchlist_removed` event with `admin_user_id` + `ticker` for the audit trail.

Note: `WatchlistManager.add_ticker` already updates priority if the ticker already exists with a lower priority — for our purposes (single fixed priority=100), this is a no-op on existing rows.

### Response shape change

`TickerCoverageEntry` (`backend/src/zebu/application/queries/data_coverage.py`) gains:

```python
is_watchlisted: bool  # NEW — True iff the ticker has an active row in ticker_watchlist
```

The query handler must read the watchlist table directly (or via `WatchlistManager.get_all_active_tickers()`) and stamp this on each entry. The existing `is_active` semantic doesn't change.

API request schema (`TickerCoverageEntry` in `backend/src/zebu/adapters/inbound/api/admin_data_coverage.py`) gains the same field with a Pydantic `Field` description.

### Frontend changes

`frontend/src/pages/AdminDataCoverage.tsx`:

- New column between "Status" and "Action": **Pin** indicator. When `is_watchlisted=true`, show a small pin glyph (or just text "Pinned" — match the editorial aesthetic; consult `PortfolioCard.tsx` and `AdminDataCoverage`'s existing pill styles for tone).
- The existing "Action" cell adds a second button alongside "Catch up": **Pin** (when `is_watchlisted=false`) or **Unpin** (when `is_watchlisted=true`). Single click; idempotent server-side.
- Pin/Unpin invokes a new mutation hook `useWatchlistMutation` that POSTs or DELETEs and invalidates the data-coverage query so the row re-renders within the next poll.
- Loading state: button shows a tiny spinner while the request is in-flight; row stays usable for other actions.
- Error state: toast with the error message (same pattern as the existing Catch up error handling).
- Disabled state: while Pin/Unpin for this row is in-flight (track via `mutation.variables?.ticker === row.ticker` per the PR #296 follow-up pattern).

`frontend/src/services/api/types.ts` — add `is_watchlisted: boolean` to `TickerCoverageEntry`; add request / response types for the new endpoints.

`frontend/src/services/api/admin.ts` — add `watchlist.add(ticker)` and `watchlist.remove(ticker)`.

`frontend/src/hooks/useDataCoverage.ts` — add `useWatchlistMutation` returning a `UseMutationResult` over the new endpoints.

## Implementation plan

### Phase 1 — Backend (~half day)

1. **Endpoint module** `backend/src/zebu/adapters/inbound/api/admin_watchlist.py` (new) — two routes, admin-gated. Wire into the FastAPI app via `main.py` or `__init__.py` per the existing admin-router pattern (read how `admin_data_coverage` and `admin_jobs` are wired).
2. **Query handler extension** — `DataCoverageQueryHandler` (`backend/src/zebu/application/queries/data_coverage.py`) reads the watchlist set and stamps `is_watchlisted` per entry. Single query of `ticker_watchlist WHERE is_active=true` → set of strings. Constant-time lookup per ticker.
3. **`TickerCoverageEntry` and `TickerCoverage` domain entity** — add the `is_watchlisted: bool` field.
4. **Integration tests** for both new endpoints:
   - POST happy path (new ticker) → 201, DB has the row.
   - POST idempotency (already-pinned) → 201 (or 200; pick one and document), no duplicate row.
   - DELETE happy path → 204, row removed.
   - DELETE non-existent ticker → 404.
   - Auth gating: non-admin → 403; unauthenticated → 401.
5. **Integration tests for the GET response shape** — `is_watchlisted=true` when the ticker is in the watchlist; `false` otherwise.

### Phase 2 — Frontend (~half day)

1. **Types + API client** — extend types, add the new client methods, add the new hook.
2. **Page changes** — new column + new action button per row.
3. **Tests** for the page:
   - Pinned ticker renders with the "Pinned" indicator and "Unpin" button.
   - Unpinned ticker renders without indicator and with "Pin" button.
   - Clicking Pin invokes the mutation with the right ticker; on success, query is invalidated.
   - Clicking Unpin invokes the delete mutation; on success, query is invalidated.
   - Per-row `isPending` only disables the active row (lesson from #296 follow-up).
   - Error toast surfaces on failure.

## Quality bar

- Clean Architecture: `WatchlistManager` is an adapter (`adapters/outbound/repositories/`); the new admin router goes in `adapters/inbound/api/`. No domain changes beyond extending the existing `TickerCoverage` entity.
- No `Any` in Python / `any` in TypeScript. No suppressions.
- Behavior-focused tests. Mock at architectural boundaries only.
- `task ci` green locally before pushing.

## Branch + PR

- Branch from main: `git checkout main && git pull --ff-only && git checkout -b feat/220-watchlist-admin-surface`
- Commit message: `feat(backend+fe): Pin/Unpin watchlist editing on data-coverage page (Task #220)`
- `gh pr create` — title `feat(backend+fe): watchlist Pin/Unpin admin surface (Task #220)`. Body must reference `agent_docs/tasks/220_watchlist_admin_surface.md`, list endpoint contracts, test plan.
- **Don't request Copilot reviewer** (errors here).
- **Run `/code-review <PR#>` via the Skill tool** after the PR is open. Address findings.
- **Complete the merge chain** — fix findings → push → wait for CI re-validation → `gh pr merge <N> --squash --delete-branch` → `git checkout main && git pull --ff-only`. Don't stop at "report findings".

## Success criteria

- [ ] Admin can POST `/admin/watchlist` with `{ticker: "AAPL"}` → ticker is added to `ticker_watchlist`.
- [ ] Admin can DELETE `/admin/watchlist/AAPL` → row removed.
- [ ] GET `/admin/data-coverage` returns `is_watchlisted` per ticker.
- [ ] UI shows pinned indicator + Unpin button on watchlisted rows; Pin button on unwatchlisted rows.
- [ ] Clicking Pin / Unpin updates the row within the next 30s poll cycle (or sooner via mutation invalidation).
- [ ] All tests pass; `task ci` green.

## Non-goals

- **Don't** surface the `priority` field in the UI. Out of scope until the scheduler actually consults it.
- **Don't** add a "Pin all currently-active stocks" bulk action. Out of scope; can ship later if the per-row UX proves clunky.
- **Don't** modify the scheduler's active-tickers union logic. The change here is additive — the scheduler keeps doing what it does today; we just give the operator a way to populate the watchlist arm of the union.
- **Don't** add backfill side-effects to the Pin action. Pin = "keep this refreshed going forward". For historical fill, the operator clicks Catch up as today. Two distinct actions.

## References

- `backend/src/zebu/adapters/outbound/repositories/watchlist_manager.py` — the manager (existing).
- `backend/src/zebu/adapters/outbound/models/ticker_watchlist.py` — the SQLModel.
- `backend/src/zebu/infrastructure/scheduler.py:207` — where the union is computed.
- `backend/src/zebu/application/queries/data_coverage.py` — the query handler that needs the `is_watchlisted` field.
- `backend/src/zebu/adapters/inbound/api/admin_data_coverage.py` — the response model that gets the new field.
- `frontend/src/pages/AdminDataCoverage.tsx` — the page that gets the new column + actions.
- Task 215 (`agent_docs/tasks/215_backfill_ux_rework.md`) — the precedent for backend+frontend single-PR scope and the per-ticker `isPending` pattern.

## Agent assignment

Single `backend-swe` agent. Frontend portion is mechanical and tightly coupled to the backend response shape; splitting would add coordination overhead.
