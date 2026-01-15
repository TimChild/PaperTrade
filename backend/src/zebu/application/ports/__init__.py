"""Repository ports (interfaces) for the application layer.

These ports define the contracts that adapters must implement for persistence.
They use typing.Protocol for structural typing, allowing duck-typed implementations.
"""

from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.transaction_repository import TransactionRepository

__all__ = ["MarketDataPort", "PortfolioRepository", "TransactionRepository"]
