# Task 211 — Recent activity feed (Phase H2)

**Status**: Implemented
**Branch**: `feat/h2-activity-feed`
**Agent**: backend-swe + frontend-swe (single PR)

## Overview

Aggregate cross-platform activity (trades, strategies, backtests, activations,
exploration tasks, API-key minting) into a single chronological feed surfaced
both via `GET /api/v1/activity` and a dashboard panel. The actor identity
column distinguishes Clerk-authored ("you") events from API-key-authored
events (the key's human label), so agent activity is visually separable from
human activity at a glance.

## Architecture

### Auth-context plumbing

`AuthenticatedUser` gains two optional fields populated only on the API-key
path:

- `api_key_id: UUID | None` — the persisted ApiKey's primary key.
- `api_key_label: str | None` — the human-readable label.

`ApiKeyAuthAdapter.verify_token` populates them; the Clerk path leaves them
`None`. A `get_active_api_key_id` dependency exposes `api_key_id` to route
handlers as `ActiveApiKeyIdDep`.

### Stamping `api_key_id` on writes

Five writable tables grow a nullable `api_key_id` FK column (ON DELETE SET
NULL → preserve audit trail when keys are revoked):

- `transactions`
- `strategies`
- `strategy_activations`
- `backtest_runs`
- `exploration_tasks`

The migration is `h001_add_api_key_id_to_writable_tables` (revises `c002`).
No backfill: existing rows have `NULL` (= "human via Clerk").

Each repository's `save()` (and `transactions.save_all()`) gains a
keyword-only `api_key_id: UUID | None = None` parameter. Routes pass the
value through:

- `BuyStockCommand` / `SellStockCommand` carry `api_key_id`.
- `RunBacktestCommand` carries `api_key_id`; the executor stamps it on
  the synthetic portfolio's deposit transaction, every trade transaction,
  the BacktestRun row.
- Strategy / activation / task creation routes pass `api_key_id` to their
  respective `save()` calls.

Domain entities are unchanged — `api_key_id` is a storage-layer concept.

### Activity aggregation

`SQLModelActivityRepository.list_events()` reads from each writable table
plus `api_keys` (joined via the injected `ApiKeyRepository` port for label
resolution), projects each row to one or more `ActivityEventDTO` instances,
merges, sorts DESC by `occurred_at`, and paginates in Python.

Event types projected:

| `ActivityEventType` | Source row | Timestamp |
|---|---|---|
| `trade` | `transactions` (BUY/SELL only) | `transaction.timestamp` |
| `strategy_created` | `strategies` | `created_at` |
| `backtest` | `backtest_runs` | `created_at` |
| `activation_created` | `strategy_activations` | `created_at` |
| `activation_run` | `strategy_activations` | `last_executed_at` |
| `task_filed` | `exploration_tasks` | `created_at` |
| `task_claimed` | `exploration_tasks` | `claimed_at` |
| `task_done` | `exploration_tasks` | `updated_at` (when `status=DONE`) |
| `api_key_minted` | `api_keys` | `created_at` |

For `task_claimed` / `task_done` the actor is the agent identifier
(`claimed_by`) rather than the original creator's credential — the row is
projected with `actor_kind="api_key"` and `actor_label=claimed_by`. For
`activation_run` the actor is `user` (scheduler executions are not
API-key authored).

### Endpoint contract

`GET /api/v1/activity`

Query parameters:

- `limit` (default 50, max 100). Note: spec said max 200 but the
  platform-wide `MAX_PAGE_LIMIT=100` constraint applies via
  `PaginatedResponse[T]`. Bumping the cap requires coordinated update —
  tracked as a follow-up.
- `offset` (default 0).
- `since` — optional ISO-8601 lower bound on `occurred_at`.
- `actor_label` — optional API-key label filter.
- `event_type` — repeatable event-type filter.

Response: standard `PaginatedResponse[ActivityEventResponse]`.

### Frontend

- `activityApi` + `useActivity` hook (TanStack Query, 10s stale time).
- `<ActivityFeed>` component: filter chip rail (per-event-type),
  table with `When / Actor / What happened` columns, click-to-navigate
  on rows whose subject has a detail page.
- `formatRelativeTime` helper in `utils/formatters.ts`: "just now",
  "Nm ago", "Nh ago", "Nd ago", or a short date for older.
- Mounted as a section on the Dashboard, below the portfolio grid.

## Testing

- **Backend** (`tests/integration/test_activity_api.py`, 16 tests):
  - Auth gating (401 / Clerk Bearer / API key).
  - Trade events render correct actor (user vs api_key + label).
  - Multi-source merge — strategies + tasks + keys all in feed.
  - Filtering: `event_type` (single + repeated), `actor_label`, `since`.
  - Pagination: `limit` / `offset` / `has_more`; oversized rejected 422.
  - Sort order: DESC by `occurred_at`.

- **Frontend** (10 component tests + 6 helper tests):
  - Rows render per event; user vs api_key actor labels.
  - Relative-time labels (e.g., "30m ago").
  - Click-to-navigate for portfolio subjects; disabled for tasks/keys.
  - Loading / error / empty states.
  - Filter chip toggle + clear behaviour.
  - Header columns ("When", "Actor", "What happened").

## Files

### Backend new

- `backend/migrations/versions/h001_add_api_key_id_to_writable_tables.py`
- `backend/src/zebu/application/dtos/activity_event_dto.py`
- `backend/src/zebu/application/ports/activity_repository.py`
- `backend/src/zebu/adapters/outbound/database/activity_repository.py`
- `backend/src/zebu/adapters/inbound/api/activity.py`
- `backend/tests/integration/test_activity_api.py`

### Backend modified

- `backend/src/zebu/application/ports/auth_port.py` (+`api_key_id`,
  `api_key_label` on `AuthenticatedUser`)
- `backend/src/zebu/adapters/auth/api_key_adapter.py` (populates the new
  fields on successful auth)
- `backend/src/zebu/adapters/inbound/api/dependencies.py` (+`get_active_api_key_id`,
  +`ActiveApiKeyIdDep` alias)
- `backend/src/zebu/adapters/outbound/database/models.py` (5 new
  `api_key_id` columns)
- 5 SQLModel repositories (`transaction`, `strategy`, `backtest_run`,
  `strategy_activation`, `exploration_task`) — `save()` accepts
  `api_key_id` kwarg
- 5 in-memory repositories — accept `api_key_id` for protocol
  compatibility (ignored in test variants)
- 5 port protocols — added kwarg to docstring + signature
- `application/commands/{buy_stock,sell_stock,run_backtest}.py` —
  carry `api_key_id`
- `application/services/backtest_executor.py` — passes
  `command.api_key_id` to every `save()`/`save_all()`
- 4 inbound API routes — pass `api_key_id` from `ActiveApiKeyIdDep`
- `backend/src/zebu/main.py` — wires `activity_router`

### Frontend new

- `frontend/src/services/api/activity.ts`
- `frontend/src/hooks/useActivity.ts`
- `frontend/src/components/features/activity/ActivityFeed.tsx`
- `frontend/src/components/features/activity/ActivityFeed.test.tsx`

### Frontend modified

- `frontend/src/services/api/types.ts` — Activity types
- `frontend/src/services/api/index.ts` — `activityApi` export
- `frontend/src/utils/formatters.ts` — `formatRelativeTime`
- `frontend/src/utils/formatters.test.ts` — 6 new tests
- `frontend/src/pages/Dashboard.tsx` — mounts `<ActivityFeed>`
- `frontend/src/mocks/handlers.ts` — MSW handler for the new endpoint

## Out of scope / follow-ups

- Bump `PaginatedResponse.MAX_PAGE_LIMIT` to support `limit=200` for the
  activity feed (task spec suggested 200 but existing infrastructure
  enforces 100 platform-wide).
- Persist a dedicated `activation_runs` table for full execution history
  rather than projecting only `last_executed_at`.
- Track `claimed_by_api_key_id` separately on tasks so claim/done rows
  resolve back to a real `api_keys.id` instead of relying on the
  `claimed_by` agent string.
- Backfill `api_key_id` for any existing rows that were created via API
  key before this migration shipped (none in production currently —
  Phase C2 only landed recently and most activity has been Bearer).
