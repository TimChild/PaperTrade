"""Integration tests for background scheduler."""

from zebu.infrastructure.scheduler import (
    SchedulerConfig,
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
