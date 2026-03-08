"""BuyAndHoldStrategy - Buy on day 1, hold forever."""

import logging
from datetime import date
from decimal import Decimal

from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal

logger = logging.getLogger(__name__)


class BuyAndHoldStrategy:
    """Buy proportionally on day 1 of the backtest, hold forever.

    On the first trading day, allocates cash across tickers according to
    the configured allocation fractions (must sum to ~1.0). On all subsequent
    days, no signals are generated.
    """

    def __init__(
        self,
        tickers: list[str],
        allocation: dict[str, float],
    ) -> None:
        """Initialize strategy with tickers and allocation fractions.

        Args:
            tickers: Symbols to trade on day 1
            allocation: Fraction of cash per ticker (should sum to ~1.0)
        """
        self._tickers = tickers
        self._allocation = allocation
        self._has_bought = False

    def generate_signals(
        self,
        current_date: date,
        price_map: dict[str, dict[date, PricePoint]],
        cash_balance: Decimal,
        holdings: dict[str, Decimal],
    ) -> list[TradeSignal]:
        """Generate BUY signals on the first call; empty list thereafter.

        Args:
            current_date: The trading day being simulated
            price_map: Pre-fetched price data (not used by this strategy)
            cash_balance: Current cash balance in USD
            holdings: Current holdings (not used after first purchase)

        Returns:
            List of BUY TradeSignals on first call, empty list on subsequent calls
        """
        if self._has_bought:
            return []

        signals: list[TradeSignal] = []

        for ticker in self._tickers:
            fraction = self._allocation.get(ticker, 0.0)
            if fraction <= 0.0:
                continue

            amount = cash_balance * Decimal(str(fraction))
            if amount <= Decimal("0"):
                continue

            signals.append(
                TradeSignal(
                    action=TradeAction.BUY,
                    ticker=ticker,
                    signal_date=current_date,
                    amount=amount,
                )
            )

        if signals:
            self._has_bought = True
            logger.debug(
                f"BuyAndHold: generated {len(signals)} BUY signals on {current_date}"
            )

        return signals
