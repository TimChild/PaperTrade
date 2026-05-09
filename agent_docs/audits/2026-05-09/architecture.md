# Audit: Architecture

**Date**: 2026-05-09
**Auditor**: architect (audit mode)
**Scope**:

- `backend/src/zebu/domain/` (entities, value objects, services, strategies, exceptions)
- `backend/src/zebu/application/` (commands, queries, services, ports, dtos, exceptions)
- `backend/src/zebu/adapters/` (inbound/api, outbound/database, outbound/market_data, outbound/repositories, auth)
- `backend/src/zebu/infrastructure/` (database, scheduler, cache, rate_limiter, market_calendar)

## Findings

### P0 Critical (blocks future work / actively broken)

- **[P0-arch-1] Domain imports from Application — strategy modules pull `PricePoint` from `application.dtos`**
  - Evidence:
    - `backend/src/zebu/domain/services/strategies/protocol.py:7` (`from zebu.application.dtos.price_point import PricePoint`)
    - `backend/src/zebu/domain/services/strategies/buy_and_hold.py:7`
    - `backend/src/zebu/domain/services/strategies/dollar_cost_averaging.py:7`
    - `backend/src/zebu/domain/services/strategies/moving_average_crossover.py:7`
  - Why it matters: Direct violation of the dependency rule (Domain must depend on nothing outward). The dependency graph has a real cycle Domain↔Application — domain strategies depend on `application.dtos.PricePoint`, while `application.services.backtest_executor` instantiates those domain strategies. Phase C+ will be adding `LiveStrategyExecutor` and `ExplorationTask` agents that re-use the same strategy `Protocol`; if the protocol stays anchored in application code, every new agent context gets pulled into the same cycle.
  - Recommended fix: Move `PricePoint` into `domain/value_objects/` (it's already constructed from `Money`+`Ticker` and has invariants — it's a value object, not a DTO). Re-export from `application.dtos.price_point` if external callers need backward compatibility, but the canonical home is the domain.

- **[P0-arch-2] Application imports from Adapters — `GetActiveTickersHandler` couples to a SQLModel ORM model**
  - Evidence: `backend/src/zebu/application/queries/get_active_tickers.py:9` (`from zebu.adapters.outbound.database.models import TransactionModel`) and `:53` takes an `AsyncSession` directly, then issues a raw `select(TransactionModel.ticker)` query.
  - Why it matters: Application use-cases must depend only on `domain` + `application.ports`. This handler bypasses `TransactionRepository` entirely and reaches into adapter ORM. As soon as a second adapter (e.g., a non-SQL store, or an in-memory test harness) is needed for the agent platform's scheduled tasks, this query breaks. It also forces every test to spin up a real DB.
  - Recommended fix: Add a `list_active_tickers(days: int) -> list[Ticker]` method to `TransactionRepository` (port). Implement it in `SQLModelTransactionRepository` and `InMemoryTransactionRepository`. The query handler should depend on the port, not on `AsyncSession`/`TransactionModel`.

### P1 High (foundation refactors making Phase C–G easier)

- **[P1-arch-1] In-memory repository implementations live in `application/ports/`**
  - Evidence: 5 files — `backend/src/zebu/application/ports/in_memory_portfolio_repository.py`, `in_memory_transaction_repository.py`, `in_memory_strategy_repository.py`, `in_memory_snapshot_repository.py`, `in_memory_backtest_run_repository.py`
  - Why it matters: `application/ports/` is the home of *contracts* (Protocols). Concrete implementations — even test doubles — belong in `adapters/`. The current layout means tests import from a layer that, by the dependency rule, isn't allowed to contain implementations. It also obscures which symbols in the package are interfaces vs. classes to instantiate.
  - Recommended fix: Move all `in_memory_*.py` files to `adapters/outbound/in_memory/` (mirroring `adapters/outbound/database/`). Update test imports.

- **[P1-arch-2] `PriceRepository` and `WatchlistManager` are concrete adapters with no port**
  - Evidence:
    - `backend/src/zebu/adapters/outbound/repositories/price_repository.py:21` (concrete class, no Protocol)
    - `backend/src/zebu/adapters/outbound/repositories/watchlist_manager.py:18`
    - Used directly by `infrastructure/scheduler.py:107` and `adapters/outbound/market_data/alpha_vantage_adapter.py:91`
  - Why it matters: Repository ports are missing for both. `AlphaVantageAdapter` takes `PriceRepository` (concrete) as a constructor parameter — adapter depending on adapter, no DI seam. Phase C's "agent execution context" will likely want an in-memory or test double of the price store; without a port there's nothing to substitute.
  - Recommended fix: Add `PriceRepositoryPort` and `WatchlistPort` Protocols under `application/ports/`. Make `AlphaVantageAdapter`, `scheduler.refresh_active_stocks`, and any future caller depend on the port.

