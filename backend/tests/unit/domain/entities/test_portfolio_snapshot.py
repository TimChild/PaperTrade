"""Tests for PortfolioSnapshot entity."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.domain.entities.portfolio_snapshot import HoldingBreakdown, PortfolioSnapshot
from zebu.domain.exceptions import InvalidPortfolioError


class TestPortfolioSnapshotConstruction:
    """Tests for PortfolioSnapshot construction and validation."""

    def test_valid_construction(self) -> None:
        """Should create PortfolioSnapshot with valid data."""
        snapshot_id = uuid4()
        portfolio_id = uuid4()
        snapshot_date = date.today()
        created_at = datetime.now(UTC)

        snapshot = PortfolioSnapshot(
            id=snapshot_id,
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            total_value=Decimal("10000.00"),
            cash_balance=Decimal("5000.00"),
            holdings_value=Decimal("5000.00"),
            holdings_count=3,
            created_at=created_at,
        )

        assert snapshot.id == snapshot_id
        assert snapshot.portfolio_id == portfolio_id
        assert snapshot.snapshot_date == snapshot_date
        assert snapshot.total_value == Decimal("10000.00")
        assert snapshot.cash_balance == Decimal("5000.00")
        assert snapshot.holdings_value == Decimal("5000.00")
        assert snapshot.holdings_count == 3
        assert snapshot.created_at == created_at

    def test_create_snapshot_with_only_cash(self) -> None:
        """Should create snapshot with only cash, no holdings."""
        portfolio_id = uuid4()
        snapshot_date = date.today()

        snapshot = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
        )

        assert snapshot.portfolio_id == portfolio_id
        assert snapshot.snapshot_date == snapshot_date
        assert snapshot.total_value == Decimal("10000.00")
        assert snapshot.cash_balance == Decimal("10000.00")
        assert snapshot.holdings_value == Decimal("0.00")
        assert snapshot.holdings_count == 0
        # Verify auto-generated fields
        assert snapshot.id is not None
        assert snapshot.created_at is not None

    def test_create_snapshot_with_holdings(self) -> None:
        """Should create snapshot with both cash and holdings."""
        portfolio_id = uuid4()
        snapshot_date = date.today()

        snapshot = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("5000.00"),
            holdings_value=Decimal("7500.50"),
            holdings_count=5,
        )

        assert snapshot.total_value == Decimal("12500.50")
        assert snapshot.cash_balance == Decimal("5000.00")
        assert snapshot.holdings_value == Decimal("7500.50")
        assert snapshot.holdings_count == 5

    def test_create_snapshot_zero_holdings(self) -> None:
        """Should create snapshot when all holdings have been sold."""
        portfolio_id = uuid4()
        snapshot_date = date.today()

        snapshot = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("12500.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
        )

        assert snapshot.total_value == Decimal("12500.00")
        assert snapshot.holdings_value == Decimal("0.00")
        assert snapshot.holdings_count == 0

    def test_snapshot_total_value_invariant(self) -> None:
        """Should enforce total_value = cash_balance + holdings_value."""
        portfolio_id = uuid4()

        # This should raise because total doesn't match sum
        with pytest.raises(InvalidPortfolioError, match="total_value must equal"):
            PortfolioSnapshot(
                id=uuid4(),
                portfolio_id=portfolio_id,
                snapshot_date=date.today(),
                total_value=Decimal("10000.00"),  # Wrong total
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("6000.00"),  # Sum = 11000, not 10000
                holdings_count=2,
                created_at=datetime.now(UTC),
            )

    def test_snapshot_non_negative_values(self) -> None:
        """Should reject negative monetary values."""
        portfolio_id = uuid4()

        # Negative cash_balance
        with pytest.raises(
            InvalidPortfolioError, match="cash_balance cannot be negative"
        ):
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date.today(),
                cash_balance=Decimal("-100.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )

        # Negative holdings_value
        with pytest.raises(
            InvalidPortfolioError, match="holdings_value cannot be negative"
        ):
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date.today(),
                cash_balance=Decimal("0.00"),
                holdings_value=Decimal("-500.00"),
                holdings_count=0,
            )

    def test_snapshot_future_date_rejected(self) -> None:
        """Should reject snapshot_date in the future."""
        portfolio_id = uuid4()
        future_date = date.today() + timedelta(days=1)

        with pytest.raises(InvalidPortfolioError, match="cannot be in the future"):
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=future_date,
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )

    def test_snapshot_past_date_allowed(self) -> None:
        """Should allow snapshot_date in the past."""
        portfolio_id = uuid4()
        past_date = date.today() - timedelta(days=30)

        snapshot = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=past_date,
            cash_balance=Decimal("5000.00"),
            holdings_value=Decimal("5000.00"),
            holdings_count=2,
        )

        assert snapshot.snapshot_date == past_date

    def test_snapshot_negative_holdings_count_rejected(self) -> None:
        """Should reject negative holdings_count."""
        portfolio_id = uuid4()

        with pytest.raises(
            InvalidPortfolioError, match="holdings_count cannot be negative"
        ):
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date.today(),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=-1,
            )


class TestPortfolioSnapshotEquality:
    """Tests for PortfolioSnapshot equality and hashing."""

    def test_equality_based_on_id(self) -> None:
        """Should consider snapshots equal if IDs match."""
        snapshot_id = uuid4()
        portfolio_id = uuid4()

        snapshot1 = PortfolioSnapshot(
            id=snapshot_id,
            portfolio_id=portfolio_id,
            snapshot_date=date.today(),
            total_value=Decimal("10000.00"),
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
            created_at=datetime.now(UTC),
        )

        snapshot2 = PortfolioSnapshot(
            id=snapshot_id,  # Same ID
            portfolio_id=uuid4(),  # Different portfolio
            snapshot_date=date.today() - timedelta(days=1),  # Different date
            total_value=Decimal("5000.00"),  # Different value
            cash_balance=Decimal("5000.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
            created_at=datetime.now(UTC),
        )

        assert snapshot1 == snapshot2

    def test_inequality_with_different_ids(self) -> None:
        """Should consider snapshots unequal if IDs differ."""
        portfolio_id = uuid4()

        snapshot1 = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=date.today(),
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
        )

        snapshot2 = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=date.today(),
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
        )

        assert snapshot1 != snapshot2

    def test_inequality_with_non_snapshot(self) -> None:
        """Should not equal non-PortfolioSnapshot objects."""
        snapshot = PortfolioSnapshot.create(
            portfolio_id=uuid4(),
            snapshot_date=date.today(),
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
        )

        assert snapshot != "not a snapshot"
        assert snapshot != 123
        assert snapshot is not None

    def test_hash_based_on_id(self) -> None:
        """Should hash consistently based on ID."""
        snapshot = PortfolioSnapshot.create(
            portfolio_id=uuid4(),
            snapshot_date=date.today(),
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
        )

        # Hash should be consistent
        assert hash(snapshot) == hash(snapshot.id)

        # Can be used in sets/dicts
        snapshot_set = {snapshot}
        assert snapshot in snapshot_set


class TestPortfolioSnapshotRepresentation:
    """Tests for PortfolioSnapshot string representation."""

    def test_repr(self) -> None:
        """Should have meaningful repr for debugging."""
        snapshot_id = uuid4()
        portfolio_id = uuid4()

        snapshot = PortfolioSnapshot(
            id=snapshot_id,
            portfolio_id=portfolio_id,
            snapshot_date=date(2024, 1, 15),
            total_value=Decimal("10000.00"),
            cash_balance=Decimal("5000.00"),
            holdings_value=Decimal("5000.00"),
            holdings_count=3,
            created_at=datetime.now(UTC),
        )

        repr_str = repr(snapshot)
        assert "PortfolioSnapshot" in repr_str
        assert str(snapshot_id) in repr_str
        assert str(portfolio_id) in repr_str
        assert "2024-01-15" in repr_str
        assert "10000.00" in repr_str


class TestHoldingBreakdown:
    """Tests for HoldingBreakdown dataclass."""

    def test_holding_breakdown_construction(self) -> None:
        """Should create HoldingBreakdown with valid data."""
        breakdown = HoldingBreakdown(
            ticker="AAPL",
            quantity=10,
            price_per_share=Decimal("150.00"),
            value=Decimal("1500.00"),
        )

        assert breakdown.ticker == "AAPL"
        assert breakdown.quantity == 10
        assert breakdown.price_per_share == Decimal("150.00")
        assert breakdown.value == Decimal("1500.00")

    def test_holding_breakdown_is_frozen(self) -> None:
        """HoldingBreakdown should be immutable."""
        breakdown = HoldingBreakdown(
            ticker="AAPL",
            quantity=10,
            price_per_share=Decimal("150.00"),
            value=Decimal("1500.00"),
        )

        with pytest.raises((AttributeError, TypeError)):
            breakdown.ticker = "MSFT"  # type: ignore[misc]


class TestPortfolioSnapshotWithBreakdown:
    """Tests for PortfolioSnapshot with holdings_breakdown field."""

    def test_create_snapshot_with_breakdown(self) -> None:
        """Should create snapshot with holdings_breakdown."""
        portfolio_id = uuid4()
        snapshot_date = date.today()
        breakdown = [
            HoldingBreakdown(
                ticker="AAPL",
                quantity=10,
                price_per_share=Decimal("150.00"),
                value=Decimal("1500.00"),
            ),
            HoldingBreakdown(
                ticker="MSFT",
                quantity=5,
                price_per_share=Decimal("300.00"),
                value=Decimal("1500.00"),
            ),
        ]

        snapshot = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("7000.00"),
            holdings_value=Decimal("3000.00"),
            holdings_count=2,
            holdings_breakdown=breakdown,
        )

        assert snapshot.holdings_breakdown == breakdown
        assert len(snapshot.holdings_breakdown) == 2

    def test_create_snapshot_without_breakdown_defaults_to_empty(self) -> None:
        """Should default holdings_breakdown to empty list when not provided."""
        snapshot = PortfolioSnapshot.create(
            portfolio_id=uuid4(),
            snapshot_date=date.today(),
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("0.00"),
            holdings_count=0,
        )

        assert snapshot.holdings_breakdown == []

    def test_snapshot_breakdown_sum_must_match_holdings_value(self) -> None:
        """Should reject breakdown where sum doesn't equal holdings_value."""
        breakdown = [
            HoldingBreakdown(
                ticker="AAPL",
                quantity=10,
                price_per_share=Decimal("150.00"),
                value=Decimal("1500.00"),
            ),
        ]

        with pytest.raises(
            InvalidPortfolioError, match="sum of holdings_breakdown values"
        ):
            PortfolioSnapshot.create(
                portfolio_id=uuid4(),
                snapshot_date=date.today(),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("2000.00"),  # Wrong: breakdown sums to 1500
                holdings_count=1,
                holdings_breakdown=breakdown,
            )

    def test_empty_breakdown_with_nonzero_holdings_value_is_allowed(self) -> None:
        """Empty breakdown with non-zero holdings_value should be allowed (backward compat)."""
        snapshot = PortfolioSnapshot.create(
            portfolio_id=uuid4(),
            snapshot_date=date.today(),
            cash_balance=Decimal("5000.00"),
            holdings_value=Decimal("3000.00"),
            holdings_count=2,
            holdings_breakdown=None,
        )

        # Old snapshots have no breakdown data but still valid
        assert snapshot.holdings_breakdown == []
        assert snapshot.holdings_value == Decimal("3000.00")

    def test_direct_construction_with_breakdown(self) -> None:
        """Should construct PortfolioSnapshot directly with breakdown."""
        snapshot_id = uuid4()
        portfolio_id = uuid4()
        breakdown = [
            HoldingBreakdown(
                ticker="AAPL",
                quantity=10,
                price_per_share=Decimal("150.00"),
                value=Decimal("1500.00"),
            ),
        ]

        snapshot = PortfolioSnapshot(
            id=snapshot_id,
            portfolio_id=portfolio_id,
            snapshot_date=date.today(),
            total_value=Decimal("6500.00"),
            cash_balance=Decimal("5000.00"),
            holdings_value=Decimal("1500.00"),
            holdings_count=1,
            created_at=datetime.now(UTC),
            holdings_breakdown=breakdown,
        )

        assert snapshot.holdings_breakdown == breakdown
