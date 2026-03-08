"""TradingStrategy protocol - contract for all strategy implementations."""

from datetime import date
from decimal import Decimal
from typing import Protocol

from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.trade_signal import TradeSignal


class TradingStrategy(Protocol):
    """Protocol that all trading strategy implementations must satisfy.

    Strategies generate trade signals for a given trading day based on
    the current price data and portfolio state.
    """

    def generate_signals(
        self,
        current_date: date,
        price_map: dict[str, dict[date, PricePoint]],
        cash_balance: Decimal,
        holdings: dict[str, Decimal],
    ) -> list[TradeSignal]:
        """Generate trade signals for a given date.

        Args:
            current_date: The trading day being simulated
            price_map: Pre-fetched price data keyed by ticker then date
            cash_balance: Current cash balance in USD
            holdings: Current holdings keyed by ticker symbol, values are shares

        Returns:
            List of trade signals to execute. May be empty.
        """
        ...
