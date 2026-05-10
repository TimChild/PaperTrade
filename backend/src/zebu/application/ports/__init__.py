"""Repository ports (interfaces) for the application layer.

These ports define the contracts that adapters must implement for persistence.
They use typing.Protocol for structural typing, allowing duck-typed implementations.
"""

from zebu.application.ports.backtest_run_repository import BacktestRunRepository
from zebu.application.ports.exploration_task_repository import (
    ExplorationTaskRepository,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.strategy_repository import StrategyRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.application.ports.trigger_fire_repository import TriggerFireRepository
from zebu.application.ports.trigger_repository import TriggerRepository

__all__ = [
    "BacktestRunRepository",
    "ExplorationTaskRepository",
    "MarketDataPort",
    "PortfolioRepository",
    "StrategyRepository",
    "TransactionRepository",
    "TriggerFireRepository",
    "TriggerRepository",
]
