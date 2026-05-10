"""Integration tests for background scheduler."""

from zebu.infrastructure.scheduler import (
    SchedulerConfig,
    execute_active_strategies,
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
        # Phase C1.2 — live strategy execution job defaults
        assert config.strategy_execution_cron == "30 0 * * 1-5"
        assert config.strategy_execution_enabled is True

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


class TestStrategyExecutionJob:
    """Phase C1.2 — live strategy execution job registration."""

    async def test_strategy_execution_job_registered_by_default(self) -> None:
        """Default config registers the live execution job alongside refresh."""
        config = SchedulerConfig(enabled=True)
        try:
            await start_scheduler(config)
            from zebu.infrastructure.scheduler import get_scheduler

            scheduler = get_scheduler()
            assert scheduler is not None
            ids = {j.id for j in scheduler.get_jobs()}
            assert "execute_active_strategies" in ids
            # Don't double-register on a second start.
            await start_scheduler(config)
            jobs = scheduler.get_jobs()
            execution_jobs = [j for j in jobs if j.id == "execute_active_strategies"]
            assert len(execution_jobs) == 1
        finally:
            await stop_scheduler()

    async def test_strategy_execution_job_disabled_by_config(self) -> None:
        """``strategy_execution_enabled=False`` skips the registration."""
        config = SchedulerConfig(enabled=True, strategy_execution_enabled=False)
        try:
            await start_scheduler(config)
            from zebu.infrastructure.scheduler import get_scheduler

            scheduler = get_scheduler()
            assert scheduler is not None
            ids = {j.id for j in scheduler.get_jobs()}
            assert "execute_active_strategies" not in ids
            # Other jobs are unaffected.
            assert "refresh_prices" in ids
        finally:
            await stop_scheduler()

    def test_execute_active_strategies_is_callable(self) -> None:
        """The job function exposed for APScheduler must be a coroutine fn."""
        # The scheduler registers ``execute_active_strategies`` directly;
        # it must be importable and async-callable. Pin this so a bad
        # rename refactor surfaces here, not at first cron fire.
        import inspect

        assert inspect.iscoroutinefunction(execute_active_strategies)
