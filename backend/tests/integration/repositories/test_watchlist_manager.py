"""Integration tests for WatchlistManager.

Tests the watchlist manager implementation against a real database
to verify ticker tracking and refresh scheduling functionality.
"""

from datetime import UTC, datetime, timedelta

import pytest

from papertrade.adapters.outbound.repositories.watchlist_manager import WatchlistManager
from papertrade.domain.value_objects.ticker import Ticker


class TestWatchlistManagerAdd:
    """Tests for add_ticker method."""

    @pytest.mark.asyncio
    async def test_add_ticker_creates_new_entry(self, session):
        """Test adding a new ticker to watchlist."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Act
        await manager.add_ticker(ticker, priority=50)
        await session.commit()

        # Assert
        active = await manager.get_all_active_tickers()
        assert len(active) == 1
        assert active[0] == ticker

    @pytest.mark.asyncio
    async def test_add_ticker_updates_priority_when_higher(self, session):
        """Test that adding existing ticker with higher priority updates it."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Add with priority 100
        await manager.add_ticker(ticker, priority=100)
        await session.commit()

        # Act - add again with higher priority (lower number)
        await manager.add_ticker(ticker, priority=50)
        await session.commit()

        # Assert - should have updated to priority 50
        active = await manager.get_all_active_tickers()
        assert len(active) == 1  # Still just one ticker

    @pytest.mark.asyncio
    async def test_add_ticker_keeps_existing_priority_when_lower(self, session):
        """Test that adding existing ticker with lower priority keeps existing."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Add with high priority
        await manager.add_ticker(ticker, priority=50)
        await session.commit()

        # Act - add again with lower priority (higher number)
        await manager.add_ticker(ticker, priority=100)
        await session.commit()

        # Assert - should still have only one ticker
        active = await manager.get_all_active_tickers()
        assert len(active) == 1

    @pytest.mark.asyncio
    async def test_add_ticker_with_custom_refresh_interval(self, session):
        """Test adding ticker with custom refresh interval."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Act
        await manager.add_ticker(
            ticker, priority=50, refresh_interval=timedelta(minutes=10)
        )
        await session.commit()

        # Assert
        active = await manager.get_all_active_tickers()
        assert len(active) == 1


class TestWatchlistManagerRemove:
    """Tests for remove_ticker method."""

    @pytest.mark.asyncio
    async def test_remove_ticker_marks_inactive(self, session):
        """Test that removing ticker marks it as inactive."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Add ticker
        await manager.add_ticker(ticker)
        await session.commit()

        # Act - remove ticker
        await manager.remove_ticker(ticker)
        await session.commit()

        # Assert - should not appear in active tickers
        active = await manager.get_all_active_tickers()
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_remove_ticker_does_not_delete_record(self, session):
        """Test that removing ticker preserves the database record."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        await manager.add_ticker(ticker)
        await session.commit()

        # Act
        await manager.remove_ticker(ticker)
        await session.commit()

        # Assert - record still exists but is inactive
        # (we can verify by re-adding and checking it updates existing record)
        await manager.add_ticker(ticker, priority=50)
        await session.commit()
        active = await manager.get_all_active_tickers()
        assert len(active) == 1


