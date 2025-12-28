"""Data Transfer Objects (DTOs) for the application layer.

DTOs are immutable data containers used to transfer data across layer boundaries.
They decouple the API from the domain model and provide serialization-friendly formats.
"""

from papertrade.application.dtos.holding_dto import HoldingDTO
from papertrade.application.dtos.portfolio_dto import PortfolioDTO
from papertrade.application.dtos.transaction_dto import TransactionDTO

__all__ = ["HoldingDTO", "PortfolioDTO", "TransactionDTO"]
