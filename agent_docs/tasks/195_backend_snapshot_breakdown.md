# Task 195: Backend — Per-Holding Snapshot Breakdown for Composition Over Time

**Agent**: backend-swe
**Priority**: Medium
**Estimated Effort**: 4-6 hours

## Objective

Extend the portfolio snapshot system to store per-holding value breakdowns, and expose this data through the performance API. This enables a "composition over time" stacked area chart on the frontend.

## Context

Currently, `PortfolioSnapshot` stores only aggregate values (`cash_balance`, `holdings_value`, `total_value`). The snapshot job already computes per-holding data `(ticker, quantity, price)` in `snapshot_job.py` line ~212, but discards it when creating the snapshot. We need to persist this breakdown.

## Design Decision: JSON Column

Use a JSON column on the existing `portfolio_snapshots` table rather than a child table. Rationale:
- The data is always read as a whole (never queried by individual ticker)
- Avoids join complexity in the performance query
- Snapshots are append-only — no need to update individual holdings
- The amount of data per snapshot is small (typically 1-10 holdings)

## Implementation Plan

### 1. Domain Entity — Add `holdings_breakdown` field

**File**: `backend/src/zebu/domain/entities/portfolio_snapshot.py`

Add a new optional field to `PortfolioSnapshot`:
```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class HoldingBreakdown:
    """Value of a single holding at snapshot time."""
    ticker: str
    quantity: int
    price_per_share: Decimal
    value: Decimal  # quantity * price_per_share

@dataclass(frozen=True)
class PortfolioSnapshot:
    # ... existing fields ...
    holdings_breakdown: list[HoldingBreakdown] = field(default_factory=list)
```

- `holdings_breakdown` defaults to empty list for backward compatibility with existing snapshots
- Add validation: `sum(h.value for h in holdings_breakdown) == holdings_value` when breakdown is non-empty
- Update the `create()` factory method to accept the breakdown

### 2. Domain Service — Preserve per-holding data

**File**: `backend/src/zebu/domain/services/snapshot_calculator.py`

Update `SnapshotCalculator.calculate_snapshot()`:
- Currently receives `holdings: list[tuple[str, int, Decimal]]` (ticker, quantity, price)
- Create `HoldingBreakdown` objects from this data
- Pass them to `PortfolioSnapshot.create()`

### 3. Database Model — Add JSON column

**File**: `backend/src/zebu/adapters/outbound/database/models.py`

Add to `PortfolioSnapshotModel`:
```python
from sqlmodel import JSON, Column

holdings_breakdown: list[dict] | None = Field(
    default=None,
    sa_column=Column(JSON, nullable=True),
)
```

Update `to_domain()` and `from_domain()` to convert between `list[HoldingBreakdown]` and `list[dict]`.

### 4. Database Migration

Create an Alembic migration to add the `holdings_breakdown` JSON column:
```bash
cd backend && alembic revision --autogenerate -m "add holdings_breakdown to portfolio_snapshots"
```

The column is nullable so existing rows are unaffected.

### 5. Snapshot Job — Pass breakdown data through

**File**: `backend/src/zebu/application/services/snapshot_job.py`

The `holdings_data` list already has `(ticker, quantity, price)` tuples. Just pass this through to the calculator (step 2 handles the rest). No major changes needed here.

### 6. API Response — Extend performance endpoint

**File**: `backend/src/zebu/adapters/inbound/api/analytics.py`

Add breakdown to `DataPointSchema`:
```python
class HoldingBreakdownSchema(BaseModel):
    ticker: str
    quantity: int
    price_per_share: JsonFloat
    value: JsonFloat

class DataPointSchema(BaseModel):
    date: date
    total_value: JsonFloat
    cash_balance: JsonFloat
    holdings_value: JsonFloat
    holdings_breakdown: list[HoldingBreakdownSchema]  # NEW
```

Note: Use the existing `JsonFloat` type alias (`Annotated[Decimal, PlainSerializer(float)]`) defined in the same file for all Decimal fields.

### 7. Tests

Add/update tests for:
- `PortfolioSnapshot` entity with `holdings_breakdown` (validation, factory method)
- `SnapshotCalculator` preserving breakdown data
- `PortfolioSnapshotModel` JSON serialization round-trip
- Snapshot job passing breakdown through
- Performance API response including breakdown
- Backward compatibility: old snapshots with no breakdown return empty list

## Key Files to Modify
- `backend/src/zebu/domain/entities/portfolio_snapshot.py`
- `backend/src/zebu/domain/services/snapshot_calculator.py`
- `backend/src/zebu/application/services/snapshot_job.py`
- `backend/src/zebu/adapters/outbound/database/models.py`
- `backend/src/zebu/adapters/inbound/api/analytics.py`
- `backend/tests/` — corresponding test files

## Validation
- All existing tests pass (`python -m pytest tests/ -x -q`)
- Ruff + Pyright pass (`ruff check src/ && pyright src/`)
- New migration applies cleanly
- API response for an old snapshot (no breakdown) returns `holdings_breakdown: []`
- API response for a new snapshot returns the full breakdown

## Important Notes
- **Backward compatibility is critical** — old snapshots must still work (nullable column, default empty list)
- The JSON column stores plain dicts, not nested SQLModel models
- Keep `HoldingBreakdown` as a domain dataclass, not a Pydantic model
- The performance query handler doesn't need changes — it already returns full `PortfolioSnapshot` objects
- A follow-up frontend task will consume this data (Task 196)
