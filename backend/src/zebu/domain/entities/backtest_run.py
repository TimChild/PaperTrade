"""BacktestRun entity - Represents a single execution of a backtest."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from zebu.domain.exceptions import InvalidBacktestRunError
from zebu.domain.value_objects.backtest_status import BacktestStatus


@dataclass(frozen=True)
class BacktestRun:
    """Represents a single backtest execution against historical market data.

    A BacktestRun captures the configuration used to run a backtest and stores
    the resulting performance metrics once the run completes.

    BacktestRun is fully immutable after creation. Equality and hashing are
    based on ``id`` only.

    Attributes:
        id: Unique backtest run identifier
        user_id: Owner of the run
        strategy_id: Reference to the strategy entity (None if strategy was deleted)
        portfolio_id: Portfolio created for this backtest
        strategy_snapshot: Complete copy of strategy config at time of run
        backtest_name: Human-readable label (1-100 characters)
        start_date: First date of the simulation window (inclusive)
        end_date: Last date of the simulation window (inclusive)
        initial_cash: Starting cash balance in USD
        status: Current lifecycle status of the run
        created_at: When the run was created (UTC)
        completed_at: When the run finished (UTC, None while pending/running)
        error_message: Human-readable failure reason (None unless FAILED)
        total_return_pct: Percentage return over the full period
        max_drawdown_pct: Maximum peak-to-trough drawdown percentage
        annualized_return_pct: Return annualized over the simulation period
        total_trades: Total number of buy/sell trades executed

    Raises:
        InvalidBacktestRunError: If any invariant is violated
    """

    id: UUID
    user_id: UUID
    strategy_id: UUID | None
    portfolio_id: UUID
    strategy_snapshot: dict[str, Any]  # noqa: ANN401
    backtest_name: str
    start_date: date
    end_date: date
    initial_cash: Decimal
    status: BacktestStatus
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    total_return_pct: Decimal | None = None
    max_drawdown_pct: Decimal | None = None
    annualized_return_pct: Decimal | None = None
    total_trades: int | None = None

    def __post_init__(self) -> None:
        """Validate BacktestRun invariants after initialization."""
        if not self.backtest_name or not self.backtest_name.strip():
            raise InvalidBacktestRunError("backtest_name cannot be empty or whitespace")
        if len(self.backtest_name) > 100:
            raise InvalidBacktestRunError(
                f"backtest_name must be maximum 100 characters, "
                f"got {len(self.backtest_name)}"
            )
        if self.start_date >= self.end_date:
            raise InvalidBacktestRunError("start_date must be before end_date")
        if self.end_date > date.today():
            raise InvalidBacktestRunError("end_date cannot be in the future")
        if self.initial_cash <= 0:
            raise InvalidBacktestRunError("initial_cash must be positive")

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only.

        Args:
            other: Object to compare

        Returns:
            True if other is BacktestRun with same ID
        """
        if not isinstance(other, BacktestRun):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets.

        Returns:
            Hash of backtest run ID
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "BacktestRun(id=UUID('...'), name='My Backtest')"
        """
        return (
            f"BacktestRun(id={self.id}, user_id={self.user_id}, "
            f"backtest_name='{self.backtest_name}')"
        )
