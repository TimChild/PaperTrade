# Phase 4.1: Domain Entities, Migrations, and Repositories for Backtesting

**Agent**: backend-swe
**Priority**: High — Foundation for the entire Phase 4 Trading Strategies & Backtesting feature

## Objective

Implement all the remaining Phase 4.1 foundation work: new domain entities, value objects, enums, Alembic migrations, repository ports, SQL and in-memory repository implementations, and database model updates. This builds on the prerequisite work already merged in PR #201 (backfill bug fix + trade_factory extraction).

## Architecture Reference

Read `docs/architecture/phase4-trading-strategies.md` thoroughly before starting — it contains the complete domain model, entity specifications, field constraints, and data model. Everything in this task implements that spec.

## What to Implement

### 1. PortfolioType Enum + Portfolio Entity Update

**New file**: `backend/src/zebu/domain/value_objects/portfolio_type.py`

```python
from enum import Enum

class PortfolioType(Enum):
    PAPER_TRADING = "PAPER_TRADING"
    BACKTEST = "BACKTEST"
```

**Modify**: `backend/src/zebu/domain/entities/portfolio.py`
- Add `portfolio_type: PortfolioType` field with default `PortfolioType.PAPER_TRADING`
- Import `PortfolioType` from the new value_objects module

### 2. StrategyType Enum + Strategy Entity

**New file**: `backend/src/zebu/domain/value_objects/strategy_type.py`

```python
from enum import Enum

class StrategyType(Enum):
    BUY_AND_HOLD = "BUY_AND_HOLD"
    DOLLAR_COST_AVERAGING = "DOLLAR_COST_AVERAGING"
    MOVING_AVERAGE_CROSSOVER = "MOVING_AVERAGE_CROSSOVER"
```

**New file**: `backend/src/zebu/domain/entities/strategy.py`

Frozen dataclass with fields from the architecture doc:
- `id: UUID`
- `user_id: UUID`
- `name: str` (1-100 chars, not blank)
- `strategy_type: StrategyType`
- `tickers: list[str]` (1-10 items)
- `parameters: dict[str, Any]` — Note: use `Any` here since strategy parameters vary by type. This is one of the rare justified uses.
- `created_at: datetime`

Add `__post_init__` validation: name not empty, name <= 100 chars, tickers list 1-10 items, created_at not in future. Follow the same pattern as `Portfolio.__post_init__`.

Equality and hash based on `id` only (same pattern as Portfolio).

### 3. BacktestStatus Enum + BacktestRun Entity

**New file**: `backend/src/zebu/domain/value_objects/backtest_status.py`

```python
from enum import Enum

class BacktestStatus(Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

**New file**: `backend/src/zebu/domain/entities/backtest_run.py`

Frozen dataclass with fields from the architecture doc:
- `id: UUID`
- `user_id: UUID`
- `strategy_id: UUID | None` (nullable — strategy may be deleted)
- `portfolio_id: UUID`
- `strategy_snapshot: dict[str, Any]` — Justified `Any` for JSON snapshot
- `backtest_name: str` (1-100 chars)
- `start_date: date`
- `end_date: date`
- `initial_cash: Decimal`
- `status: BacktestStatus`
- `created_at: datetime`
- `completed_at: datetime | None = None`
- `error_message: str | None = None`
- `total_return_pct: Decimal | None = None`
- `max_drawdown_pct: Decimal | None = None`
- `annualized_return_pct: Decimal | None = None`
- `total_trades: int | None = None`

Add `__post_init__` validation: backtest_name not empty, <= 100 chars, start_date < end_date, end_date <= today, initial_cash > 0.

Equality and hash based on `id`.

### 4. TradeSignal Value Object

**New file**: `backend/src/zebu/domain/value_objects/trade_signal.py`

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

class TradeAction(Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass(frozen=True)
class TradeSignal:
    action: TradeAction
    ticker: str
    signal_date: date
    quantity: Decimal | None = None  # Shares (whole or fractional)
    amount: Decimal | None = None    # USD amount

    def __post_init__(self) -> None:
        # Exactly one of quantity or amount must be set
        if (self.quantity is None) == (self.amount is None):
            raise ValueError("Exactly one of quantity or amount must be set")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.amount is not None and self.amount <= 0:
            raise ValueError("amount must be positive")
```

Note on fractional shares: Use `Decimal` for quantity (not int). For v1 the BacktestTransactionBuilder will floor to whole shares when resolving, but storing as Decimal prepares for fractional share support later.

### 5. Database Models

**Modify**: `backend/src/zebu/adapters/outbound/database/models.py`

Add `portfolio_type` to `PortfolioModel`:
- Add `portfolio_type: str = Field(default="PAPER_TRADING")`
- Update `to_domain()` to pass `portfolio_type=PortfolioType(self.portfolio_type)`
- Update `from_domain()` to save `portfolio_type=portfolio.portfolio_type.value`

