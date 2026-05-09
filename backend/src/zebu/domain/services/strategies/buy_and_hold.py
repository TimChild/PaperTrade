"""BuyAndHoldStrategy - Buy on day 1, hold forever."""

import logging
from datetime import date
from decimal import Decimal

from zebu.domain.value_objects.allocation import Allocation
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal

logger = logging.getLogger(__name__)


class BuyAndHoldStrategy:
    """Buy proportionally on day 1 of the backtest, hold forever.

    On the first trading day, allocates cash across tickers according to
    the configured ``Allocation``. On all subsequent days, no signals are
    generated.
    """

    def __init__(
        self,
        tickers: list[str],
        allocation: Allocation,
    ) -> None:
        """Initialize strategy with tickers and allocation.

        Args:
            tickers: Symbols to trade on day 1
            allocation: Validated Allocation describing per-ticker fractions
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

        for ticker_str in self._tickers:
            ticker = Ticker(ticker_str)
            fraction = self._allocation.fraction_for(ticker)
            if fraction <= Decimal("0"):
                continue

            amount_decimal = (cash_balance * fraction).quantize(Decimal("0.01"))
            if amount_decimal <= Decimal("0"):
                continue

            signals.append(
                TradeSignal(
                    action=TradeAction.BUY,
                    ticker=ticker,
                    signal_date=current_date,
                    amount=Money(amount_decimal, "USD"),
                )
            )

        if signals:
            self._has_bought = True
            logger.debug(
                f"BuyAndHold: generated {len(signals)} BUY signals on {current_date}"
            )

        return signals
