"""Tests for batch price fetching functionality."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.dtos.price_point import PricePoint
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker


@pytest.fixture
def market_data():
    """Provide in-memory market data adapter."""
    return InMemoryMarketDataAdapter()


class TestBatchPrices:
    """Tests for batch price fetching."""

    async def test_batch_prices_returns_all_seeded_tickers(self, market_data):
        """Test batch fetch returns all requested tickers when available."""
        # Arrange - Seed prices for AAPL, GOOGL, MSFT
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("175.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("GOOGL"),
                price=Money(Decimal("140.50"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("MSFT"),
                price=Money(Decimal("380.25"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )

        tickers = [Ticker("AAPL"), Ticker("GOOGL"), Ticker("MSFT")]

        # Act
        result = await market_data.get_batch_prices(tickers)

        # Assert
        assert len(result) == 3
        assert Ticker("AAPL") in result
        assert Ticker("GOOGL") in result
        assert Ticker("MSFT") in result
        assert result[Ticker("AAPL")].price.amount == Decimal("175.00")
        assert result[Ticker("GOOGL")].price.amount == Decimal("140.50")
        assert result[Ticker("MSFT")].price.amount == Decimal("380.25")

    async def test_batch_prices_partial_results_when_some_missing(self, market_data):
        """Test batch fetch returns only available tickers."""
        # Arrange - Only seed AAPL, not GOOGL
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("175.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )

        tickers = [Ticker("AAPL"), Ticker("GOOGL")]

        # Act
        result = await market_data.get_batch_prices(tickers)

        # Assert - Only AAPL should be in result
        assert len(result) == 1
        assert Ticker("AAPL") in result
        assert Ticker("GOOGL") not in result

    async def test_batch_prices_empty_list_returns_empty_dict(self, market_data):
        """Test batch fetch with empty list returns empty dict."""
        # Arrange
        tickers: list[Ticker] = []

        # Act
        result = await market_data.get_batch_prices(tickers)

        # Assert
        assert len(result) == 0
        assert result == {}

    async def test_batch_prices_all_missing_returns_empty_dict(self, market_data):
        """Test batch fetch when all tickers are missing."""
        # Arrange - Don't seed any data
        tickers = [Ticker("AAPL"), Ticker("GOOGL"), Ticker("MSFT")]

        # Act
        result = await market_data.get_batch_prices(tickers)

        # Assert
        assert len(result) == 0
        assert result == {}

    async def test_batch_prices_single_ticker(self, market_data):
        """Test batch fetch works with single ticker."""
        # Arrange
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("175.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )

        tickers = [Ticker("AAPL")]

        # Act
        result = await market_data.get_batch_prices(tickers)

        # Assert
        assert len(result) == 1
        assert Ticker("AAPL") in result
        assert result[Ticker("AAPL")].price.amount == Decimal("175.00")

    async def test_batch_prices_duplicate_tickers(self, market_data):
        """Test batch fetch with duplicate tickers."""
        # Arrange
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("175.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )

        # Request AAPL twice
        tickers = [Ticker("AAPL"), Ticker("AAPL")]

        # Act
        result = await market_data.get_batch_prices(tickers)

        # Assert - Should still return only one entry
        assert len(result) == 1
        assert Ticker("AAPL") in result
