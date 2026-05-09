# Database Audit — Phase B1

**Auditor**: backend-swe
**Slug**: db
**Date**: 2026-05-09
**Scope**: SQLModel definitions, Alembic migrations, repository implementations, connection/session/transaction handling.

## Inventory

**Tables (7)**: `portfolios`, `transactions`, `portfolio_snapshots`, `strategies`, `backtest_runs`, `price_history`, `ticker_watchlist`.

**Migration chain (single-rooted, linear)** — `c9b7d8e0f1a2` → `e46ccf3fcc35` → `7ca1e9126eba` → `a6a5412b5d02` → `b001add_portfolio_type` → `b002add_strategy_and_backtest`. No merge migrations, no dual roots, no `down_revision = None` after the first.

**Indexes** — every FK-style column has at least a single-column index, plus composite `(portfolio_id, timestamp)` and `(portfolio_id, snapshot_date)` for the obvious sort paths. The `BACKLOG.md` line item "Add Database Indexes for Transaction.portfolio_id and Transaction.timestamp" is **already done** in `c9b7d8e0f1a2_create_core_portfolio_tables.py` (lines 79–90) — backlog item is stale.

## Findings

### P0

**P0-db-1: `echo=True` is hardcoded in production engine config.**
File: `backend/src/zebu/infrastructure/database.py:25`. Every SQL statement is logged at INFO level — in prod that means the structured-logging pipeline emits one line per query plus the formatted bind-params. Two impacts: (a) measurable per-request latency on chatty endpoints (snapshot, transaction list), (b) log-volume cost / noise in Grafana Cloud. Fix: `engine_kwargs = {"echo": os.getenv("DB_ECHO", "false").lower() == "true"}` and default off in prod. ~5-line change.

**P0-db-2: No foreign-key constraints anywhere in the schema.**
Every cross-table id (`Transaction.portfolio_id`, `Snapshot.portfolio_id`, `BacktestRun.user_id|strategy_id|portfolio_id`, `Strategy.user_id`) is a bare `Uuid` column with neither a `ForeignKey` in the SQLModel `Field(...)` nor a `sa.ForeignKey` in any migration. Consequences: orphan rows are possible (a deleted portfolio can leave snapshots/transactions behind unless `DeletePortfolioHandler` runs in the right order — and it does, but nothing in the DB enforces that), and joins lose the referential-integrity safety net that engineers naturally assume from a relational schema. The `delete_portfolio.py` handler comment "Delete related data in correct order to maintain referential integrity" is doing the DB's job manually. Recommended: add `ForeignKey(...) ON DELETE CASCADE` (or `RESTRICT`) constraints in a new migration; classify deletion strategy per relationship explicitly. P0 because Phase B's planned new entities (`exploration_tasks`, `agent_runs`, `strategy_condition_triggers`) will also reference these tables — entrenching the no-FK pattern in Phase B will make a later cleanup migrations-painful.

### P1

**P1-db-1: N+1 in `BacktestExecutor._run_pipeline` transaction persistence.**
File: `backend/src/zebu/application/services/backtest_executor.py:287-288`. After simulation builds `builder.transactions` (often hundreds for a multi-month backtest), each `Transaction` is saved via a separate `await self._transaction_repo.save(transaction)` call. Each `save()` does: `SELECT` for existence (`get(transaction.id)`), `INSERT`, `flush()`. Worse, `transaction_repository.save` (`transaction_repository.py:131-147`) does `existing = await self.get(...)` *and* relies on `IntegrityError` — keep one or the other, not both. Bulk-insert path needed (`session.add_all(models)` + a single flush at the end). Clear win: 100 transactions go from ~300 round-trips to ~1.

**P1-db-2: N+1 in `SnapshotJobService.run_daily_snapshot`.**
File: `backend/src/zebu/application/services/snapshot_job.py:80-98`. For each portfolio: one `get_by_portfolio` to load transactions, then per-holding `get_current_price` calls. The `TransactionRepository.get_by_portfolios(portfolio_ids)` batch method already exists (`transaction_repository.py:178-211`) and is unused here. Phase E (agent-driven exploration) will multiply portfolios; left unfixed, the daily snapshot job's runtime grows linearly with portfolio count. Restructure `run_daily_snapshot` to batch-fetch transactions once, then iterate.

**P1-db-3: Missing unique constraint on `(portfolio_snapshots.portfolio_id, snapshot_date)`.**
The model docstring asserts "One snapshot per portfolio per day (unique constraint enforced)" (`models.py:245`) but neither the SQLModel `__table_args__` nor the migration `c9b7d8e0f1a2` declares a `UniqueConstraint`. There is only an *index* on the same columns. `SnapshotRepository.save()` (`snapshot_repository.py:43-72`) implements upsert via SELECT-then-update — race condition: two concurrent `run_daily_snapshot` invocations (or backfill + scheduler overlap) can both read "no existing row" and both `INSERT`, producing duplicates. Add `UniqueConstraint("portfolio_id", "snapshot_date", name="uq_snapshot_portfolio_date")` and a migration; switch repo to a real `INSERT ... ON CONFLICT` pattern.

