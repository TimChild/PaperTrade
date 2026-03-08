"""StrategyType value object - strategy algorithm discriminator."""

from enum import Enum


class StrategyType(Enum):
    """Represents the type of a trading strategy."""

    BUY_AND_HOLD = "BUY_AND_HOLD"
    DOLLAR_COST_AVERAGING = "DOLLAR_COST_AVERAGING"
    MOVING_AVERAGE_CROSSOVER = "MOVING_AVERAGE_CROSSOVER"
