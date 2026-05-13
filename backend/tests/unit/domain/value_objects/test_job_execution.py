"""Tests for the :class:`JobExecution` value object.

Phase J (Task #212 Layer 1) — these tests pin the invariants of the
audit row entity. Lifecycle behaviour (record_start / record_finish) is
exercised in the in-memory repository tests and the decorator tests.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from zebu.domain.value_objects.job_execution import JobExecution
from zebu.domain.value_objects.job_execution_status import JobExecutionStatus


def _running(
    *,
    started_at: datetime | None = None,
) -> JobExecution:
    """Build a minimal ``RUNNING`` entity for tests."""
    return JobExecution(
        id=uuid4(),
        job_name="refresh_active_stocks",
        started_at=started_at if started_at is not None else datetime.now(UTC),
        status=JobExecutionStatus.RUNNING,
        metadata={},
    )


def _terminal(
    *,
    status: JobExecutionStatus,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    metadata: dict[str, str] | None = None,
    error_message: str | None = None,
) -> JobExecution:
    """Build a terminal-state entity for tests."""
    started = started_at if started_at is not None else datetime.now(UTC)
    finished = (
        finished_at if finished_at is not None else started + timedelta(seconds=1)
    )
    return JobExecution(
        id=uuid4(),
        job_name="refresh_active_stocks",
        started_at=started,
        finished_at=finished,
        status=status,
        metadata=metadata if metadata is not None else {},
        error_message=error_message,
    )


class TestJobExecutionRunning:
    """Construction in ``RUNNING`` state."""

    def test_running_with_minimal_fields_constructs(self) -> None:
        execution = _running()
        assert execution.status is JobExecutionStatus.RUNNING
        assert execution.finished_at is None
        assert execution.error_message is None

    def test_running_rejects_finished_at(self) -> None:
        """A RUNNING row cannot carry a finished_at."""
        with pytest.raises(ValueError, match="status=RUNNING requires finished_at"):
            JobExecution(
                id=uuid4(),
                job_name="refresh_active_stocks",
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                status=JobExecutionStatus.RUNNING,
                metadata={},
            )


class TestJobExecutionTerminal:
    """Construction in ``SUCCEEDED`` / ``FAILED`` states."""

    def test_succeeded_requires_finished_at(self) -> None:
        with pytest.raises(ValueError, match="status=SUCCEEDED requires finished_at"):
            JobExecution(
                id=uuid4(),
                job_name="refresh_active_stocks",
                started_at=datetime.now(UTC),
                status=JobExecutionStatus.SUCCEEDED,
                metadata={},
            )

    def test_failed_requires_finished_at(self) -> None:
        with pytest.raises(ValueError, match="status=FAILED requires finished_at"):
            JobExecution(
                id=uuid4(),
                job_name="refresh_active_stocks",
                started_at=datetime.now(UTC),
                status=JobExecutionStatus.FAILED,
                metadata={},
            )

    def test_succeeded_with_terminal_fields_constructs(self) -> None:
        execution = _terminal(status=JobExecutionStatus.SUCCEEDED)
        assert execution.status is JobExecutionStatus.SUCCEEDED
        assert execution.finished_at is not None

    def test_failed_with_error_message_constructs(self) -> None:
        execution = _terminal(
            status=JobExecutionStatus.FAILED,
            error_message="boom",
        )
        assert execution.error_message == "boom"


class TestJobExecutionInvariants:
    """Other invariants pinned by ``__post_init__``."""

    def test_empty_job_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="job_name must be non-empty"):
            JobExecution(
                id=uuid4(),
                job_name="",
                started_at=datetime.now(UTC),
                status=JobExecutionStatus.RUNNING,
                metadata={},
            )

    def test_naive_started_at_rejected(self) -> None:
        with pytest.raises(ValueError, match="started_at must be timezone-aware"):
            JobExecution(
                id=uuid4(),
                job_name="refresh_active_stocks",
                started_at=datetime.now(),  # noqa: DTZ005  # naive on purpose for the test
                status=JobExecutionStatus.RUNNING,
                metadata={},
            )

    def test_naive_finished_at_rejected(self) -> None:
        started = datetime.now(UTC)
        with pytest.raises(ValueError, match="finished_at must be timezone-aware"):
            JobExecution(
                id=uuid4(),
                job_name="refresh_active_stocks",
                started_at=started,
                finished_at=datetime.now(),  # noqa: DTZ005  # naive on purpose for the test
                status=JobExecutionStatus.SUCCEEDED,
                metadata={},
            )

    def test_finished_before_started_rejected(self) -> None:
        started = datetime.now(UTC)
        with pytest.raises(ValueError, match="finished_at must be >= started_at"):
            JobExecution(
                id=uuid4(),
                job_name="refresh_active_stocks",
                started_at=started,
                finished_at=started - timedelta(seconds=1),
                status=JobExecutionStatus.SUCCEEDED,
                metadata={},
            )

    def test_overlong_error_message_rejected(self) -> None:
        with pytest.raises(ValueError, match="error_message must be at most"):
            _terminal(
                status=JobExecutionStatus.FAILED,
                error_message="x" * 501,
            )

    def test_error_message_at_max_accepted(self) -> None:
        execution = _terminal(
            status=JobExecutionStatus.FAILED,
            error_message="x" * 500,
        )
        assert execution.error_message is not None
        assert len(execution.error_message) == 500

    def test_metadata_is_copied(self) -> None:
        """Mutating the source dict must not affect the persisted entity."""
        source: dict[str, str] = {"k": "v"}
        execution = _running()
        # Build a new one with metadata to test isolation
        execution = JobExecution(
            id=execution.id,
            job_name=execution.job_name,
            started_at=execution.started_at,
            status=JobExecutionStatus.RUNNING,
            metadata=source,
        )
        source["k"] = "tampered"
        assert execution.metadata == {"k": "v"}


class TestJobExecutionIdentity:
    """Equality / hashing semantics."""

    def test_equality_is_by_id(self) -> None:
        a = _running()
        b = JobExecution(
            id=a.id,
            job_name="different_name",  # contents differ
            started_at=datetime.now(UTC),
            status=JobExecutionStatus.RUNNING,
            metadata={"k": "v"},
        )
        assert a == b

    def test_different_ids_unequal(self) -> None:
        a = _running()
        b = _running()
        assert a != b

    def test_hashable(self) -> None:
        a = _running()
        assert {a} == {a}
