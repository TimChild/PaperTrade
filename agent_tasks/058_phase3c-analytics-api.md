# Task 058: Phase 3c Analytics - API Endpoints

**Status**: Not Started
**Depends On**: Tasks 056, 057 (Domain & Repository) complete
**Blocks**: Task 059 (Frontend Charts)
**Estimated Effort**: 2-3 days

## Objective

Implement API endpoints for portfolio analytics: performance data over time, portfolio composition, and performance metrics.

## Reference Architecture

Full specification: `architecture_plans/phase3-refined/phase3c-analytics.md` (see "API Changes" section)

## Success Criteria

- [ ] `GET /api/v1/portfolios/{id}/performance` endpoint implemented
- [ ] `GET /api/v1/portfolios/{id}/composition` endpoint implemented
- [ ] Time range filtering (1W, 1M, 3M, 1Y, ALL)
- [ ] Performance metrics calculated and returned
- [ ] API tests pass
- [ ] All existing tests still pass
- [ ] No new lint/type errors

## Implementation Details

### 1. Use Cases

**Location**: `backend/app/application/use_cases/`

#### GetPortfolioPerformanceUseCase

**File**: `backend/app/application/use_cases/get_portfolio_performance.py`

```python
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Sequence
from uuid import UUID

from app.application.ports.snapshot_repository import SnapshotRepositoryPort
from app.domain.entities.portfolio_snapshot import PortfolioSnapshot
from app.domain.value_objects.performance_metrics import PerformanceMetrics

class TimeRange(str, Enum):
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    ONE_YEAR = "1Y"
    ALL = "ALL"

@dataclass
class PerformanceData:
    portfolio_id: UUID
    time_range: TimeRange
    data_points: Sequence[PortfolioSnapshot]
    metrics: PerformanceMetrics | None  # None if insufficient data

class GetPortfolioPerformanceUseCase:
    def __init__(self, snapshot_repo: SnapshotRepositoryPort):
        self._snapshot_repo = snapshot_repo

    async def execute(
        self,
        portfolio_id: UUID,
        time_range: TimeRange,
    ) -> PerformanceData:
        today = date.today()
        start_date = self._calculate_start_date(today, time_range)

        snapshots = await self._snapshot_repo.get_range(
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=today,
        )

        metrics = None
        if len(snapshots) >= 2:
            metrics = PerformanceMetrics.calculate(list(snapshots))

        return PerformanceData(
            portfolio_id=portfolio_id,
            time_range=time_range,
            data_points=snapshots,
            metrics=metrics,
        )

    def _calculate_start_date(self, end_date: date, time_range: TimeRange) -> date:
        match time_range:
            case TimeRange.ONE_WEEK:
                return end_date - timedelta(days=7)
            case TimeRange.ONE_MONTH:
                return end_date - timedelta(days=30)
            case TimeRange.THREE_MONTHS:
                return end_date - timedelta(days=90)
            case TimeRange.ONE_YEAR:
                return end_date - timedelta(days=365)
            case TimeRange.ALL:
                return date(2000, 1, 1)  # Far past date
```

#### GetPortfolioCompositionUseCase

**File**: `backend/app/application/use_cases/get_portfolio_composition.py`

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from app.application.ports.portfolio_repository import PortfolioRepositoryPort
from app.application.ports.market_data import MarketDataPort

@dataclass
class CompositionItem:
    ticker: str
    value: Decimal
    percentage: Decimal
    quantity: int | None  # None for cash

@dataclass
class PortfolioComposition:
    portfolio_id: UUID
    total_value: Decimal
    composition: Sequence[CompositionItem]

