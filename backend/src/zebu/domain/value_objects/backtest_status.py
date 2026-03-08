"""BacktestStatus value object - lifecycle state of a backtest run."""

from enum import Enum


class BacktestStatus(Enum):
    """Represents the execution status of a backtest run."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
