"""Tests for Holding entity (derived, not persisted)."""

from decimal import Decimal

from zebu.domain.entities.holding import Holding
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


class TestHoldingConstruction:
    """Tests for Holding construction."""

    def test_valid_construction(self) -> None:
        """Should create Holding with valid data."""
        ticker = Ticker("AAPL")
        quantity = Quantity(Decimal("10"))
        cost_basis = Money(Decimal("1000.00"))

        holding = Holding(ticker=ticker, quantity=quantity, cost_basis=cost_basis)

        assert holding.ticker == ticker
        assert holding.quantity == quantity
        assert holding.cost_basis == cost_basis

    def test_valid_construction_with_zero_quantity(self) -> None:
        """Should allow zero quantity (closed position)."""
        holding = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("0")),
            cost_basis=Money(Decimal("0.00")),
        )
        assert holding.quantity.is_zero()
        assert holding.cost_basis.is_zero()


class TestHoldingCalculations:
    """Tests for Holding calculated properties."""

    def test_average_cost_per_share(self) -> None:
        """Should calculate average cost per share correctly."""
        holding = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1500.00")),
        )

        avg_cost = holding.average_cost_per_share
        assert avg_cost is not None
        assert avg_cost.amount == Decimal("150.00")

    def test_average_cost_per_share_with_zero_quantity(self) -> None:
        """Should return None for average cost when quantity is zero."""
        holding = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("0")),
            cost_basis=Money(Decimal("0.00")),
        )

        assert holding.average_cost_per_share is None


class TestHoldingEquality:
    """Tests for Holding equality semantics."""

    def test_equality_based_on_all_fields(self) -> None:
        """Holdings should be equal only if ticker, quantity, AND cost_basis match."""
        h1 = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1000.00")),
        )
        h2 = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1000.00")),
        )

        assert h1 == h2

    def test_inequality_different_quantity(self) -> None:
        """Holdings with same ticker but different quantity should not be equal."""
        h1 = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1000.00")),
        )
        h2 = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("20")),  # Different quantity
            cost_basis=Money(Decimal("2000.00")),
        )

        assert h1 != h2

    def test_inequality_different_cost_basis(self) -> None:
        """Holdings with same ticker and quantity.

        But different cost should not be equal.
        """
        h1 = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1000.00")),
        )
        h2 = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1500.00")),  # Different cost
        )

        assert h1 != h2

    def test_inequality_different_tickers(self) -> None:
        """Holdings with different tickers should not be equal."""
        h1 = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1000.00")),
        )
        h2 = Holding(
            ticker=Ticker("MSFT"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1000.00")),
        )

        assert h1 != h2


class TestHoldingStringRepresentation:
    """Tests for Holding string representation."""

    def test_repr_representation(self) -> None:
        """Should have useful repr."""
        holding = Holding(
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            cost_basis=Money(Decimal("1500.00")),
        )
        repr_str = repr(holding)
        assert "Holding" in repr_str
        assert "AAPL" in repr_str
        assert "10" in repr_str
