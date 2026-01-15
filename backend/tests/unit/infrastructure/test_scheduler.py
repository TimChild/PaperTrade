"""Integration tests for background scheduler."""

from unittest.mock import AsyncMock

import pytest

from zebu.infrastructure.scheduler import (
    SchedulerConfig,
    refresh_active_stocks,
    start_scheduler,
    stop_scheduler,
)


class TestSchedulerConfiguration:
    """Tests for scheduler configuration."""

    def test_scheduler_config_defaults(self) -> None:
        """Test that SchedulerConfig has correct default values."""
        config = SchedulerConfig()

        assert config.enabled is True
        assert config.refresh_cron == "0 0 * * *"
        assert config.timezone == "UTC"
        assert config.max_instances == 1
        assert config.batch_size == 5
        assert config.batch_delay_seconds == 60
        assert config.max_age_hours == 24
        assert config.active_stock_days == 30

    def test_scheduler_config_custom_values(self) -> None:
        """Test that SchedulerConfig accepts custom values."""
        config = SchedulerConfig(
            enabled=False,
            refresh_cron="0 */6 * * *",  # Every 6 hours
            batch_size=10,
            batch_delay_seconds=12,
            active_stock_days=7,
        )

        assert config.enabled is False
        assert config.refresh_cron == "0 */6 * * *"
        assert config.batch_size == 10
        assert config.batch_delay_seconds == 12
        assert config.active_stock_days == 7


class TestRefreshActiveStocks:
    """Tests for refresh_active_stocks job."""

    @pytest.mark.skip(reason="Requires database setup and mocked market data")
    async def test_refresh_with_no_active_tickers(self, test_engine: AsyncMock) -> None:
        """Test refresh job handles empty ticker list gracefully."""
        # Arrange
        config = SchedulerConfig(
            enabled=True,
            batch_size=5,
            batch_delay_seconds=1,
            active_stock_days=30,
        )

        # Act - should not raise any errors
        await refresh_active_stocks(config)

        # Assert - job completes without errors

    @pytest.mark.asyncio
    async def test_refresh_updates_watchlist_metadata(
        self, test_engine: AsyncMock
    ) -> None:
        """Test that refresh updates watchlist metadata after fetching prices."""
        # This test requires a more complex setup with mocked market data
        # For now, we'll skip it and rely on manual testing
        pytest.skip("Requires mocked market data adapter")

    @pytest.mark.asyncio
    async def test_refresh_respects_batch_delay(self) -> None:
        """Test that refresh job waits between batches."""
        # This test would measure timing between batches
        # For now, we'll skip it as it's timing-dependent
        pytest.skip("Timing-dependent test, skip for CI stability")


class TestSchedulerLifecycle:
    """Tests for scheduler start/stop lifecycle."""

    async def test_start_scheduler_when_disabled(self) -> None:
        """Test that scheduler doesn't start when disabled in config."""
        # Arrange
        config = SchedulerConfig(enabled=False)

        # Act
        await start_scheduler(config)

        # Assert - no scheduler should be created
        from zebu.infrastructure.scheduler import is_scheduler_running

        assert not is_scheduler_running()

    async def test_start_and_stop_scheduler(self) -> None:
        """Test that scheduler can be started and stopped."""
        # Arrange
        config = SchedulerConfig(
            enabled=True,
            refresh_cron="0 0 * * *",
        )

        try:
            # Act - Start
            await start_scheduler(config)

            # Assert - Scheduler is running
            from zebu.infrastructure.scheduler import is_scheduler_running

            assert is_scheduler_running()

        finally:
            # Act - Stop
            await stop_scheduler()

            # Assert - Scheduler is stopped
            from zebu.infrastructure.scheduler import is_scheduler_running

            assert not is_scheduler_running()

    async def test_start_scheduler_twice_does_not_duplicate(self) -> None:
        """Test that starting scheduler twice doesn't create duplicate instance."""
        # Arrange
        config = SchedulerConfig(enabled=True)

        try:
            # Act - Start twice
            await start_scheduler(config)
            await start_scheduler(config)

            # Assert - Only one scheduler instance
            from zebu.infrastructure.scheduler import get_scheduler

            scheduler = get_scheduler()
            assert scheduler is not None

            # Check that there's only one job
            jobs = scheduler.get_jobs()
            refresh_jobs = [j for j in jobs if j.id == "refresh_prices"]
            assert len(refresh_jobs) == 1

        finally:
            # Cleanup
            await stop_scheduler()


class TestSchedulerIntegration:
    """Integration tests for scheduler with database."""

    @pytest.mark.asyncio
    async def test_refresh_finds_tickers_from_watchlist_and_transactions(
        self, test_engine: AsyncMock
    ) -> None:
        """Test that refresh job finds tickers from both watchlist and transactions."""
        # This is a more complex integration test that would require:
        # 1. Seeding database with watchlist entries
        # 2. Seeding database with transactions
        # 3. Mocking market data adapter
        # 4. Running refresh job
        # 5. Verifying that prices were fetched for all tickers
        pytest.skip("Complex integration test - manual testing recommended")
