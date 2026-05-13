"""Tests for the :class:`BackfillTask` entity.

Phase J (Task #212 Layer 2) — pin the invariants of the queued-fetch
audit row. Lifecycle behaviour (the in-memory adapter's ``mark_*``
helpers) is exercised separately in the port tests.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from zebu.domain.entities.backfill_task import (
    BackfillTask,
    InvalidBackfillTaskError,
)
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.ticker import Ticker


def _pending(
    *,
    ticker: str = "AAPL",
    start: date | None = None,
    end: date | None = None,
    priority: BackfillPriority = BackfillPriority.LOW,
    created_at: datetime | None = None,
) -> BackfillTask:
    """Build a minimal PENDING task for tests."""
    today = date.today()
    return BackfillTask(
        id=uuid4(),
        ticker=Ticker(ticker),
        start_date=start if start is not None else today - timedelta(days=30),
        end_date=end if end is not None else today,
        priority=priority,
        status=BackfillTaskStatus.PENDING,
        created_at=created_at if created_at is not None else datetime.now(UTC),
    )


class TestBackfillTaskPending:
    """Construction in PENDING state."""

    def test_pending_with_minimal_fields_constructs(self) -> None:
        task = _pending()
        assert task.status is BackfillTaskStatus.PENDING
        assert task.finished_at is None
        assert task.error_message is None
        assert not task.is_terminal

    def test_pending_rejects_finished_at(self) -> None:
        with pytest.raises(InvalidBackfillTaskError, match="finished_at to be None"):
            BackfillTask(
                id=uuid4(),
                ticker=Ticker("AAPL"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                priority=BackfillPriority.LOW,
                status=BackfillTaskStatus.PENDING,
                created_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )

    def test_pending_rejects_error_message(self) -> None:
        with pytest.raises(
            InvalidBackfillTaskError, match="must not carry an error_message"
        ):
            BackfillTask(
                id=uuid4(),
                ticker=Ticker("AAPL"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                priority=BackfillPriority.LOW,
                status=BackfillTaskStatus.PENDING,
                created_at=datetime.now(UTC),
                error_message="boom",
            )


class TestBackfillTaskDateRange:
    """Date-range invariants."""

    def test_end_before_start_rejected(self) -> None:
        with pytest.raises(
            InvalidBackfillTaskError, match="end_date must be >= start_date"
        ):
            _pending(start=date(2024, 1, 31), end=date(2024, 1, 1))

    def test_single_day_window_accepted(self) -> None:
        d = date(2024, 1, 15)
        task = _pending(start=d, end=d)
        assert task.start_date == task.end_date


class TestBackfillTaskTimestamps:
    """Timestamp invariants."""

    def test_naive_created_at_rejected(self) -> None:
        with pytest.raises(
            InvalidBackfillTaskError, match="created_at must be timezone-aware"
        ):
            BackfillTask(
                id=uuid4(),
                ticker=Ticker("AAPL"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                priority=BackfillPriority.LOW,
                status=BackfillTaskStatus.PENDING,
                created_at=datetime.now(),  # noqa: DTZ005 - intentional
            )

    def test_future_created_at_rejected(self) -> None:
        future = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(
            InvalidBackfillTaskError, match="created_at cannot be in the future"
        ):
            _pending(created_at=future)


class TestBackfillTaskTerminalStates:
    """SUCCEEDED / FAILED invariants."""

    def test_succeeded_requires_finished_at(self) -> None:
        with pytest.raises(
            InvalidBackfillTaskError, match="succeeded requires finished_at"
        ):
            BackfillTask(
                id=uuid4(),
                ticker=Ticker("AAPL"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                priority=BackfillPriority.LOW,
                status=BackfillTaskStatus.SUCCEEDED,
                created_at=datetime.now(UTC),
            )

    def test_failed_requires_error_message(self) -> None:
        with pytest.raises(
            InvalidBackfillTaskError, match="FAILED requires a non-empty error_message"
        ):
            BackfillTask(
                id=uuid4(),
                ticker=Ticker("AAPL"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                priority=BackfillPriority.LOW,
                status=BackfillTaskStatus.FAILED,
                created_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )

    def test_failed_rejects_whitespace_only_error_message(self) -> None:
        with pytest.raises(InvalidBackfillTaskError, match="non-empty error_message"):
            BackfillTask(
                id=uuid4(),
                ticker=Ticker("AAPL"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                priority=BackfillPriority.LOW,
                status=BackfillTaskStatus.FAILED,
                created_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                error_message="   ",
            )

    def test_succeeded_with_terminal_fields_constructs(self) -> None:
        now = datetime.now(UTC)
        task = BackfillTask(
            id=uuid4(),
            ticker=Ticker("AAPL"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            priority=BackfillPriority.HIGH,
            status=BackfillTaskStatus.SUCCEEDED,
            created_at=now - timedelta(seconds=10),
            finished_at=now,
        )
        assert task.status is BackfillTaskStatus.SUCCEEDED
        assert task.is_terminal

    def test_overlong_error_message_rejected(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(
            InvalidBackfillTaskError, match="error_message must be at most"
        ):
            BackfillTask(
                id=uuid4(),
                ticker=Ticker("AAPL"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                priority=BackfillPriority.LOW,
                status=BackfillTaskStatus.FAILED,
                created_at=now - timedelta(seconds=10),
                finished_at=now,
                error_message="x" * 501,
            )


class TestBackfillTaskTransitions:
    """State-machine helpers."""

    def test_start_running_from_pending(self) -> None:
        task = _pending()
        running = task.start_running()
        assert running.status is BackfillTaskStatus.RUNNING
        assert running.finished_at is None
        # Original is unchanged (frozen).
        assert task.status is BackfillTaskStatus.PENDING

    def test_start_running_from_running_rejected(self) -> None:
        task = _pending().start_running()
        with pytest.raises(InvalidBackfillTaskError, match="only PENDING"):
            task.start_running()

    def test_mark_succeeded_from_running(self) -> None:
        running = _pending().start_running()
        now = datetime.now(UTC)
        finished = running.mark_succeeded(at=now)
        assert finished.status is BackfillTaskStatus.SUCCEEDED
        # The entity's invariant requires finished_at >= created_at;
        # the equality check is on the same datetime instance.
        assert finished.finished_at == now
        assert finished.finished_at is not None
        assert finished.finished_at >= finished.created_at

    def test_mark_succeeded_from_terminal_rejected(self) -> None:
        finished = _pending().start_running().mark_succeeded(at=datetime.now(UTC))
        with pytest.raises(InvalidBackfillTaskError, match="already terminal"):
            finished.mark_succeeded(at=datetime.now(UTC))

    def test_mark_failed_from_running(self) -> None:
        running = _pending().start_running()
        now = datetime.now(UTC)
        failed = running.mark_failed(error_message="boom", at=now)
        assert failed.status is BackfillTaskStatus.FAILED
        assert failed.error_message == "boom"

    def test_mark_failed_from_pending(self) -> None:
        """Permitted — the spec calls for short-circuit FAIL of a fresh task."""
        task = _pending()
        now = datetime.now(UTC)
        failed = task.mark_failed(error_message="boom", at=now)
        assert failed.status is BackfillTaskStatus.FAILED

    def test_mark_failed_truncates_long_message(self) -> None:
        task = _pending()
        now = datetime.now(UTC)
        long_msg = "x" * 700
        failed = task.mark_failed(error_message=long_msg, at=now)
        assert failed.error_message is not None
        assert len(failed.error_message) == 500

    def test_mark_failed_empty_message_rejected(self) -> None:
        task = _pending()
        now = datetime.now(UTC)
        with pytest.raises(
            InvalidBackfillTaskError, match="requires a non-empty error_message"
        ):
            task.mark_failed(error_message="   ", at=now)


class TestBackfillTaskIdentity:
    """Equality / hashing semantics."""

    def test_equality_is_by_id(self) -> None:
        a = _pending()
        b = BackfillTask(
            id=a.id,
            ticker=Ticker("MSFT"),  # contents differ
            start_date=a.start_date,
            end_date=a.end_date,
            priority=BackfillPriority.HIGH,
            status=BackfillTaskStatus.PENDING,
            created_at=a.created_at,
        )
        assert a == b

    def test_different_ids_unequal(self) -> None:
        assert _pending() != _pending()

    def test_hashable(self) -> None:
        a = _pending()
        assert {a, a} == {a}
