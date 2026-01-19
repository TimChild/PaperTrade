"""Unit tests for AlphaVantageAdapter weekend handling in get_current_price.

These tests verify that get_current_price() and get_batch_prices() correctly
handle weekends and holidays by serving cached prices from the last trading day.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zebu.adapters.outbound.market_data.alpha_vantage_adapter import (
    AlphaVantageAdapter,
)
from zebu.application.dtos.price_point import PricePoint
from zebu.application.exceptions import MarketDataUnavailableError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker


@pytest.fixture
def mock_rate_limiter() -> MagicMock:
    """Provide mock rate limiter."""
    limiter = MagicMock()
    limiter.can_make_request = AsyncMock(return_value=True)
    limiter.consume_token = AsyncMock(return_value=True)
    limiter.get_remaining_tokens = AsyncMock(
        return_value={"minute": 5, "day": 500}
    )
    return limiter


@pytest.fixture
def mock_price_repository() -> MagicMock:
    """Provide mock price repository."""
    return MagicMock()


@pytest.fixture
def mock_price_cache() -> MagicMock:
    """Provide mock price cache."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Provide mock HTTP client."""
    return MagicMock()


@pytest.fixture
def alpha_vantage_adapter(
    mock_rate_limiter: MagicMock,
    mock_price_repository: MagicMock,
    mock_price_cache: MagicMock,
    mock_http_client: MagicMock,
) -> AlphaVantageAdapter:
    """Provide configured Alpha Vantage adapter for testing."""
    return AlphaVantageAdapter(
        rate_limiter=mock_rate_limiter,
        price_repository=mock_price_repository,
        price_cache=mock_price_cache,
        http_client=mock_http_client,
        api_key="test_key",
    )


def create_price_point(
    ticker: Ticker, date: datetime, price: Decimal = Decimal("150.00")
) -> PricePoint:
    """Helper to create a price point for testing."""
    return PricePoint(
        ticker=ticker,
        timestamp=date,
        price=Money(price, "USD"),
        open=Money(price - Decimal("1.00"), "USD"),
        high=Money(price + Decimal("2.00"), "USD"),
        low=Money(price - Decimal("2.00"), "USD"),
        close=Money(price, "USD"),
        volume=1000000,
        source="alpha_vantage",
        interval="1day",
    )


