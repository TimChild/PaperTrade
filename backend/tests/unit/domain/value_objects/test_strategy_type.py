"""Tests for StrategyType value object."""

from zebu.domain.value_objects.strategy_type import StrategyType


class TestStrategyType:
    """Tests for StrategyType enum."""

    def test_buy_and_hold_value(self) -> None:
        """BUY_AND_HOLD should have the expected string value."""
        assert StrategyType.BUY_AND_HOLD.value == "BUY_AND_HOLD"

    def test_dollar_cost_averaging_value(self) -> None:
        """DOLLAR_COST_AVERAGING should have the expected string value."""
        assert StrategyType.DOLLAR_COST_AVERAGING.value == "DOLLAR_COST_AVERAGING"

    def test_moving_average_crossover_value(self) -> None:
        """MOVING_AVERAGE_CROSSOVER should have the expected string value."""
        assert StrategyType.MOVING_AVERAGE_CROSSOVER.value == "MOVING_AVERAGE_CROSSOVER"

    def test_all_members_present(self) -> None:
        """Enum should contain exactly the expected members."""
        assert set(StrategyType) == {
            StrategyType.BUY_AND_HOLD,
            StrategyType.DOLLAR_COST_AVERAGING,
            StrategyType.MOVING_AVERAGE_CROSSOVER,
        }

    def test_from_string_round_trip(self) -> None:
        """Should reconstruct enum from its string value."""
        assert StrategyType("BUY_AND_HOLD") == StrategyType.BUY_AND_HOLD
