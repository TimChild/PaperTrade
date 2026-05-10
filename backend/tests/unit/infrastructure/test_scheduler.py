"""Integration tests for background scheduler."""

from zebu.infrastructure.scheduler import (
    SchedulerConfig,
    evaluate_triggers,
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
        # Phase F-2 — trigger evaluation job defaults.
        # Market-hours window every 15 minutes Mon-Fri 14:00-20:59 UTC
        # (covers 09:30-17:00 ET ±1 hour for DST). Off-hours every 6h.
        assert config.trigger_evaluation_market_hours_cron == "*/15 14-20 * * 1-5"
        assert config.trigger_evaluation_off_hours_cron == "0 */6 * * *"
        assert config.trigger_evaluation_enabled is True

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


class TestTriggerEvaluationJob:
    """Phase F-2 — trigger evaluation job registration."""

    async def test_trigger_evaluation_jobs_registered_by_default(self) -> None:
        """Default config registers both trigger evaluator jobs."""
        config = SchedulerConfig(enabled=True)
        try:
            await start_scheduler(config)
            from zebu.infrastructure.scheduler import get_scheduler

            scheduler = get_scheduler()
            assert scheduler is not None
            ids = {j.id for j in scheduler.get_jobs()}
            assert "evaluate_triggers_market_hours" in ids
            assert "evaluate_triggers_off_hours" in ids
            # Idempotent re-registration: starting twice doesn't duplicate.
            await start_scheduler(config)
            jobs = scheduler.get_jobs()
            market_jobs = [j for j in jobs if j.id == "evaluate_triggers_market_hours"]
            off_hours_jobs = [j for j in jobs if j.id == "evaluate_triggers_off_hours"]
            assert len(market_jobs) == 1
            assert len(off_hours_jobs) == 1
        finally:
            await stop_scheduler()

    async def test_trigger_evaluation_jobs_disabled_by_config(self) -> None:
        """``trigger_evaluation_enabled=False`` skips job registration."""
        config = SchedulerConfig(enabled=True, trigger_evaluation_enabled=False)
        try:
            await start_scheduler(config)
            from zebu.infrastructure.scheduler import get_scheduler

            scheduler = get_scheduler()
            assert scheduler is not None
            ids = {j.id for j in scheduler.get_jobs()}
            assert "evaluate_triggers_market_hours" not in ids
            assert "evaluate_triggers_off_hours" not in ids
            # Other jobs unaffected.
            assert "refresh_prices" in ids
        finally:
            await stop_scheduler()

    async def test_trigger_evaluation_jobs_have_max_instances_one(self) -> None:
        """Both trigger jobs are registered with ``max_instances=1``.

        Per the Phase-F design §6.1: APScheduler ``max_instances=1`` is
        the only deduplication mechanism so a slow tick can't queue up.
        """
        config = SchedulerConfig(enabled=True)
        try:
            await start_scheduler(config)
            from zebu.infrastructure.scheduler import get_scheduler

            scheduler = get_scheduler()
            assert scheduler is not None
            for job_id in (
                "evaluate_triggers_market_hours",
                "evaluate_triggers_off_hours",
            ):
                job = scheduler.get_job(job_id)
                assert job is not None
                assert job.max_instances == 1
        finally:
            await stop_scheduler()

    async def test_trigger_evaluation_market_hours_cron_matches_config(
        self,
    ) -> None:
        """The registered market-hours job uses the config cron string."""
        # Use a custom cron so we can assert pass-through; APScheduler
        # exposes the trigger via ``str(job.trigger)``.
        config = SchedulerConfig(
            enabled=True,
            trigger_evaluation_market_hours_cron="*/30 14-20 * * 1-5",
        )
        try:
            await start_scheduler(config)
            from zebu.infrastructure.scheduler import get_scheduler

            scheduler = get_scheduler()
            assert scheduler is not None
            job = scheduler.get_job("evaluate_triggers_market_hours")
            assert job is not None
            # APScheduler renders the CronTrigger as a string containing
            # each field; check that the minute and hour overrides flow
            # through.
            trigger_repr = str(job.trigger)
            assert "*/30" in trigger_repr
            assert "14-20" in trigger_repr
        finally:
            await stop_scheduler()

    def test_evaluate_triggers_is_callable(self) -> None:
        """``evaluate_triggers`` must be importable and an async coroutine."""
        # The scheduler registers ``evaluate_triggers`` directly. Pin
        # this so a bad rename surfaces here, not at first cron fire.
        import inspect

        assert inspect.iscoroutinefunction(evaluate_triggers)
