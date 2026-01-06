# Task 057: Phase 3c Analytics - Database & Repository

**Status**: Not Started
**Depends On**: Task 056 (Domain Layer) complete
**Blocks**: Tasks 058, 059, 060
**Estimated Effort**: 2 days

## Objective

Implement database schema and repository for portfolio snapshots to enable analytics data persistence and retrieval.

## Reference Architecture

Full specification: `architecture_plans/phase3-refined/phase3c-analytics.md` (see "Database Schema Changes" section)

## Success Criteria

- [ ] `portfolio_snapshots` table created via SQLModel
- [ ] `SnapshotRepository` port and SQLite/PostgreSQL adapters implemented
- [ ] Proper indexes for performance (portfolio_id, snapshot_date)
- [ ] Integration tests for repository operations
- [ ] All existing tests still pass
- [ ] No new lint/type errors

## Implementation Details

### 1. SQLModel for PortfolioSnapshot

**Location**: `backend/app/adapters/repositories/models.py` (add to existing)

```python
from sqlmodel import SQLModel, Field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

class PortfolioSnapshotModel(SQLModel, table=True):
    """Database model for portfolio snapshots."""

    __tablename__ = "portfolio_snapshots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    portfolio_id: UUID = Field(foreign_key="portfolios.id", nullable=False, index=True)
    snapshot_date: date = Field(nullable=False)
    total_value: Decimal = Field(max_digits=15, decimal_places=2, nullable=False)
    cash_balance: Decimal = Field(max_digits=15, decimal_places=2, nullable=False)
    holdings_value: Decimal = Field(max_digits=15, decimal_places=2, nullable=False)
    holdings_count: int = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        # Unique constraint on (portfolio_id, snapshot_date)
        pass
```

**Note**: Add unique constraint via SQLAlchemy for (portfolio_id, snapshot_date) combination.

### 2. Snapshot Repository Port

**Location**: `backend/app/application/ports/snapshot_repository.py`

```python
from abc import ABC, abstractmethod
from datetime import date
from typing import Sequence
from uuid import UUID

from app.domain.entities.portfolio_snapshot import PortfolioSnapshot

class SnapshotRepositoryPort(ABC):
    """Port for portfolio snapshot persistence."""

    @abstractmethod
    async def save(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        """Save a snapshot. Updates if exists for same portfolio+date."""
        pass

    @abstractmethod
    async def get_by_portfolio_and_date(
        self, portfolio_id: UUID, snapshot_date: date
    ) -> PortfolioSnapshot | None:
        """Get snapshot for a specific date."""
        pass

    @abstractmethod
    async def get_range(
        self,
        portfolio_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Sequence[PortfolioSnapshot]:
        """Get snapshots for a date range (inclusive)."""
        pass

    @abstractmethod
    async def get_latest(self, portfolio_id: UUID) -> PortfolioSnapshot | None:
        """Get the most recent snapshot."""
        pass

    @abstractmethod
    async def delete_by_portfolio(self, portfolio_id: UUID) -> int:
        """Delete all snapshots for a portfolio. Returns count deleted."""
        pass
```

### 3. SQLModel Repository Adapter

**Location**: `backend/app/adapters/repositories/sqlmodel_snapshot_repository.py`

