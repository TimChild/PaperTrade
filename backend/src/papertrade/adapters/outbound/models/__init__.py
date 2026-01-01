"""SQLModel models for market data persistence."""

from papertrade.adapters.outbound.models.price_history import PriceHistoryModel
from papertrade.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel

__all__ = ["PriceHistoryModel", "TickerWatchlistModel"]
