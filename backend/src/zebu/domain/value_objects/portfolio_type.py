"""PortfolioType value object - discriminates paper trading from backtest portfolios."""

from enum import Enum


class PortfolioType(Enum):
    """Represents the type of a portfolio."""

    PAPER_TRADING = "PAPER_TRADING"
    BACKTEST = "BACKTEST"