```python
from datetime import date
from typing import Sequence
from uuid import UUID

from sqlmodel import Session, select

from app.application.ports.snapshot_repository import SnapshotRepositoryPort
from app.domain.entities.portfolio_snapshot import PortfolioSnapshot
from app.adapters.repositories.models import PortfolioSnapshotModel

class SQLModelSnapshotRepository(SnapshotRepositoryPort):
    """SQLModel implementation of snapshot repository."""

    def __init__(self, session: Session):
        self._session = session

    async def save(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        # Check if exists (upsert logic)
        existing = await self.get_by_portfolio_and_date(
            snapshot.portfolio_id, snapshot.snapshot_date
        )

        if existing:
            # Update existing
            statement = select(PortfolioSnapshotModel).where(
                PortfolioSnapshotModel.id == existing.id
            )
            model = self._session.exec(statement).one()
            model.total_value = snapshot.total_value
            model.cash_balance = snapshot.cash_balance
            model.holdings_value = snapshot.holdings_value
            model.holdings_count = snapshot.holdings_count
            self._session.add(model)
        else:
            # Create new
            model = PortfolioSnapshotModel(
                id=snapshot.id,
                portfolio_id=snapshot.portfolio_id,
                snapshot_date=snapshot.snapshot_date,
                total_value=snapshot.total_value,
                cash_balance=snapshot.cash_balance,
                holdings_value=snapshot.holdings_value,
                holdings_count=snapshot.holdings_count,
                created_at=snapshot.created_at,
            )
            self._session.add(model)

        self._session.commit()
        self._session.refresh(model)
        return self._to_domain(model)

    async def get_by_portfolio_and_date(
        self, portfolio_id: UUID, snapshot_date: date
    ) -> PortfolioSnapshot | None:
        statement = select(PortfolioSnapshotModel).where(
            PortfolioSnapshotModel.portfolio_id == portfolio_id,
            PortfolioSnapshotModel.snapshot_date == snapshot_date,
        )
        result = self._session.exec(statement).first()
        return self._to_domain(result) if result else None

    async def get_range(
        self,
        portfolio_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Sequence[PortfolioSnapshot]:
        statement = (
            select(PortfolioSnapshotModel)
            .where(
                PortfolioSnapshotModel.portfolio_id == portfolio_id,
                PortfolioSnapshotModel.snapshot_date >= start_date,
                PortfolioSnapshotModel.snapshot_date <= end_date,
            )
            .order_by(PortfolioSnapshotModel.snapshot_date)
        )
        results = self._session.exec(statement).all()
        return [self._to_domain(r) for r in results]

    async def get_latest(self, portfolio_id: UUID) -> PortfolioSnapshot | None:
        statement = (
            select(PortfolioSnapshotModel)
            .where(PortfolioSnapshotModel.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshotModel.snapshot_date.desc())
            .limit(1)
        )
        result = self._session.exec(statement).first()
        return self._to_domain(result) if result else None

    async def delete_by_portfolio(self, portfolio_id: UUID) -> int:
        statement = select(PortfolioSnapshotModel).where(
            PortfolioSnapshotModel.portfolio_id == portfolio_id
        )
        results = self._session.exec(statement).all()
        count = len(results)
        for model in results:
            self._session.delete(model)
        self._session.commit()
        return count

    def _to_domain(self, model: PortfolioSnapshotModel) -> PortfolioSnapshot:
        """Convert database model to domain entity."""
        return PortfolioSnapshot(
            id=model.id,
            portfolio_id=model.portfolio_id,
            snapshot_date=model.snapshot_date,
            total_value=model.total_value,
            cash_balance=model.cash_balance,
            holdings_value=model.holdings_value,
            holdings_count=model.holdings_count,
            created_at=model.created_at,
        )
```

### 4. Database Migration

Ensure the `portfolio_snapshots` table is created when the app starts. SQLModel handles this via `SQLModel.metadata.create_all(engine)`.

**Add indexes** (important for performance):
- Index on `(portfolio_id, snapshot_date)` - Range queries for charts
- Index on `snapshot_date` alone - Batch processing by date

### 5. Integration Tests

**Location**: `backend/tests/adapters/test_snapshot_repository.py`

Required tests:
- `test_save_new_snapshot`
- `test_save_updates_existing_snapshot`
- `test_get_by_portfolio_and_date_found`
- `test_get_by_portfolio_and_date_not_found`
- `test_get_range_returns_ordered_snapshots`
- `test_get_range_empty_when_no_data`
- `test_get_latest_returns_most_recent`
- `test_delete_by_portfolio_removes_all`

## Implementation Order

1. Add `PortfolioSnapshotModel` to models.py
2. Create `SnapshotRepositoryPort` interface
3. Implement `SQLModelSnapshotRepository`
4. Add integration tests
5. Update dependency injection in `dependencies.py`
6. Run full test suite

## Commands

```bash
# Run repository tests
cd backend && uv run pytest tests/adapters/test_snapshot_repository.py -v

# Run all adapter tests
cd backend && uv run pytest tests/adapters/ -v

# Full backend test suite
task test:backend
```

## Notes

- Follow existing repository patterns in `backend/app/adapters/repositories/`
- Use `session.exec()` (SQLModel) not `session.execute()` (deprecated SQLAlchemy)
- The repository handles upsert logic (update if exists, insert if new)
- Indexes are critical for chart performance with large datasets