- **[P1-arch-3] FastAPI dependency aliases use concrete adapter types instead of ports**
  - Evidence: `backend/src/zebu/adapters/inbound/api/dependencies.py:286-294`
    - `PortfolioRepositoryDep = Annotated[SQLModelPortfolioRepository, ...]`
    - `TransactionRepositoryDep = Annotated[SQLModelTransactionRepository, ...]`
    - `SnapshotRepositoryDep = Annotated[SQLModelSnapshotRepository, ...]`
    - `PriceRepositoryDep = Annotated[PriceRepository, ...]`
  - Why it matters: Inbound adapters and the API routes that consume them are statically typed against `SQLModel*` adapter classes, not the `Protocol`s. The whole point of defining ports was to keep callers at the abstraction; this gives back the boundary. Compare to `MarketDataDep = Annotated[MarketDataPort, ...]` and `AuthPortDep = Annotated[AuthPort, ...]` on the same file — those *do* use the Protocol and work fine.
  - Recommended fix: Change every `*Dep` alias to use the Protocol from `application.ports`. Adjust route handlers' parameter types accordingly. No behavior change required; this is purely a typing fix.

- **[P1-arch-4] Domain entities embed wall-clock reads in their invariants**
  - Evidence:
    - `backend/src/zebu/domain/entities/portfolio.py:53` (`now = datetime.now(UTC)` inside `__post_init__`)
    - `backend/src/zebu/domain/entities/strategy.py:54` (same pattern)
    - `backend/src/zebu/domain/entities/portfolio_snapshot.py:75` (`today = date.today()` inside `__post_init__`) and `:142` (`created_at=datetime.now(UTC)` inside the `create` factory)
    - `backend/src/zebu/domain/entities/backtest_run.py:75` (`if self.end_date > date.today()`)
  - Why it matters: Domain rule explicitly prohibits I/O / side effects. `datetime.now()` is a side effect (reads OS clock). Beyond philosophy, this *actively* hurts: snapshot tests have to mock `datetime` globally, time-travel tests for backtests can't be reliable, and Phase D's agent simulation harness will need to replay scenarios with controlled time. Note that `trade_factory.create_buy_transaction` (`backend/src/zebu/domain/services/trade_factory.py:19`) already does this correctly — it accepts `timestamp: datetime` as a parameter. The entities should follow that pattern.
  - Recommended fix: Make all "must not be in the future" checks accept the `now`/`today` to compare against (passed by the use-case from a `Clock` port). For factories like `PortfolioSnapshot.create()`, accept a `created_at: datetime` parameter. Drop the `__post_init__` clock check or have it default to `None` (skip) so callers must opt in.

- **[P1-arch-5] `TradeSignal` value object uses primitives where domain VOs already exist**
  - Evidence: `backend/src/zebu/domain/value_objects/trade_signal.py:35-38`
    - `ticker: str` (should be `Ticker`)
    - `amount: Decimal | None` (should be `Money` — unit and currency are implicit USD comments rather than enforced)
    - `quantity: Decimal | None` (should be `Quantity`)
  - Why it matters: This VO is the contract between strategies and the executor. Currency/symbol invariants are silently lost the moment a `TradeSignal` is built. Phase B+ adds live trading and exploration agents producing signals — every new producer is one more place that can violate `Ticker` format or attach an unintended currency. Primitive obsession in a top-level domain VO compounds.
  - Recommended fix: Replace `ticker: str` with `Ticker`, `amount: Decimal | None` with `Money | None`, `quantity: Decimal | None` with `Quantity | None`. Update producers (3 strategies) and consumer (`BacktestTransactionBuilder`).

### P2 Medium (worth fixing, not blocking)

- **[P2-arch-1] `BacktestRun.initial_cash` is `Decimal`, not `Money`**
  - Evidence: `backend/src/zebu/domain/entities/backtest_run.py:54` (`initial_cash: Decimal`); `backend/src/zebu/application/services/backtest_executor.py:200` immediately wraps it: `initial_cash = Money(command.initial_cash, "USD")`.
  - Why it matters: `Money` already exists as the canonical monetary VO; the entity dropping back to `Decimal` makes the currency assumption invisible at the domain boundary. The wrap at the use-case layer shows that the surrounding code knows it should be `Money` but the entity hasn't caught up.
  - Recommended fix: Change `BacktestRun.initial_cash` to `Money`. Propagate to `RunBacktestCommand` and the API request schema.

- **[P2-arch-2] `BacktestRun.strategy_snapshot: dict[str, Any]` is a typed-as-anything escape hatch**
  - Evidence: `backend/src/zebu/domain/entities/backtest_run.py:50` (`strategy_snapshot: dict[str, Any]  # noqa: ANN401`)
  - Why it matters: A "snapshot of a strategy" is itself a domain concept. Typing it as `dict[str, Any]` means no static guarantees about what the snapshot contains, despite the executor (`backtest_executor.py:112-118`) building it with a consistent shape every time.
  - Recommended fix: Introduce a `StrategySnapshot` value object (frozen dataclass) with explicit fields (`id`, `name`, `strategy_type`, `tickers`, `parameters`). Domain typing then enforces what every snapshot contains.