class GetPortfolioCompositionUseCase:
    def __init__(
        self,
        portfolio_repo: PortfolioRepositoryPort,
        market_data: MarketDataPort,
    ):
        self._portfolio_repo = portfolio_repo
        self._market_data = market_data

    async def execute(self, portfolio_id: UUID) -> PortfolioComposition:
        portfolio = await self._portfolio_repo.get(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        # Get holdings with current values
        items: list[CompositionItem] = []
        total_value = portfolio.cash_balance

        for ticker, quantity in portfolio.holdings.items():
            price = await self._market_data.get_current_price(ticker)
            value = Decimal(quantity) * price.price
            total_value += value
            items.append(CompositionItem(
                ticker=ticker,
                value=value,
                percentage=Decimal("0"),  # Calculate after total known
                quantity=quantity,
            ))

        # Add cash
        items.append(CompositionItem(
            ticker="CASH",
            value=portfolio.cash_balance,
            percentage=Decimal("0"),
            quantity=None,
        ))

        # Calculate percentages
        if total_value > 0:
            for item in items:
                item.percentage = (item.value / total_value * 100).quantize(Decimal("0.1"))

        return PortfolioComposition(
            portfolio_id=portfolio_id,
            total_value=total_value,
            composition=items,
        )
```

### 2. API Router

**Location**: `backend/app/adapters/api/routes/analytics.py` (new file)

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from app.adapters.api.dependencies import get_snapshot_repository, get_portfolio_repository, get_market_data
from app.application.use_cases.get_portfolio_performance import (
    GetPortfolioPerformanceUseCase,
    TimeRange,
)
from app.application.use_cases.get_portfolio_composition import (
    GetPortfolioCompositionUseCase,
)
from app.adapters.api.schemas.analytics import (
    PerformanceResponse,
    CompositionResponse,
)

router = APIRouter(prefix="/portfolios", tags=["analytics"])

@router.get("/{portfolio_id}/performance", response_model=PerformanceResponse)
async def get_performance(
    portfolio_id: UUID,
    range: TimeRange = Query(default=TimeRange.ONE_MONTH, alias="range"),
    snapshot_repo=Depends(get_snapshot_repository),
):
    """Get portfolio performance data for charts."""
    use_case = GetPortfolioPerformanceUseCase(snapshot_repo)
    result = await use_case.execute(portfolio_id, range)
    return PerformanceResponse.from_domain(result)

@router.get("/{portfolio_id}/composition", response_model=CompositionResponse)
async def get_composition(
    portfolio_id: UUID,
    portfolio_repo=Depends(get_portfolio_repository),
    market_data=Depends(get_market_data),
):
    """Get portfolio holdings composition for pie chart."""
    use_case = GetPortfolioCompositionUseCase(portfolio_repo, market_data)
    try:
        result = await use_case.execute(portfolio_id)
        return CompositionResponse.from_domain(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### 3. API Schemas

**Location**: `backend/app/adapters/api/schemas/analytics.py` (new file)

```python
from datetime import date
from decimal import Decimal
from pydantic import BaseModel
from typing import Sequence
from uuid import UUID

class DataPointSchema(BaseModel):
    date: date
    total_value: Decimal
    cash_balance: Decimal
    holdings_value: Decimal

class MetricsSchema(BaseModel):
    starting_value: Decimal
    ending_value: Decimal
    absolute_gain: Decimal
    percentage_gain: Decimal
    highest_value: Decimal
    lowest_value: Decimal

class PerformanceResponse(BaseModel):
    portfolio_id: UUID
    range: str
    data_points: list[DataPointSchema]
    metrics: MetricsSchema | None

    @classmethod
    def from_domain(cls, data):
        return cls(
            portfolio_id=data.portfolio_id,
            range=data.time_range.value,
            data_points=[
                DataPointSchema(
                    date=s.snapshot_date,
                    total_value=s.total_value,
                    cash_balance=s.cash_balance,
                    holdings_value=s.holdings_value,
                )
                for s in data.data_points
            ],
            metrics=MetricsSchema(
                starting_value=data.metrics.starting_value,
                ending_value=data.metrics.ending_value,
                absolute_gain=data.metrics.absolute_gain,
                percentage_gain=data.metrics.percentage_gain,
                highest_value=data.metrics.highest_value,
                lowest_value=data.metrics.lowest_value,
            ) if data.metrics else None,
        )

class CompositionItemSchema(BaseModel):
    ticker: str
    value: Decimal
    percentage: Decimal
    quantity: int | None

class CompositionResponse(BaseModel):
    portfolio_id: UUID
    total_value: Decimal
    composition: list[CompositionItemSchema]

    @classmethod
    def from_domain(cls, data):
        return cls(
            portfolio_id=data.portfolio_id,
            total_value=data.total_value,
            composition=[
                CompositionItemSchema(
                    ticker=item.ticker,
                    value=item.value,
                    percentage=item.percentage,
                    quantity=item.quantity,
                )
                for item in data.composition
            ],
        )
```

### 4. Register Router

Update `backend/app/adapters/api/main.py` to include the analytics router:

```python
from app.adapters.api.routes.analytics import router as analytics_router

app.include_router(analytics_router, prefix="/api/v1")
```

### 5. API Tests

**Location**: `backend/tests/api/test_analytics_api.py`

Required tests:
- `test_get_performance_success_with_data`
- `test_get_performance_empty_data`
- `test_get_performance_different_time_ranges`
- `test_get_performance_invalid_portfolio`
- `test_get_composition_success`
- `test_get_composition_portfolio_not_found`
- `test_get_composition_cash_only_portfolio`

## Implementation Order

1. Create use cases (GetPortfolioPerformanceUseCase, GetPortfolioCompositionUseCase)
2. Create Pydantic schemas
3. Create API router
4. Register router in main app
5. Add dependency injection for snapshot repository
6. Write API tests
7. Run full test suite

## Commands

```bash
# Run API tests only
cd backend && uv run pytest tests/api/test_analytics_api.py -v

# Run all API tests
cd backend && uv run pytest tests/api/ -v

# Full backend test suite
task test:backend
```

## Notes

- Follow existing API patterns in `backend/app/adapters/api/routes/`
- Use Query parameter with alias for `range` (Python reserved word)
- Performance endpoint requires snapshots to exist (created by background job)
- Composition endpoint calculates live from current holdings + prices
- All endpoints require authentication (add auth dependency)
