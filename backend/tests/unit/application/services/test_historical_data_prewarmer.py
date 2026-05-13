"""Tests for :class:`HistoricalDataPrewarmer`.

Phase J (Task #212 Layer 2) — behavior-focused: we mock only at the
:class:`MarketDataPort` boundary. The task queue uses the real in-memory
adapter so we can assert task transitions end-to-end.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.ports.in_memory_backfill_task_repository import (
    InMemoryBackfillTaskRepository,
)
from zebu.application.services.historical_data_prewarmer import (
    HistoricalDataPrewarmer,
)
from zebu.domain.entities.backfill_task import BackfillTask
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.ticker import Ticker

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _CountingAdapter:
    """Wraps :class:`InMemoryMarketDataAdapter` and records calls.

    Behavior-focused: we instantiate the real in-memory port and observe
    its call pattern rather than overriding internals.
    """

    def __init__(self, underlying: InMemoryMarketDataAdapter) -> None:
        self._underlying = underlying
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        self.calls.append((ticker.symbol, start, end))
        return await self._underlying.get_price_history(ticker, start, end, interval)

    # Pass-through; not used in these tests but required to satisfy the Protocol.
    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        return await self._underlying.get_current_price(ticker)

    async def get_batch_prices(self, tickers: list[Ticker]) -> dict[Ticker, PricePoint]:
        return await self._underlying.get_batch_prices(tickers)

    async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> PricePoint:
        return await self._underlying.get_price_at(ticker, timestamp)

    async def get_supported_tickers(self) -> list[Ticker]:
        return await self._underlying.get_supported_tickers()


def _make_adapter(*tickers: str) -> InMemoryMarketDataAdapter:
    """In-memory adapter seeded with one PricePoint per ticker.

    The prewarmer's success path only requires ``get_price_history`` to
    return *something* (it doesn't inspect the bars). One row per ticker
    keeps the test setup minimal.
    """
    adapter = InMemoryMarketDataAdapter()
    seed_dt = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)
    for symbol in tickers:
        adapter.seed_price(
            PricePoint(
                ticker=Ticker(symbol),
                price=Money(Decimal("100"), "USD"),
                timestamp=seed_dt,
                source="database",
                interval="1day",
            )
        )
    return adapter


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def start_date() -> date:
    return date(2024, 1, 1)


@pytest.fixture
def end_date() -> date:
    return date(2024, 1, 31)


@pytest.fixture
def repository() -> InMemoryBackfillTaskRepository:
    return InMemoryBackfillTaskRepository()


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestPrewarmSuccess:
    """Happy path: every ticker fetches cleanly."""

    async def test_succeeded_tickers_are_reported(
        self,
        start_date: date,
        end_date: date,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        adapter = _make_adapter("AAPL", "MSFT")
        prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repository)

        result = await prewarmer.prewarm(
            [Ticker("AAPL"), Ticker("MSFT")],
            start_date,
            end_date,
            priority=BackfillPriority.LOW,
        )

        succeeded_symbols = sorted(t.symbol for t in result.succeeded)
        assert succeeded_symbols == ["AAPL", "MSFT"]
        assert result.failed == []
        assert result.skipped == []

    async def test_succeeded_tasks_persist_as_succeeded(
        self,
        start_date: date,
        end_date: date,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        adapter = _make_adapter("AAPL")
        prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repository)
        await prewarmer.prewarm(
            [Ticker("AAPL")],
            start_date,
            end_date,
            priority=BackfillPriority.HIGH,
        )

        # Find the AAPL task — there is one
        found = await repository.find_existing(
            Ticker("AAPL"),
            start_date,
            end_date,
            status_in=[BackfillTaskStatus.SUCCEEDED],
        )
        assert found is not None
        assert found.status is BackfillTaskStatus.SUCCEEDED
        assert found.priority is BackfillPriority.HIGH

    async def test_market_data_called_with_utc_window(
        self,
        start_date: date,
        end_date: date,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        underlying = _make_adapter("AAPL")
        counter = _CountingAdapter(underlying)
        prewarmer = HistoricalDataPrewarmer(market_data=counter, repository=repository)
        await prewarmer.prewarm(
            [Ticker("AAPL")],
            start_date,
            end_date,
            priority=BackfillPriority.LOW,
        )

        assert len(counter.calls) == 1
        symbol, fetch_start, fetch_end = counter.calls[0]
        assert symbol == "AAPL"
        # start is 00:00:00 UTC, end is 23:59:59 UTC, both tz-aware.
        assert fetch_start.tzinfo is UTC
        assert fetch_end.tzinfo is UTC
        assert fetch_start.date() == start_date
        assert fetch_end.date() == end_date


# ---------------------------------------------------------------------------
# Partial failure
# ---------------------------------------------------------------------------


class TestPrewarmPartialFailure:
    """One ticker fails; the rest still complete successfully."""

    async def test_failed_ticker_does_not_abort_batch(
        self,
        start_date: date,
        end_date: date,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        # MSFT is seeded; AAPL is intentionally missing so the in-memory
        # adapter raises TickerNotFoundError when the prewarmer fetches.
        adapter = _make_adapter("MSFT")
        prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repository)

        result = await prewarmer.prewarm(
            [Ticker("AAPL"), Ticker("MSFT")],
            start_date,
            end_date,
            priority=BackfillPriority.LOW,
        )

        assert [t.symbol for t in result.succeeded] == ["MSFT"]
        assert [t.symbol for t, _ in result.failed] == ["AAPL"]
        # The failure message preserves the underlying error class info.
        failed_msg = result.failed[0][1]
        assert "AAPL" in failed_msg or "ticker" in failed_msg.lower()

    async def test_failed_ticker_persists_as_failed(
        self,
        start_date: date,
        end_date: date,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        adapter = _make_adapter("MSFT")
        prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repository)
        await prewarmer.prewarm(
            [Ticker("AAPL")],
            start_date,
            end_date,
            priority=BackfillPriority.LOW,
        )

        failed = await repository.find_existing(
            Ticker("AAPL"),
            start_date,
            end_date,
            status_in=[BackfillTaskStatus.FAILED],
        )
        assert failed is not None
        assert failed.error_message is not None
        assert failed.error_message.strip() != ""


# ---------------------------------------------------------------------------
# Skip when already-pending
# ---------------------------------------------------------------------------


class TestPrewarmSkip:
    """Idempotency: an existing PENDING/RUNNING task short-circuits the call."""

    async def test_skips_when_pending_task_exists(
        self,
        start_date: date,
        end_date: date,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        # Seed a PENDING row for the same range; the prewarmer should skip.
        from uuid import uuid4

        existing = BackfillTask(
            id=uuid4(),
            ticker=Ticker("AAPL"),
            start_date=start_date,
            end_date=end_date,
            priority=BackfillPriority.LOW,
            status=BackfillTaskStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        await repository.create(existing)

        underlying = _make_adapter("AAPL")
        counter = _CountingAdapter(underlying)
        prewarmer = HistoricalDataPrewarmer(market_data=counter, repository=repository)
        result = await prewarmer.prewarm(
            [Ticker("AAPL")],
            start_date,
            end_date,
            priority=BackfillPriority.LOW,
        )

        assert [t.symbol for t in result.skipped] == ["AAPL"]
        assert result.succeeded == []
        # The market-data adapter should NOT have been called.
        assert counter.calls == []

    async def test_does_not_skip_terminal_succeeded_task(
        self,
        start_date: date,
        end_date: date,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        """A previously-SUCCEEDED task for the same range does NOT cause a skip.

        The activation path always pre-warms — a SUCCEEDED task means we
        already have the data cached; but the prewarmer's idempotency
        only filters non-terminal rows. A re-prewarm produces a fresh
        SUCCEEDED row because the underlying market data is cached
        downstream of the prewarmer.
        """
        from uuid import uuid4

        finished_at = datetime.now(UTC)
        already = BackfillTask(
            id=uuid4(),
            ticker=Ticker("AAPL"),
            start_date=start_date,
            end_date=end_date,
            priority=BackfillPriority.LOW,
            status=BackfillTaskStatus.SUCCEEDED,
            created_at=finished_at,
            finished_at=finished_at,
        )
        await repository.create(already)

        adapter = _make_adapter("AAPL")
        prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repository)
        result = await prewarmer.prewarm(
            [Ticker("AAPL")],
            start_date,
            end_date,
            priority=BackfillPriority.LOW,
        )
        assert [t.symbol for t in result.succeeded] == ["AAPL"]


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestPrewarmDeduplication:
    """Duplicate tickers in the input are processed once."""

    async def test_duplicate_tickers_processed_once(
        self,
        start_date: date,
        end_date: date,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        adapter = _make_adapter("AAPL")
        prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repository)
        result = await prewarmer.prewarm(
            [Ticker("AAPL"), Ticker("AAPL"), Ticker("AAPL")],
            start_date,
            end_date,
            priority=BackfillPriority.LOW,
        )
        assert [t.symbol for t in result.succeeded] == ["AAPL"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestPrewarmValidation:
    async def test_end_before_start_rejected(
        self,
        repository: InMemoryBackfillTaskRepository,
    ) -> None:
        adapter = _make_adapter()
        prewarmer = HistoricalDataPrewarmer(market_data=adapter, repository=repository)
        with pytest.raises(ValueError, match="must be >= start_date"):
            await prewarmer.prewarm(
                [Ticker("AAPL")],
                date(2024, 1, 31),
                date(2024, 1, 1),
                priority=BackfillPriority.LOW,
            )