- **[P2-arch-3] `PricePoint.is_stale()` reads the wall clock**
  - Evidence: `backend/src/zebu/application/dtos/price_point.py:181` (`now = datetime.now(UTC)`)
  - Why it matters: Same clock-injection issue as the entities, but on a value object that the domain strategies consume. Making this method pure (`is_stale(self, max_age, now)`) lets backtests deterministically reproduce staleness behavior.
  - Recommended fix: Add a `now: datetime` parameter; update the (likely few) callers.

- **[P2-arch-4] `InsufficientHistoricalDataError` and `InvalidTokenError` are in `domain/exceptions.py` but are integration concerns**
  - Evidence:
    - `backend/src/zebu/domain/exceptions.py:188` (`InsufficientHistoricalDataError`) — only raised from `application/services/historical_data_preparer.py:87` after an empty result from the market data port
    - `backend/src/zebu/domain/exceptions.py:218` (`InvalidTokenError`) — only consumed in `adapters/auth/clerk_adapter.py` and `application/ports/auth_port.py`
  - Why it matters: Both errors describe failures of *external* systems (market data adapter returned nothing, auth provider rejected token), not violations of business rules expressible in pure domain terms. Their presence in `domain/exceptions.py` muddles the model.
  - Recommended fix: Move `InsufficientHistoricalDataError` to `application/exceptions.py` (sits next to `MarketDataError`). Move `InvalidTokenError` and the `AuthenticationError` base to `application/exceptions.py` next to the auth port. Re-export from `domain.exceptions` if you want to avoid touching every catch site immediately.

- **[P2-arch-5] `adapters/outbound/repositories/` and `adapters/outbound/models/` are organized inconsistently**
  - Evidence: Compare directory layout under `backend/src/zebu/adapters/outbound/`:
    - `database/` — has both repositories (`portfolio_repository.py`, `transaction_repository.py`, …) and `models.py` together
    - `repositories/` — has `price_repository.py` and `watchlist_manager.py`
    - `models/` — has `price_history.py` and `ticker_watchlist.py`
  - Why it matters: Two parallel organizational schemes. A future agent looking for "the repository for X" has to check two locations and remember which classes ended up where. The price/watchlist features were clearly added with a different mental model than the original portfolio/transaction features.
  - Recommended fix: Pick one structure and consolidate. Easiest: merge `outbound/repositories/*` + `outbound/models/*` into `outbound/database/` so all SQLModel-backed code lives together.

### P3 Nice-to-have (defer)

- **[P3-arch-1] No domain-layer `Clock` port**
  - Why it matters: Once P1-arch-4 lands, every use case that needs "now" will inject it from FastAPI. A small `Clock` port in `application/ports/` (`now() -> datetime`) standardizes how use cases get time and makes the substitution one-liner in tests. Defer until Phase D's agent simulation harness actually needs it.

- **[P3-arch-2] `domain/services/strategies/` could become its own package**
  - Why it matters: Strategies are currently pure-domain services but their location under `domain/services/strategies/` mixes them with simple `staticmethod` calculators (`portfolio_calculator.py`, `snapshot_calculator.py`). As more strategies appear in Phase C–E, the directory will grow. Defer until count > 6.

## Summary

- Total: 11 | P0: 2 | P1: 5 | P2: 5 | P3: 2 (P3 not counted toward total — they're deferred)
- Estimated total fix effort: ~16–20 hours
  - P0-arch-1 (move `PricePoint` to domain): ~2h
  - P0-arch-2 (add port method, repository implementations): ~2h
  - P1-arch-1 (relocate in-memory repos): ~1h
  - P1-arch-2 (add ports for price/watchlist): ~3h
  - P1-arch-3 (DI alias retyping): ~1h
  - P1-arch-4 (clock-inject domain entities): ~3h
  - P1-arch-5 (TradeSignal VO upgrade + propagate): ~3h
  - P2 collectively: ~4h

- Notable strengths (what's GOOD):
  - `PortfolioCalculator`, `SnapshotCalculator`, `trade_factory` are exemplary pure domain services — all functions static or take `timestamp` as a parameter, no I/O.
  - `Money`, `Ticker`, `Quantity` value objects are well-defined with proper invariants and arithmetic operations.
  - `application/ports/` correctly uses `typing.Protocol` for structural typing of repositories.
  - `MarketDataPort` and `AuthPort` are correctly applied through DI in API routes (`MarketDataDep`, `AuthPortDep`) — these prove the pattern works; the other repository deps just need to follow suit.
  - `application.services.backtest_executor` only depends on `application.ports.*` and `domain.*` — clean Clean-Architecture orchestration despite being long.
  - `application/exceptions.py` cleanly separates integration errors (`MarketDataError`, …) from domain rule violations.
