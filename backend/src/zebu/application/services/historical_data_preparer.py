"""HistoricalDataPreparer - Pre-fetches historical price data for backtesting."""

import logging
from datetime import UTC, date, datetime, timedelta

from zebu.application.dtos.price_point import PricePoint
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.domain.exceptions import InsufficientHistoricalDataError
from zebu.domain.value_objects.ticker import Ticker

logger = logging.getLogger(__name__)

# Type alias for the price map returned by this service
PriceMap = dict[str, dict[date, PricePoint]]


class HistoricalDataPreparer:
    """Pre-fetches and validates historical price data for backtesting.

    Fetches all required price history before the simulation loop begins,
    so the executor can run without async calls during iteration.
    """

    def __init__(self, market_data: MarketDataPort) -> None:
        """Initialize with a market data port.

        Args:
            market_data: Market data adapter for fetching price history
        """
        self._market_data = market_data

    async def prepare(
        self,
        tickers: list[str],
        start_date: date,
        end_date: date,
        warm_up_days: int = 0,
    ) -> PriceMap:
        """Fetch price history for all tickers covering the full date range.

        Args:
            tickers: Stock symbols to fetch
            start_date: First day of simulation
            end_date: Last day of simulation
            warm_up_days: Extra calendar days before start_date for indicators

        Returns:
            PriceMap: dict mapping ticker -> date -> PricePoint

        Raises:
            InsufficientHistoricalDataError: If any ticker returns no data
        """
        effective_start = start_date - timedelta(days=warm_up_days)

        start_dt = datetime(
            effective_start.year,
            effective_start.month,
            effective_start.day,
            0,
            0,
            0,
            tzinfo=UTC,
        )
        end_dt = datetime(
            end_date.year,
            end_date.month,
            end_date.day,
            23,
            59,
            59,
            tzinfo=UTC,
        )

        price_map: PriceMap = {}

        for ticker_str in tickers:
            ticker = Ticker(ticker_str)
            logger.debug(
                f"Fetching price history for {ticker_str} "
                f"from {effective_start} to {end_date}"
            )
            price_points = await self._market_data.get_price_history(
                ticker, start_dt, end_dt, interval="1day"
            )

            if not price_points:
                raise InsufficientHistoricalDataError(
                    ticker=ticker_str,
                    message=(
                        f"No historical price data available for {ticker_str} "
                        f"between {effective_start} and {end_date}"
                    ),
                )

            price_map[ticker_str] = {pp.timestamp.date(): pp for pp in price_points}
            logger.debug(
                f"Loaded {len(price_map[ticker_str])} price points for {ticker_str}"
            )

        return price_map
