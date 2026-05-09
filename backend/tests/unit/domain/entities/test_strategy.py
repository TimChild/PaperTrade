"""Tests for Strategy entity."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.domain.entities.strategy import Strategy
from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.strategy_parameters import (
    BuyAndHoldParameters,
    DcaParameters,
    MaCrossoverParameters,
)
from zebu.domain.value_objects.strategy_type import StrategyType


def _make_strategy(**overrides: object) -> Strategy:
    """Factory helper for building valid Strategy instances."""
    defaults: dict[str, object] = {
        "id": uuid4(),
        "user_id": uuid4(),
        "name": "My Strategy",
        "strategy_type": StrategyType.BUY_AND_HOLD,
        "tickers": ["AAPL"],
        "parameters": BuyAndHoldParameters(allocation={"AAPL": Decimal("1")}),
        "created_at": datetime.now(UTC) - timedelta(minutes=1),
    }
    defaults.update(overrides)
    return Strategy(**defaults)  # type: ignore[arg-type]


class TestStrategyConstruction:
    """Tests for valid and invalid Strategy construction."""

    def test_valid_construction(self) -> None:
        """Should create a Strategy with all valid fields."""
        strategy = _make_strategy()
        assert strategy.name == "My Strategy"
        assert strategy.strategy_type == StrategyType.BUY_AND_HOLD
        assert strategy.tickers == ["AAPL"]

    def test_valid_construction_with_multiple_tickers(self) -> None:
        """Should accept up to 10 tickers."""
        tickers = [f"T{i}" for i in range(10)]
        # Allocation must sum to 1.0; spread evenly across 10 tickers.
        allocation = {t: Decimal("0.1") for t in tickers}
        strategy = _make_strategy(
            tickers=tickers,
            parameters=BuyAndHoldParameters(allocation=allocation),
        )
        assert len(strategy.tickers) == 10

    def test_name_empty_raises_error(self) -> None:
        """Should raise InvalidStrategyError for empty name."""
        with pytest.raises(InvalidStrategyError, match="cannot be empty or whitespace"):
            _make_strategy(name="")

    def test_name_whitespace_only_raises_error(self) -> None:
        """Should raise InvalidStrategyError for whitespace-only name."""
        with pytest.raises(InvalidStrategyError, match="cannot be empty or whitespace"):
            _make_strategy(name="   ")

    def test_name_too_long_raises_error(self) -> None:
        """Should raise InvalidStrategyError for names exceeding 100 characters."""
        with pytest.raises(InvalidStrategyError, match="maximum 100 characters"):
            _make_strategy(name="x" * 101)

    def test_name_exactly_100_chars_is_valid(self) -> None:
        """Should allow names exactly 100 characters long."""
        strategy = _make_strategy(name="x" * 100)
        assert len(strategy.name) == 100

    def test_tickers_empty_raises_error(self) -> None:
        """Should raise InvalidStrategyError for empty tickers list."""
        with pytest.raises(InvalidStrategyError, match="between 1 and 10 tickers"):
            _make_strategy(tickers=[])

    def test_tickers_more_than_10_raises_error(self) -> None:
        """Should raise InvalidStrategyError for more than 10 tickers."""
        with pytest.raises(InvalidStrategyError, match="between 1 and 10 tickers"):
            _make_strategy(tickers=[f"T{i}" for i in range(11)])

    def test_future_created_at_raises_error(self) -> None:
        """Should raise InvalidStrategyError for future created_at."""
        future = datetime.now(UTC) + timedelta(hours=1)
        with pytest.raises(InvalidStrategyError, match="cannot be in the future"):
            _make_strategy(created_at=future)

    def test_parameters_type_must_match_strategy_type(self) -> None:
        """Should raise when parameters concrete type does not match strategy_type."""
        # BuyAndHoldParameters but strategy_type is DOLLAR_COST_AVERAGING
        with pytest.raises(InvalidStrategyError, match="does not match strategy_type"):
            _make_strategy(
                strategy_type=StrategyType.DOLLAR_COST_AVERAGING,
                parameters=BuyAndHoldParameters(allocation={"AAPL": Decimal("1")}),
            )

    def test_dca_strategy_with_dca_parameters_is_valid(self) -> None:
        """DCA strategy paired with DcaParameters constructs successfully."""
        strategy = _make_strategy(
            strategy_type=StrategyType.DOLLAR_COST_AVERAGING,
            parameters=DcaParameters(
                frequency_days=30,
                amount_per_period=Decimal("100"),
                allocation={"AAPL": Decimal("1")},
            ),
        )
        assert strategy.strategy_type == StrategyType.DOLLAR_COST_AVERAGING

    def test_ma_crossover_strategy_with_typed_parameters_is_valid(self) -> None:
        """MA crossover strategy paired with MaCrossoverParameters is valid."""
        strategy = _make_strategy(
            strategy_type=StrategyType.MOVING_AVERAGE_CROSSOVER,
            parameters=MaCrossoverParameters(
                fast_window=10,
                slow_window=20,
                invest_fraction=Decimal("0.5"),
            ),
        )
        assert strategy.strategy_type == StrategyType.MOVING_AVERAGE_CROSSOVER


class TestStrategyEquality:
    """Tests for Strategy equality semantics."""

    def test_equal_strategies_have_same_id(self) -> None:
        """Two Strategy objects with the same ID should be equal."""
        strategy_id = uuid4()
        a = _make_strategy(id=strategy_id)
        b = _make_strategy(id=strategy_id, name="Different Name")
        assert a == b

    def test_different_ids_are_not_equal(self) -> None:
        """Strategies with different IDs should not be equal."""
        assert _make_strategy() != _make_strategy()

    def test_not_equal_to_non_strategy(self) -> None:
        """Strategy should not be equal to a non-Strategy object."""
        assert _make_strategy() != "not a strategy"

    def test_hashable(self) -> None:
        """Strategy should be usable in sets and as dict keys."""
        strategy = _make_strategy()
        assert hash(strategy) == hash(strategy)
        s = {strategy}
        assert strategy in s

    def test_equal_strategies_have_same_hash(self) -> None:
        """Equal strategies (same ID) must have the same hash."""
        strategy_id = uuid4()
        a = _make_strategy(id=strategy_id)
        b = _make_strategy(id=strategy_id, name="Other")
        assert hash(a) == hash(b)
