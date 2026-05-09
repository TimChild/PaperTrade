"""Unit tests for DeterministicMockMarketDataAdapter.

Verifies the contract documented in the adapter docstring:

- Returns deterministic prices for any valid ticker (no seeding required)
- Same symbol always maps to the same price
- Different symbols map to different prices
- Prices stay within the [20.00, 499.99] band so common test
  insufficient-funds and "buy 20 shares" scenarios stay valid
- Satisfies the MarketDataPort surface (every method behaves)
- get_price_history reflects daily-cadence behaviour over a range
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from zebu.adapters.outbound.market_data.deterministic_mock_adapter import (
    DeterministicMockMarketDataAdapter,
)
from zebu.domain.value_objects.ticker import Ticker


@pytest.fixture
def adapter() -> DeterministicMockMarketDataAdapter:
    """Provide a fresh adapter for each test."""
    return DeterministicMockMarketDataAdapter()


class TestGetCurrentPrice:
    """get_current_price returns deterministic prices for any valid ticker."""

    @pytest.mark.asyncio
    async def test_returns_price_for_unseeded_ticker(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        """The mock adapter does not require seeding — any valid ticker works."""
        price_point = await adapter.get_current_price(Ticker("ZZZZZ"))
        assert price_point.ticker.symbol == "ZZZZZ"
        assert price_point.price.currency == "USD"

    @pytest.mark.asyncio
    async def test_price_is_deterministic(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        """Two consecutive calls for the same ticker return the same amount."""
        first = await adapter.get_current_price(Ticker("AAPL"))
        second = await adapter.get_current_price(Ticker("AAPL"))
        assert first.price.amount == second.price.amount

    @pytest.mark.asyncio
    async def test_different_tickers_different_prices(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        """A spread of tickers yields a spread of prices (no global constant)."""
        symbols = ("AAPL", "GOOGL", "MSFT", "IBM", "TSLA")
        prices = {
            sym: (await adapter.get_current_price(Ticker(sym))).price.amount
            for sym in symbols
        }
        # At minimum, we want more than one distinct price.
        assert len({p for p in prices.values()}) > 1

    @pytest.mark.asyncio
    async def test_price_within_expected_band(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        """Prices always fall in the [20.00, 499.99] USD band."""
        for symbol in ("AAPL", "GOOGL", "MSFT", "IBM", "TSLA", "AMZN", "NVDA"):
            price_point = await adapter.get_current_price(Ticker(symbol))
            assert Decimal("20.00") <= price_point.price.amount <= Decimal("499.99")
            # 1000 shares of any ticker must exceed a $1,000 portfolio's cash
            # to keep the insufficient-funds E2E test valid.
            assert price_point.price.amount * 1000 > Decimal("1000")
            # 20 shares must fit in a $30,000 portfolio with room to spare.
            assert price_point.price.amount * 20 < Decimal("30000")

    @pytest.mark.asyncio
    async def test_price_has_two_decimal_places(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        """Money requires <=2 decimal places; the adapter must comply."""
        price_point = await adapter.get_current_price(Ticker("AAPL"))
        # exponent of 0.01 is -2; deeper (-3, -4) would be 3+ decimal places.
        assert price_point.price.amount.as_tuple().exponent >= -2

    @pytest.mark.asyncio
    async def test_timestamp_is_utc_aware(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        """Timestamps are timezone-aware UTC, as PricePoint requires."""
        price_point = await adapter.get_current_price(Ticker("AAPL"))
        assert price_point.timestamp.tzinfo is UTC


class TestGetBatchPrices:
    """get_batch_prices returns one entry per requested ticker."""

    @pytest.mark.asyncio
    async def test_returns_entry_for_every_ticker(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        tickers = [Ticker("AAPL"), Ticker("MSFT"), Ticker("GOOGL")]
        result = await adapter.get_batch_prices(tickers)
        assert set(result.keys()) == set(tickers)

    @pytest.mark.asyncio
    async def test_batch_matches_single_lookup(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        """Batch result and single-lookup result agree on price for each ticker."""
        ticker = Ticker("MSFT")
        single = await adapter.get_current_price(ticker)
        batch = await adapter.get_batch_prices([ticker])
        assert batch[ticker].price.amount == single.price.amount

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_dict(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        result = await adapter.get_batch_prices([])
        assert result == {}


class TestGetPriceAt:
    """get_price_at honours the requested timestamp and rejects naive ones."""

    @pytest.mark.asyncio
    async def test_returns_deterministic_price_at_timestamp(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        when = datetime(2025, 6, 15, 14, 0, tzinfo=UTC)
        price_point = await adapter.get_price_at(Ticker("AAPL"), when)
        assert price_point.timestamp == when
        # Same symbol should still produce the same price as get_current_price.
        current = await adapter.get_current_price(Ticker("AAPL"))
        assert price_point.price.amount == current.price.amount

    @pytest.mark.asyncio
    async def test_naive_timestamp_raises_value_error(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        naive = datetime(2025, 6, 15, 14, 0)  # no tzinfo
        with pytest.raises(ValueError, match="timezone-aware"):
            await adapter.get_price_at(Ticker("AAPL"), naive)


class TestGetPriceHistory:
    """get_price_history returns daily-cadence deterministic prices."""

    @pytest.mark.asyncio
    async def test_inclusive_start_and_end(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 5, tzinfo=UTC)
        history = await adapter.get_price_history(Ticker("AAPL"), start, end)
        # 1, 2, 3, 4, 5 → 5 points
        assert len(history) == 5
        assert history[0].timestamp == start
        assert history[-1].timestamp == end

    @pytest.mark.asyncio
    async def test_all_history_points_share_deterministic_price(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 3, tzinfo=UTC)
        history = await adapter.get_price_history(Ticker("AAPL"), start, end)
        amounts = {p.price.amount for p in history}
        assert len(amounts) == 1

    @pytest.mark.asyncio
    async def test_end_before_start_raises_value_error(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        start = datetime(2025, 1, 5, tzinfo=UTC)
        end = datetime(2025, 1, 1, tzinfo=UTC)
        with pytest.raises(ValueError, match="must not be before start"):
            await adapter.get_price_history(Ticker("AAPL"), start, end)

    @pytest.mark.asyncio
    async def test_non_daily_interval_returns_empty(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        """The mock keeps higher-frequency intervals out of scope deliberately."""
        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 1, 12, tzinfo=UTC)
        history = await adapter.get_price_history(
            Ticker("AAPL"), start, end, interval="1hour"
        )
        assert history == []


class TestGetSupportedTickers:
    """get_supported_tickers returns the constructor-supplied allowlist."""

    @pytest.mark.asyncio
    async def test_default_includes_common_symbols(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        tickers = await adapter.get_supported_tickers()
        symbols = {t.symbol for t in tickers}
        # IBM stays in the list to keep the historical hardcoded E2E paths
        # working, alongside common substitutes.
        assert {"AAPL", "GOOGL", "IBM", "MSFT", "TSLA"}.issubset(symbols)

    @pytest.mark.asyncio
    async def test_respects_custom_supported_list(self) -> None:
        adapter = DeterministicMockMarketDataAdapter(supported_tickers=("AAPL", "TSLA"))
        symbols = {t.symbol for t in await adapter.get_supported_tickers()}
        assert symbols == {"AAPL", "TSLA"}


class TestSeedTimestampSemantics:
    """Sanity check: timestamp on get_current_price is strictly in the past.

    This matters because consumers (the price repository, and as_of-priced
    trades) often query for "now" using >= semantics; a price stamped exactly
    at now() can trip flaky comparisons. The adapter timestamps 1 minute back
    to keep that path clean.
    """

    @pytest.mark.asyncio
    async def test_current_price_timestamp_is_in_past(
        self, adapter: DeterministicMockMarketDataAdapter
    ) -> None:
        before = datetime.now(UTC)
        price_point = await adapter.get_current_price(Ticker("AAPL"))
        # Up to 1 minute back, with a 2-second buffer for slow CI.
        assert price_point.timestamp <= before
        assert price_point.timestamp >= before - timedelta(seconds=62)
