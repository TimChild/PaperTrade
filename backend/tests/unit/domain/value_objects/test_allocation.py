"""Tests for Allocation value object."""

from decimal import Decimal

import pytest

from zebu.domain.exceptions import InvalidAllocationError
from zebu.domain.value_objects.allocation import Allocation
from zebu.domain.value_objects.ticker import Ticker


class TestAllocationConstruction:
    """Tests for Allocation construction and validation."""

    def test_valid_construction_single_ticker(self) -> None:
        """Single-ticker 100% allocation is valid."""
        allocation = Allocation(weights={Ticker("AAPL"): Decimal("1.0")})
        assert allocation.fraction_for(Ticker("AAPL")) == Decimal("1.0")

    def test_valid_construction_multiple_tickers(self) -> None:
        """Multi-ticker allocation summing to 1.0 is valid."""
        allocation = Allocation(
            weights={
                Ticker("AAPL"): Decimal("0.6"),
                Ticker("GOOGL"): Decimal("0.4"),
            }
        )
        assert allocation.fraction_for(Ticker("AAPL")) == Decimal("0.6")
        assert allocation.fraction_for(Ticker("GOOGL")) == Decimal("0.4")

    def test_empty_allocation_raises_error(self) -> None:
        """Empty allocation raises InvalidAllocationError."""
        with pytest.raises(InvalidAllocationError, match="at least one ticker"):
            Allocation(weights={})

    def test_negative_weight_raises_error(self) -> None:
        """Negative weight raises InvalidAllocationError."""
        with pytest.raises(InvalidAllocationError, match=r"in \[0, 1\]"):
            Allocation(
                weights={
                    Ticker("AAPL"): Decimal("-0.1"),
                    Ticker("GOOGL"): Decimal("1.1"),
                }
            )

    def test_weight_above_one_raises_error(self) -> None:
        """Weight > 1.0 raises InvalidAllocationError."""
        with pytest.raises(InvalidAllocationError, match=r"in \[0, 1\]"):
            Allocation(weights={Ticker("AAPL"): Decimal("1.5")})

    def test_weights_not_summing_to_one_raises_error(self) -> None:
        """Weights summing to something other than 1.0 raise InvalidAllocationError."""
        with pytest.raises(InvalidAllocationError, match="must sum to 1.0"):
            Allocation(
                weights={
                    Ticker("AAPL"): Decimal("0.5"),
                    Ticker("GOOGL"): Decimal("0.4"),
                }
            )

    def test_sum_within_tolerance_is_accepted(self) -> None:
        """Sums within tolerance (~0.001) are accepted."""
        # 0.333 + 0.333 + 0.333 = 0.999 (within tolerance)
        allocation = Allocation(
            weights={
                Ticker("AAPL"): Decimal("0.333"),
                Ticker("GOOGL"): Decimal("0.333"),
                Ticker("MSFT"): Decimal("0.334"),
            }
        )
        assert allocation.fraction_for(Ticker("AAPL")) == Decimal("0.333")


class TestAllocationFromRaw:
    """Tests for the Allocation.from_raw constructor."""

    def test_from_raw_with_floats(self) -> None:
        """Float weights are converted to Decimal."""
        allocation = Allocation.from_raw({"AAPL": 0.6, "GOOGL": 0.4})
        assert allocation.fraction_for(Ticker("AAPL")) == Decimal("0.6")
        assert allocation.fraction_for(Ticker("GOOGL")) == Decimal("0.4")

    def test_from_raw_with_decimals(self) -> None:
        """Decimal weights pass through unchanged."""
        allocation = Allocation.from_raw(
            {"AAPL": Decimal("0.6"), "GOOGL": Decimal("0.4")}
        )
        assert allocation.fraction_for(Ticker("AAPL")) == Decimal("0.6")
        assert allocation.fraction_for(Ticker("GOOGL")) == Decimal("0.4")

    def test_from_raw_with_strings(self) -> None:
        """String weights parse via Decimal."""
        allocation = Allocation.from_raw({"AAPL": "1.0"})
        assert allocation.fraction_for(Ticker("AAPL")) == Decimal("1.0")

    def test_from_raw_lowercases_ticker(self) -> None:
        """Lowercase ticker symbols are normalised by Ticker."""
        allocation = Allocation.from_raw({"aapl": 1.0})
        assert allocation.fraction_for(Ticker("AAPL")) == Decimal("1.0")

    def test_from_raw_empty_raises_error(self) -> None:
        """Empty raw mapping raises InvalidAllocationError."""
        with pytest.raises(InvalidAllocationError, match="at least one ticker"):
            Allocation.from_raw({})


class TestAllocationFractionFor:
    """Tests for fraction_for() lookup."""

    def test_unknown_ticker_returns_zero(self) -> None:
        """Tickers not in the allocation return Decimal('0')."""
        allocation = Allocation.from_raw({"AAPL": 1.0})
        assert allocation.fraction_for(Ticker("MSFT")) == Decimal("0")


class TestAllocationEquality:
    """Tests for Allocation equality semantics."""

    def test_equal_allocations(self) -> None:
        """Allocations with the same weights are equal."""
        a = Allocation.from_raw({"AAPL": 0.6, "GOOGL": 0.4})
        b = Allocation.from_raw({"AAPL": 0.6, "GOOGL": 0.4})
        assert a == b

    def test_different_allocations_not_equal(self) -> None:
        """Allocations with different weights are not equal."""
        a = Allocation.from_raw({"AAPL": 1.0})
        b = Allocation.from_raw({"GOOGL": 1.0})
        assert a != b

    def test_hashable(self) -> None:
        """Allocations are hashable for use in sets/dict keys."""
        a = Allocation.from_raw({"AAPL": 1.0})
        assert {a, a} == {a}


class TestAllocationImmutability:
    """Tests for Allocation immutability."""

    def test_is_frozen(self) -> None:
        """Allocation is a frozen dataclass."""
        allocation = Allocation.from_raw({"AAPL": 1.0})
        with pytest.raises(AttributeError):
            allocation.weights = {}  # type: ignore[misc]
