"""Repository interfaces (Ports) for domain entities."""

from papertrade.domain.repositories.portfolio_repository import PortfolioRepository
from papertrade.domain.repositories.transaction_repository import TransactionRepository

__all__ = ["PortfolioRepository", "TransactionRepository"]
