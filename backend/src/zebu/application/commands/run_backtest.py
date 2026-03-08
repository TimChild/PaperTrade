"""RunBacktestCommand - Command for triggering a backtest execution."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class RunBacktestCommand:
    """Command to run a backtest simulation.

    Attributes:
        user_id: ID of the user requesting the backtest
        strategy_id: ID of the strategy to backtest
        backtest_name: Human-readable name for this run
        start_date: First day of the simulation (inclusive)
        end_date: Last day of the simulation (inclusive)
        initial_cash: Starting cash balance in USD
    """

    user_id: UUID
    strategy_id: UUID
    backtest_name: str
    start_date: date
    end_date: date
    initial_cash: Decimal