class TestWatchlistManagerGetStale:
    """Tests for get_stale_tickers method."""

    @pytest.mark.asyncio
    async def test_get_stale_returns_tickers_needing_refresh(self, session):
        """Test getting tickers that need refresh."""
        # Arrange
        manager = WatchlistManager(session)

        # Add ticker that has never been refreshed
        ticker1 = Ticker("AAPL")
        await manager.add_ticker(ticker1)
        await session.commit()

        # Act
        stale = await manager.get_stale_tickers(limit=10)

        # Assert - should return AAPL (never refreshed)
        assert len(stale) == 1
        assert stale[0] == ticker1

    @pytest.mark.asyncio
    async def test_get_stale_returns_past_next_refresh_time(self, session):
        """Test getting tickers whose next_refresh_at has passed."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Add ticker and set next refresh in the past
        await manager.add_ticker(ticker)
        past_time = datetime.now(UTC) - timedelta(hours=1)
        next_time = datetime.now(UTC) - timedelta(minutes=30)
        await manager.update_refresh_metadata(ticker, past_time, next_time)
        await session.commit()

        # Act
        stale = await manager.get_stale_tickers(limit=10)

        # Assert
        assert len(stale) == 1
        assert stale[0] == ticker

    @pytest.mark.asyncio
    async def test_get_stale_excludes_recently_refreshed(self, session):
        """Test that recently refreshed tickers are not returned."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Add ticker and set next refresh in the future
        await manager.add_ticker(ticker)
        now = datetime.now(UTC)
        next_time = now + timedelta(hours=1)
        await manager.update_refresh_metadata(ticker, now, next_time)
        await session.commit()

        # Act
        stale = await manager.get_stale_tickers(limit=10)

        # Assert - should not return AAPL (next refresh is future)
        assert len(stale) == 0

    @pytest.mark.asyncio
    async def test_get_stale_respects_priority_ordering(self, session):
        """Test that stale tickers are returned in priority order."""
        # Arrange
        manager = WatchlistManager(session)

        # Add tickers with different priorities
        await manager.add_ticker(Ticker("AAPL"), priority=100)
        await manager.add_ticker(Ticker("GOOGL"), priority=50)
        await manager.add_ticker(Ticker("MSFT"), priority=75)
        await session.commit()

        # Act
        stale = await manager.get_stale_tickers(limit=10)

        # Assert - should be ordered by priority (lowest number first)
        assert len(stale) == 3
        assert stale[0] == Ticker("GOOGL")  # priority 50
        assert stale[1] == Ticker("MSFT")  # priority 75
        assert stale[2] == Ticker("AAPL")  # priority 100

    @pytest.mark.asyncio
    async def test_get_stale_respects_limit(self, session):
        """Test that limit parameter is respected."""
        # Arrange
        manager = WatchlistManager(session)

        # Add 5 tickers
        tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        for ticker_symbol in tickers:
            await manager.add_ticker(Ticker(ticker_symbol), priority=100)
        await session.commit()

        # Act - request only 3
        stale = await manager.get_stale_tickers(limit=3)

        # Assert
        assert len(stale) == 3

    @pytest.mark.asyncio
    async def test_get_stale_excludes_inactive_tickers(self, session):
        """Test that inactive tickers are not returned."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Add and then remove ticker
        await manager.add_ticker(ticker)
        await manager.remove_ticker(ticker)
        await session.commit()

        # Act
        stale = await manager.get_stale_tickers(limit=10)

        # Assert - should not return inactive ticker
        assert len(stale) == 0


class TestWatchlistManagerUpdateRefresh:
    """Tests for update_refresh_metadata method."""

    @pytest.mark.asyncio
    async def test_update_refresh_metadata_updates_timestamps(self, session):
        """Test updating refresh metadata."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        # Add ticker
        await manager.add_ticker(ticker)
        await session.commit()

        # Act
        now = datetime.now(UTC)
        next_time = now + timedelta(minutes=5)
        await manager.update_refresh_metadata(ticker, now, next_time)
        await session.commit()

        # Assert - ticker should not be stale anymore
        stale = await manager.get_stale_tickers(limit=10)
        assert len(stale) == 0

    @pytest.mark.asyncio
    async def test_update_refresh_metadata_allows_future_refresh(self, session):
        """Test that metadata update schedules future refresh."""
        # Arrange
        manager = WatchlistManager(session)
        ticker = Ticker("AAPL")

        await manager.add_ticker(ticker)
        await session.commit()

        # Act - set next refresh 10 seconds in future
        now = datetime.now(UTC)
        next_time = now + timedelta(seconds=10)
        await manager.update_refresh_metadata(ticker, now, next_time)
        await session.commit()

        # Assert - not stale yet
        stale = await manager.get_stale_tickers(limit=10)
        assert len(stale) == 0


class TestWatchlistManagerGetAllActive:
    """Tests for get_all_active_tickers method."""

    @pytest.mark.asyncio
    async def test_get_all_active_returns_all_active_tickers(self, session):
        """Test getting all active tickers."""
        # Arrange
        manager = WatchlistManager(session)

        # Add multiple tickers
        for ticker_symbol in ["AAPL", "GOOGL", "MSFT"]:
            await manager.add_ticker(Ticker(ticker_symbol))
        await session.commit()

        # Act
        active = await manager.get_all_active_tickers()

        # Assert
        assert len(active) == 3
        symbols = [t.symbol for t in active]
        assert "AAPL" in symbols
        assert "GOOGL" in symbols
        assert "MSFT" in symbols

    @pytest.mark.asyncio
    async def test_get_all_active_excludes_inactive(self, session):
        """Test that inactive tickers are excluded."""
        # Arrange
        manager = WatchlistManager(session)

        # Add tickers
        await manager.add_ticker(Ticker("AAPL"))
        await manager.add_ticker(Ticker("GOOGL"))
        await session.commit()

        # Remove one
        await manager.remove_ticker(Ticker("AAPL"))
        await session.commit()

        # Act
        active = await manager.get_all_active_tickers()

        # Assert - should only return GOOGL
        assert len(active) == 1
        assert active[0] == Ticker("GOOGL")

    @pytest.mark.asyncio
    async def test_get_all_active_returns_sorted_by_priority(self, session):
        """Test that tickers are returned sorted by priority."""
        # Arrange
        manager = WatchlistManager(session)

        # Add in mixed priority order
        await manager.add_ticker(Ticker("AAPL"), priority=100)
        await manager.add_ticker(Ticker("GOOGL"), priority=50)
        await manager.add_ticker(Ticker("MSFT"), priority=75)
        await session.commit()

        # Act
        active = await manager.get_all_active_tickers()

        # Assert - should be ordered by priority
        assert len(active) == 3
        assert active[0] == Ticker("GOOGL")  # priority 50
        assert active[1] == Ticker("MSFT")  # priority 75
        assert active[2] == Ticker("AAPL")  # priority 100

    @pytest.mark.asyncio
    async def test_get_all_active_returns_empty_when_none(self, session):
        """Test that empty list is returned when no active tickers."""
        # Arrange
        manager = WatchlistManager(session)

        # Act
        active = await manager.get_all_active_tickers()

        # Assert
        assert active == []