Add new `StrategyModel(SQLModel, table=True)`:
- Table name: `strategies`
- Columns matching the architecture doc data model section
- `tickers` and `parameters` stored as JSON columns
- `to_domain()` and `from_domain()` conversion methods
- Index on `user_id`

Add new `BacktestRunModel(SQLModel, table=True)`:
- Table name: `backtest_runs`
- Columns matching the architecture doc data model section
- `strategy_snapshot` stored as JSON column
- `to_domain()` and `from_domain()` conversion methods
- Indexes on `user_id`, `portfolio_id` (unique), `strategy_id`

### 6. Alembic Migrations

Create two migrations (run from `backend/` directory):

**Migration 1**: `uv run alembic revision --autogenerate -m "add_portfolio_type_to_portfolios"`
- Adds `portfolio_type VARCHAR NOT NULL DEFAULT 'PAPER_TRADING'` to `portfolios`

**Migration 2**: `uv run alembic revision --autogenerate -m "add_strategy_and_backtest_tables"`
- Creates `strategies` table
- Creates `backtest_runs` table

Verify the autogenerated migrations are correct, fix if needed.

### 7. Repository Ports (Protocols)

**New file**: `backend/src/zebu/application/ports/strategy_repository.py`

```python
class StrategyRepository(Protocol):
    async def get(self, strategy_id: UUID) -> Strategy | None: ...
    async def get_by_user(self, user_id: UUID) -> list[Strategy]: ...
    async def save(self, strategy: Strategy) -> None: ...
    async def delete(self, strategy_id: UUID) -> None: ...
```

**New file**: `backend/src/zebu/application/ports/backtest_run_repository.py`

```python
class BacktestRunRepository(Protocol):
    async def get(self, backtest_id: UUID) -> BacktestRun | None: ...
    async def get_by_user(self, user_id: UUID) -> list[BacktestRun]: ...
    async def get_by_strategy(self, strategy_id: UUID) -> list[BacktestRun]: ...
    async def save(self, backtest_run: BacktestRun) -> None: ...
    async def delete(self, backtest_id: UUID) -> None: ...
```

Follow the existing patterns in `portfolio_repository.py` for docstrings and typing.

### 8. In-Memory Repository Implementations

**New file**: `backend/src/zebu/application/ports/in_memory_strategy_repository.py`
**New file**: `backend/src/zebu/application/ports/in_memory_backtest_run_repository.py`

Follow the pattern in `in_memory_portfolio_repository.py`: dict storage, thread-safe with Lock, sorted returns.

### 9. SQL Repository Implementations

**New file**: `backend/src/zebu/adapters/outbound/database/strategy_repository.py`
**New file**: `backend/src/zebu/adapters/outbound/database/backtest_run_repository.py`

Follow the pattern in the existing `portfolio_repository.py` for SQLModel-based implementations. Use `select()` queries, `session.exec()`, model `to_domain()`/`from_domain()` conversions.

### 10. Update Portfolio API Response

In `backend/src/zebu/adapters/inbound/api/portfolios.py`:
- Add `portfolio_type: str` to portfolio response schemas
- Include it in list and detail responses

### 11. Tests

Write comprehensive tests for:

**Domain entities** (in `backend/tests/unit/domain/entities/`):
- `test_strategy.py`: Valid creation, name validation, tickers validation, equality
- `test_backtest_run.py`: Valid creation, date validation, status, metric fields

**Value objects** (in `backend/tests/unit/domain/value_objects/`):
- `test_trade_signal.py`: Valid creation, exactly-one-of invariant, positive values
- `test_portfolio_type.py`: Enum values (brief)
- `test_strategy_type.py`: Enum values (brief)

**Portfolio entity update**:
- Test default portfolio_type is PAPER_TRADING
- Test creating portfolio with BACKTEST type
- Ensure existing portfolio tests still pass

**Model round-trips** (in existing or new integration test files):
- PortfolioModel to_domain/from_domain with portfolio_type
- StrategyModel to_domain/from_domain
- BacktestRunModel to_domain/from_domain

## Constraints

- Run `task quality:backend` after all changes — all tests must pass, ruff + pyright clean
- Follow existing code patterns exactly (frozen dataclasses, validation in __post_init__, Protocol ports)
- Use `Any` only for the two justified cases (strategy parameters dict, strategy_snapshot dict) — add a brief `# type: ignore` comment or Pyright config if needed, with justification
- All existing tests must continue to pass unchanged (default values ensure backward compat)
- Commit messages: use conventional commits (`feat`, `test`, etc.)

## Success Criteria

- All new entities, value objects, and enums are created per the architecture doc
- Portfolio entity has portfolio_type field with backward-compatible default
- Two Alembic migrations created and verified
- Repository ports + in-memory + SQL implementations for Strategy and BacktestRun
- PortfolioModel updated with portfolio_type column
- Portfolio API response includes portfolio_type
- Comprehensive tests for all new code
- `task quality:backend` passes cleanly