class TestGetCurrentPriceWeekend:
    """Tests for get_current_price() weekend handling."""

    async def test_saturday_returns_friday_price(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return Friday's cached price when requesting on Saturday."""
        ticker = Ticker("AAPL")

        # Saturday, Jan 18, 2026, 10:00 AM
        mock_now = datetime(2026, 1, 18, 10, 0, 0, tzinfo=UTC)

        # Friday, Jan 17, 2026 at market close (21:00 UTC)
        friday_price = create_price_point(
            ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC), Decimal("259.96")
        )

        # Mock get_latest_price to return None (no fresh data in Tier 2)
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)

        # Mock get_price_at to return Friday's price
        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Act
            result = await alpha_vantage_adapter.get_current_price(ticker)

            # Assert
            assert result.price.amount == Decimal("259.96")
            assert result.source == "database"
            assert result.timestamp == friday_price.timestamp

            # Verify API was NOT called
            mock_rate_limiter.consume_token.assert_not_called()

            # Verify price was cached with longer TTL (2 hours = 7200 seconds)
            mock_price_cache.set.assert_called_once()
            call_args = mock_price_cache.set.call_args
            assert call_args[1]["ttl"] == 7200

    async def test_sunday_returns_friday_price(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return Friday's cached price when requesting on Sunday."""
        ticker = Ticker("AAPL")

        # Sunday, Jan 19, 2026, 10:00 AM
        mock_now = datetime(2026, 1, 19, 10, 0, 0, tzinfo=UTC)

        # Friday, Jan 17, 2026 at market close (21:00 UTC)
        friday_price = create_price_point(
            ticker, datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC), Decimal("259.96")
        )

        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Act
            result = await alpha_vantage_adapter.get_current_price(ticker)

            # Assert
            assert result.price.amount == Decimal("259.96")
            assert result.source == "database"

            # Verify API was NOT called
            mock_rate_limiter.consume_token.assert_not_called()

    async def test_holiday_returns_last_trading_day_price(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return last trading day's price on market holiday."""
        ticker = Ticker("AAPL")

        # Monday, Jan 20, 2025 (MLK Day - market holiday)
        mock_now = datetime(2025, 1, 20, 10, 0, 0, tzinfo=UTC)

        # Friday, Jan 17, 2025 at market close
        friday_price = create_price_point(
            ticker, datetime(2025, 1, 17, 21, 0, 0, tzinfo=UTC), Decimal("225.00")
        )

        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=friday_price)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Act
            result = await alpha_vantage_adapter.get_current_price(ticker)

            # Assert
            assert result.price.amount == Decimal("225.00")
            assert result.source == "database"

            # Verify API was NOT called
            mock_rate_limiter.consume_token.assert_not_called()

    async def test_weekend_no_cached_data_fetches_from_api(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should fetch from API when no cached data available on weekend."""
        ticker = Ticker("AAPL")

        # Sunday, Jan 19, 2026, 10:00 AM
        mock_now = datetime(2026, 1, 19, 10, 0, 0, tzinfo=UTC)

        # No cached data available
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.get_price_at = AsyncMock(return_value=None)
        mock_price_repository.upsert_price = AsyncMock()

        # Mock API response (Alpha Vantage returns Friday's close on weekends)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "259.96",
            }
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Act
            result = await alpha_vantage_adapter.get_current_price(ticker)

            # Assert - should fetch from API
            assert result.price.amount == Decimal("259.96")
            assert result.source == "alpha_vantage"

            # Verify API WAS called
            mock_rate_limiter.consume_token.assert_called_once()
            mock_http_client.get.assert_called_once()

    async def test_trading_day_fetches_from_api(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should fetch from API on trading day when no cached data."""
        ticker = Ticker("AAPL")

        # Monday, Jan 13, 2026, 10:00 AM (regular trading day)
        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        # No cached data
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.upsert_price = AsyncMock()

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "150.25",
            }
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Act
            result = await alpha_vantage_adapter.get_current_price(ticker)

            # Assert
            assert result.price.amount == Decimal("150.25")
            assert result.source == "alpha_vantage"

            # Verify API WAS called
            mock_rate_limiter.consume_token.assert_called_once()
            mock_http_client.get.assert_called_once()


