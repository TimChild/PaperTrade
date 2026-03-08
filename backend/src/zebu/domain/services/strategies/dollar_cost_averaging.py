"""DollarCostAveragingStrategy - Invest a fixed amount at regular intervals."""

import logging
from datetime import date
from decimal import Decimal

from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal

logger = logging.getLogger(__name__)


class DollarCostAveragingStrategy:
    """Invest a fixed dollar amount at regular intervals across tickers.

    On the first trading day and every ``frequency_days`` thereafter, allocates
    ``amount_per_period`` across tickers according to the configured allocation
    fractions (which must sum to ~1.0). On all other days, no signals are
    generated.
    """

    def __init__(
        self,
        tickers: list[str],
        frequency_days: int,
        amount_per_period: Decimal,
        allocation: dict[str, float],
    ) -> None:
        """Initialize strategy with tickers, frequency, amount, and allocation.

        Args:
            tickers: Symbols to invest in on each purchase date
            frequency_days: Number of days between purchases (1–365)
            amount_per_period: Total USD amount to invest per period
            allocation: Fraction of amount_per_period per ticker (should sum to ~1.0)
        """
        self._tickers = tickers
        self._frequency_days = frequency_days
        self._amount_per_period = amount_per_period
        self._allocation = allocation
        self._last_purchase_date: date | None = None

    def generate_signals(
        self,
        current_date: date,
        price_map: dict[str, dict[date, PricePoint]],
        cash_balance: Decimal,
        holdings: dict[str, Decimal],
    ) -> list[TradeSignal]:
        """Generate BUY signals when the purchase interval has elapsed.

        On the first call (or when ``frequency_days`` have elapsed since the
        last purchase), emits one BUY signal per ticker using an amount-based
        signal (``amount = amount_per_period * allocation[ticker]``).

        Args:
            current_date: The trading day being simulated
            price_map: Pre-fetched price data (not used by this strategy)
            cash_balance: Current cash balance in USD (not used; executor skips
                signals that exceed available cash)
            holdings: Current holdings (not used by this strategy)

        Returns:
            List of BUY TradeSignals or empty list if not a purchase day
        """
        # Determine whether to purchase today
        if self._last_purchase_date is None:
            should_purchase = True
        else:
            days_elapsed = (current_date - self._last_purchase_date).days
            should_purchase = days_elapsed >= self._frequency_days

        if not should_purchase:
            return []

        signals: list[TradeSignal] = []
        for ticker in self._tickers:
            fraction = self._allocation.get(ticker, 0.0)
            if fraction <= 0.0:
                continue
            amount = self._amount_per_period * Decimal(str(fraction))
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
            self._last_purchase_date = current_date
            logger.debug(
                "DollarCostAveraging: generated %d BUY signals on %s",
                len(signals),
                current_date,
            )

        return signals
