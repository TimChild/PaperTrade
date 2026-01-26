# Task 056: Phase 3c Analytics - Domain Layer

**Status**: Not Started
**Depends On**: Phase 3b complete (PR #72 merged ✅)
**Blocks**: Tasks 057, 058, 059, 060
**Estimated Effort**: 2-3 days

## Objective

Implement domain entities and value objects for portfolio analytics: `PortfolioSnapshot` entity and `PerformanceMetrics` value object, plus snapshot calculation logic.

## Reference Architecture

Full specification: `docs/architecture/phase3-refined/phase3c-analytics.md`

## Success Criteria

- [ ] `PortfolioSnapshot` entity implemented with all properties
- [ ] `PerformanceMetrics` value object implemented
- [ ] Snapshot calculation logic implemented and tested
- [ ] Unit tests for all domain components (>90% coverage)
- [ ] All existing 499+ tests still pass
- [ ] No new lint/type errors

## Implementation Details

### 1. PortfolioSnapshot Entity

**Location**: `backend/app/domain/entities/portfolio_snapshot.py`

```python
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

@dataclass
class PortfolioSnapshot:
    """Daily snapshot of portfolio value for analytics."""

    id: UUID
    portfolio_id: UUID
    snapshot_date: date
    total_value: Decimal  # cash_balance + holdings_value
    cash_balance: Decimal
    holdings_value: Decimal
    holdings_count: int
    created_at: datetime

    @classmethod
    def create(
        cls,
        portfolio_id: UUID,
        snapshot_date: date,
        cash_balance: Decimal,
        holdings_value: Decimal,
        holdings_count: int,
    ) -> "PortfolioSnapshot":
        """Factory method to create a new snapshot."""
        return cls(
            id=uuid4(),
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            total_value=cash_balance + holdings_value,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            holdings_count=holdings_count,
            created_at=datetime.now(),
        )
```

**Invariants**:
- `total_value == cash_balance + holdings_value` (always)
- `snapshot_date <= today` (cannot snapshot future)
- All monetary values are non-negative
- `holdings_count >= 0`

### 2. PerformanceMetrics Value Object

**Location**: `backend/app/domain/value_objects/performance_metrics.py`

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class PerformanceMetrics:
    """Calculated performance metrics for a time period."""

    period_start: date
    period_end: date
    starting_value: Decimal
    ending_value: Decimal
    absolute_gain: Decimal  # ending - starting
    percentage_gain: Decimal  # (ending/starting - 1) * 100
    highest_value: Decimal  # max in period
    lowest_value: Decimal  # min in period

    @classmethod
    def calculate(
        cls,
        snapshots: list,  # List[PortfolioSnapshot]
    ) -> "PerformanceMetrics":
        """Calculate metrics from a list of snapshots."""
        if not snapshots:
            raise ValueError("Cannot calculate metrics from empty snapshots")

        sorted_snapshots = sorted(snapshots, key=lambda s: s.snapshot_date)
        first = sorted_snapshots[0]
        last = sorted_snapshots[-1]

        absolute_gain = last.total_value - first.total_value
        percentage_gain = (
            (last.total_value / first.total_value - 1) * 100
            if first.total_value > 0 else Decimal("0")
        )

        return cls(
            period_start=first.snapshot_date,
            period_end=last.snapshot_date,
            starting_value=first.total_value,
            ending_value=last.total_value,
            absolute_gain=absolute_gain,
            percentage_gain=percentage_gain.quantize(Decimal("0.01")),
            highest_value=max(s.total_value for s in snapshots),
            lowest_value=min(s.total_value for s in snapshots),
        )
```

### 3. Snapshot Calculation Service

**Location**: `backend/app/domain/services/snapshot_calculator.py`

```python
from decimal import Decimal
from datetime import date
from typing import Protocol
from uuid import UUID

from app.domain.entities.portfolio_snapshot import PortfolioSnapshot

class SnapshotCalculator:
    """Service for calculating portfolio snapshots."""

    def calculate_snapshot(
        self,
        portfolio_id: UUID,
        snapshot_date: date,
        cash_balance: Decimal,
        holdings: list[tuple[str, int, Decimal]],  # (ticker, qty, price)
    ) -> PortfolioSnapshot:
        """Calculate a snapshot for the given portfolio state."""
        holdings_value = sum(
            Decimal(qty) * price for _, qty, price in holdings
        )

        return PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            holdings_count=len(holdings),
        )
```

### 4. Domain Exports

Update `backend/app/domain/__init__.py` to export new entities.

Update `backend/app/domain/entities/__init__.py` to include PortfolioSnapshot.

Update `backend/app/domain/value_objects/__init__.py` to include PerformanceMetrics.

### 5. Unit Tests

**Location**: `backend/tests/domain/test_portfolio_snapshot.py`

Required tests:
- `test_create_snapshot_with_only_cash`
- `test_create_snapshot_with_holdings`
- `test_create_snapshot_zero_holdings`
- `test_snapshot_total_value_invariant`
- `test_snapshot_non_negative_values`

**Location**: `backend/tests/domain/test_performance_metrics.py`

Required tests:
- `test_calculate_metrics_from_snapshots`
- `test_calculate_metrics_positive_gain`
- `test_calculate_metrics_negative_gain`
- `test_calculate_metrics_empty_snapshots_raises`
- `test_calculate_metrics_single_snapshot`
- `test_highest_lowest_values`
- `test_percentage_gain_calculation`

**Location**: `backend/tests/domain/test_snapshot_calculator.py`

Required tests:
- `test_calculate_snapshot_cash_only`
- `test_calculate_snapshot_with_multiple_holdings`
- `test_calculate_snapshot_empty_holdings`

## Implementation Order

1. Create `PortfolioSnapshot` entity with tests
2. Create `PerformanceMetrics` value object with tests
3. Create `SnapshotCalculator` service with tests
4. Update domain exports
5. Run full test suite to verify no regressions

## Commands

```bash
# Run domain tests only
cd backend && uv run pytest tests/domain/ -v

# Run specific test file
cd backend && uv run pytest tests/domain/test_portfolio_snapshot.py -v

# Full test suite
task test:backend
```

## Notes

- Keep domain pure - no database operations, no I/O
- All calculations use Decimal for precision
- Follow existing code patterns in `backend/app/domain/`
- This task is foundational - blocks all other Phase 3c tasks