class TestGetBatchPricesWeekend:
    """Tests for get_batch_prices() weekend handling."""

    async def test_saturday_returns_friday_prices_for_all_tickers(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
    ) -> None:
        """Should return Friday's cached prices for all tickers on Saturday."""
        tickers = [Ticker("AAPL"), Ticker("MSFT"), Ticker("GOOGL")]

        # Saturday, Jan 18, 2026, 10:00 AM
        mock_now = datetime(2026, 1, 18, 10, 0, 0, tzinfo=UTC)

        # Friday prices for all tickers
        friday_prices = {
            "AAPL": create_price_point(
                Ticker("AAPL"),
                datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC),
                Decimal("259.96"),
            ),
            "MSFT": create_price_point(
                Ticker("MSFT"),
                datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC),
                Decimal("425.50"),
            ),
            "GOOGL": create_price_point(
                Ticker("GOOGL"),
                datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC),
                Decimal("150.00"),
            ),
        }

        # Mock get_latest_price to return None (no fresh data in Tier 2)
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)

        # Mock get_price_at to return Friday's price for each ticker
        async def mock_get_price_at(ticker: Ticker, timestamp: datetime) -> PricePoint:
            return friday_prices[ticker.symbol]

        mock_price_repository.get_price_at = AsyncMock(side_effect=mock_get_price_at)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Act
            result = await alpha_vantage_adapter.get_batch_prices(tickers)

            # Assert
            assert len(result) == 3
            assert result[Ticker("AAPL")].price.amount == Decimal("259.96")
            assert result[Ticker("MSFT")].price.amount == Decimal("425.50")
            assert result[Ticker("GOOGL")].price.amount == Decimal("150.00")

            # All should have source="database"
            for price in result.values():
                assert price.source == "database"

            # Verify API was NOT called
            mock_rate_limiter.consume_token.assert_not_called()

    async def test_sunday_fetches_uncached_tickers_from_api(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should fetch from API for tickers without cached data on weekend."""
        tickers = [Ticker("AAPL"), Ticker("MSFT"), Ticker("TSLA")]

        # Sunday, Jan 19, 2026, 10:00 AM
        mock_now = datetime(2026, 1, 19, 10, 0, 0, tzinfo=UTC)

        # Friday prices only for AAPL and MSFT
        friday_aapl = create_price_point(
            Ticker("AAPL"),
            datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC),
            Decimal("259.96"),
        )
        friday_msft = create_price_point(
            Ticker("MSFT"),
            datetime(2026, 1, 17, 21, 0, 0, tzinfo=UTC),
            Decimal("425.50"),
        )

        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.upsert_price = AsyncMock()

        # Mock get_price_at to return None for TSLA ticker
        async def mock_get_price_at(
            ticker: Ticker, timestamp: datetime
        ) -> PricePoint | None:
            if ticker.symbol == "AAPL":
                return friday_aapl
            elif ticker.symbol == "MSFT":
                return friday_msft
            else:
                return None

        mock_price_repository.get_price_at = AsyncMock(side_effect=mock_get_price_at)

        # Mock API response for TSLA
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "TSLA",
                "05. price": "350.00",
            }
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Act
            result = await alpha_vantage_adapter.get_batch_prices(tickers)

            # Assert - should get all 3 tickers
            assert len(result) == 3
            assert Ticker("AAPL") in result
            assert Ticker("MSFT") in result
            assert Ticker("TSLA") in result

            # AAPL and MSFT from cache
            assert result[Ticker("AAPL")].source == "database"
            assert result[Ticker("MSFT")].source == "database"

            # TSLA from API
            assert result[Ticker("TSLA")].source == "alpha_vantage"
            assert result[Ticker("TSLA")].price.amount == Decimal("350.00")

            # Verify API WAS called (for TSLA)
            mock_rate_limiter.consume_token.assert_called_once()

    async def test_trading_day_fetches_from_api_for_uncached_tickers(
        self,
        alpha_vantage_adapter: AlphaVantageAdapter,
        mock_price_repository: MagicMock,
        mock_price_cache: MagicMock,
        mock_rate_limiter: MagicMock,
        mock_http_client: MagicMock,
    ) -> None:
        """Should fetch from API on trading day for uncached tickers."""
        tickers = [Ticker("AAPL")]

        # Monday, Jan 13, 2026, 10:00 AM (regular trading day)
        mock_now = datetime(2026, 1, 13, 10, 0, 0, tzinfo=UTC)

        # No cached data
        mock_price_repository.get_latest_price = AsyncMock(return_value=None)
        mock_price_repository.upsert_price = AsyncMock()

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "150.25",
            }
        }
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "zebu.adapters.outbound.market_data.alpha_vantage_adapter.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Act
            result = await alpha_vantage_adapter.get_batch_prices(tickers)

            # Assert
            assert len(result) == 1
            assert result[Ticker("AAPL")].price.amount == Decimal("150.25")
            assert result[Ticker("AAPL")].source == "alpha_vantage"

            # Verify API WAS called
            mock_rate_limiter.consume_token.assert_called_once()
            mock_http_client.get.assert_called_once()