**P1-db-4: No connection-pool config; no `pool_pre_ping`.**
File: `backend/src/zebu/infrastructure/database.py:29`. `create_async_engine(DATABASE_URL, **engine_kwargs)` takes the SQLAlchemy defaults: `pool_size=5`, `max_overflow=10`, no `pool_pre_ping`, no `pool_recycle`. On Postgres-over-network with idle connections, the first DB call after a connection drop (PG idle timeout, network blip, DB restart during deploy) returns `OperationalError`, breaking the request. With Phase F's scheduled agents holding sessions for longer-than-request lifetimes, this risk grows. Recommended: `pool_pre_ping=True`, `pool_recycle=1800`, configurable `pool_size` via env var (default 10–20). When used with SQLite, retain `connect_args={"check_same_thread": False}` and skip the pool kwargs.

**P1-db-5: Phase E table planning gap.**
Proposal §3.6 / Phase E names new entities (`exploration_tasks`, `exploration_findings`, `agent_runs`, `strategy_condition_triggers`) that will be the *primary* read path for the agent-history dashboard. None exists yet. Without a deliberate index plan from day one — `exploration_tasks(status, created_at)`, `agent_runs(agent_id, started_at)`, `findings(exploration_task_id, created_at)` — these tables grow unbounded with one row per agent invocation per parameter sweep and become slow within weeks. Address in the architect spec for B3-onward, not in code yet — but flag as P1 so it's not forgotten.

### P2

**P2-db-1: `transaction_repository.save()` does redundant existence check.**
File: `backend/src/zebu/adapters/outbound/database/transaction_repository.py:131-147`. Either trust the DB's PK uniqueness (catch `IntegrityError`) or skip the optimistic SELECT — current code does both. The SELECT is wasted on the happy path (the common case is "new transaction"). Tied to P1-db-1's bulk-insert refactor.

**P2-db-2: `sa.JSON()` instead of PG `JSONB` in migrations.**
Files: `b002add_strategy_and_backtest.py:45,46,60` (`tickers`, `parameters`, `strategy_snapshot`), `a6a5412b5d02_*.py:43` (`holdings_breakdown`). On Postgres, `sa.JSON()` maps to `json`, not `jsonb` — meaning no GIN-indexable containment queries (`@>`), slower comparison, no deduplicating storage. Phase E agents querying "find all explorations with `parameters.fast_window=10`" will table-scan. Switch to `postgresql.JSONB` with a SQLite fallback (or simply `sa.JSON().with_variant(JSONB(), "postgresql")`).

**P2-db-3: Schema-domain divergence — `PortfolioModel.updated_at` and `version`.**
The `Portfolio` domain entity (`portfolio.py`) has no `updated_at` or `version` field, but `PortfolioModel` carries both. `version` is incremented in `portfolio_repository.save()` for "optimistic locking" but no read path checks it — the locking is currently theatre. Either expose it in the domain entity and check on save, or remove the column. (Worth doing in B5/B6 refactor pass, not a hot fire.)

**P2-db-4: `init_db()` runs `SQLModel.metadata.create_all` on SQLite startup.**
File: `backend/src/zebu/infrastructure/database.py:40-50`. Dev-mode shortcut. Risk: divergence between `create_all`-produced schema and `alembic upgrade head`-produced schema goes unnoticed because tests rarely run against migrations. Recommendation: run alembic in dev too, or add a CI smoke test that asserts `create_all` schema == `upgrade head` schema. Especially relevant given the no-FK gap above — `create_all` and migrations both omit FKs today, but a future model-side-only FK declaration would silently apply only to fresh SQLite DBs.

**P2-db-5: `alembic.ini` hardcodes a sync SQLite URL.**
File: `backend/alembic.ini:87` `sqlalchemy.url = sqlite:///./papertrade.db`. The CD pipeline overrides via `DATABASE_URL` env var (env.py:31-32) and `env.py` correctly routes async URLs to `run_migrations_online_async`. The hardcoded URL is dead but misleading — anyone running `uv run alembic upgrade head` locally without setting `DATABASE_URL` hits the project-root SQLite file rather than the container's path. Either remove or change to `sqlalchemy.url = ${DATABASE_URL}`.

### P3

**P3-db-1: Stale BACKLOG line item.**
`BACKLOG.md` "Add Database Indexes — Transaction.portfolio_id and Transaction.timestamp" is already implemented. Remove during BACKLOG/PROGRESS tidy.

**P3-db-2: Cosmetic docstring rot in `e46ccf3fcc35_add_price_history_table.py`.**
The file's docstring shows `Revises:` (empty) but the actual `down_revision` is `"c9b7d8e0f1a2"`. Cosmetic only; the revision graph is correct.

## Top concern

**P0-db-2: zero foreign-key constraints across the entire schema.** The DB cannot enforce that `Transaction.portfolio_id` actually points at a real portfolio, that deleting a portfolio cascades to snapshots, or that `BacktestRun.strategy_id` references a non-deleted strategy. With Phase B about to introduce more cross-references (`exploration_tasks.target_portfolio_id`, `agent_runs.exploration_task_id`, etc.), ratifying the no-FK pattern now makes the eventual cleanup migration both larger and riskier. Cheap to fix today; expensive later.

## Counts

- P0: 2
- P1: 5
- P2: 5
- P3: 2
- **Total: 14**
