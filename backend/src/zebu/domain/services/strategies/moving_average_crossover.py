"""MovingAverageCrossoverStrategy - Trade based on SMA crossover signals."""

import logging
from datetime import date
from decimal import Decimal

from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal

logger = logging.getLogger(__name__)


class MovingAverageCrossoverStrategy:
    """Generate trade signals based on Simple Moving Average (SMA) crossovers.

    Emits a BUY signal (golden cross) when the fast SMA crosses above the slow
    SMA and no position is currently held. Emits a SELL signal (death cross)
    when the fast SMA crosses below the slow SMA and a position is held.

    Requires warm-up data of at least ``slow_window`` trading days before the
    simulation start date so that both SMAs can be computed on day 1.
    """

    def __init__(
        self,
        tickers: list[str],
        fast_window: int,
        slow_window: int,
        invest_fraction: float,
    ) -> None:
        """Initialize strategy parameters.

        Args:
            tickers: Symbols to monitor for crossover signals
            fast_window: Number of trading days for the short-term SMA (2–200)
            slow_window: Number of trading days for the long-term SMA (2–200,
                must be > fast_window)
            invest_fraction: Fraction of available cash to invest on a BUY signal
                (0 < value ≤ 1.0)
        """
        self._tickers = tickers
        self._fast_window = fast_window
        self._slow_window = slow_window
        self._invest_fraction = invest_fraction
        # Previous day's (fast_sma, slow_sma) per ticker for crossover detection
        self._prev_sma: dict[str, tuple[Decimal, Decimal] | None] = {
            t: None for t in tickers
        }

    def generate_signals(
        self,
        current_date: date,
        price_map: dict[str, dict[date, PricePoint]],
        cash_balance: Decimal,
        holdings: dict[str, Decimal],
    ) -> list[TradeSignal]:
        """Generate BUY/SELL signals based on SMA crossovers.

        Args:
            current_date: The trading day being simulated
            price_map: Pre-fetched price data keyed by ticker then date
            cash_balance: Current cash balance in USD
            holdings: Current holdings keyed by ticker symbol (shares)

        Returns:
            List of TradeSignals (BUY or SELL) or empty list if no crossover
        """
        signals: list[TradeSignal] = []

        for ticker in self._tickers:
            ticker_prices = price_map.get(ticker, {})

            fast_sma = self._compute_sma(ticker_prices, current_date, self._fast_window)
            slow_sma = self._compute_sma(ticker_prices, current_date, self._slow_window)

            if fast_sma is None or slow_sma is None:
                logger.debug(
                    "MovingAverageCrossover: insufficient data for %s on %s",
                    ticker,
                    current_date,
                )
                self._prev_sma[ticker] = None
                continue

            prev = self._prev_sma.get(ticker)

            if prev is not None:
                prev_fast, prev_slow = prev
                current_holding = holdings.get(ticker, Decimal("0"))
                has_position = current_holding > Decimal("0")

                # Golden cross: fast crosses above slow → BUY
                if prev_fast <= prev_slow and fast_sma > slow_sma and not has_position:
                    amount = cash_balance * Decimal(str(self._invest_fraction))
                    if amount > Decimal("0"):
                        signals.append(
                            TradeSignal(
                                action=TradeAction.BUY,
                                ticker=ticker,
                                signal_date=current_date,
                                amount=amount,
                            )
                        )
                        logger.debug(
                            "MovingAverageCrossover: BUY signal for %s on %s "
                            "(fast=%.4f, slow=%.4f)",
                            ticker,
                            current_date,
                            fast_sma,
                            slow_sma,
                        )

                # Death cross: fast crosses below slow → SELL
                elif prev_fast >= prev_slow and fast_sma < slow_sma and has_position:
                    signals.append(
                        TradeSignal(
                            action=TradeAction.SELL,
                            ticker=ticker,
                            signal_date=current_date,
                            quantity=current_holding,
                        )
                    )
                    logger.debug(
                        "MovingAverageCrossover: SELL signal for %s on %s "
                        "(fast=%.4f, slow=%.4f)",
                        ticker,
                        current_date,
                        fast_sma,
                        slow_sma,
                    )

            self._prev_sma[ticker] = (fast_sma, slow_sma)

        return signals

    def _compute_sma(
        self,
        price_map_for_ticker: dict[date, PricePoint],
        as_of_date: date,
        window: int,
    ) -> Decimal | None:
        """Compute a Simple Moving Average using the last ``window`` trading days.

        Looks backward from ``as_of_date`` (inclusive) using the actual dates
        available in ``price_map_for_ticker`` (trading days only — weekends and
        holidays are automatically excluded because they have no entries in the
        map).

        Args:
            price_map_for_ticker: Price data for a single ticker keyed by date
            as_of_date: The reference date (inclusive upper bound)
            window: Number of trading days to average

        Returns:
            Simple Moving Average as a Decimal, or None if there are fewer than
            ``window`` trading days available up to and including ``as_of_date``.
        """
        sorted_dates = sorted(d for d in price_map_for_ticker if d <= as_of_date)
        if len(sorted_dates) < window:
            return None

        last_n = sorted_dates[-window:]
        total = sum(
            (price_map_for_ticker[d].price.amount for d in last_n),
            Decimal("0"),
        )
        return total / Decimal(str(window))
