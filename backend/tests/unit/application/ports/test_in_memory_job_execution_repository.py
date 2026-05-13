"""Tests for :class:`InMemoryJobExecutionRepository`.

Phase J (Task #212 Layer 1) — these tests pin the lifecycle contract
(record_start → RUNNING row, record_finish → terminal row, latest
returns newest started_at). The decorator tests reuse the in-memory
repo so its correctness is load-bearing.
"""

import asyncio

import pytest

from zebu.application.ports.in_memory_job_execution_repository import (
    InMemoryJobExecutionRepository,
)
from zebu.domain.value_objects.job_execution_status import JobExecutionStatus


@pytest.mark.asyncio
class TestRecordStart:
    async def test_returns_running_entity(self) -> None:
        repo = InMemoryJobExecutionRepository()
        execution = await repo.record_start("refresh_active_stocks")
        assert execution.status is JobExecutionStatus.RUNNING
        assert execution.finished_at is None
        assert execution.job_name == "refresh_active_stocks"

    async def test_assigns_fresh_id_each_call(self) -> None:
        repo = InMemoryJobExecutionRepository()
        a = await repo.record_start("refresh_active_stocks")
        b = await repo.record_start("refresh_active_stocks")
        assert a.id != b.id

    async def test_starter_metadata_persists(self) -> None:
        repo = InMemoryJobExecutionRepository()
        execution = await repo.record_start(
            "refresh_active_stocks",
            metadata={"trigger": "manual"},
        )
        assert execution.metadata == {"trigger": "manual"}

    async def test_no_metadata_yields_empty_dict(self) -> None:
        repo = InMemoryJobExecutionRepository()
        execution = await repo.record_start("refresh_active_stocks")
        assert execution.metadata == {}


@pytest.mark.asyncio
class TestRecordFinish:
    async def test_succeeded_path(self) -> None:
        repo = InMemoryJobExecutionRepository()
        start = await repo.record_start("refresh_active_stocks")
        finished = await repo.record_finish(
            start,
            status=JobExecutionStatus.SUCCEEDED,
            metadata={"duration_seconds": "1.234"},
        )
        assert finished.status is JobExecutionStatus.SUCCEEDED
        assert finished.finished_at is not None
        assert finished.error_message is None
        assert finished.metadata == {"duration_seconds": "1.234"}

    async def test_failed_path(self) -> None:
        repo = InMemoryJobExecutionRepository()
        start = await repo.record_start("refresh_active_stocks")
        finished = await repo.record_finish(
            start,
            status=JobExecutionStatus.FAILED,
            error_message="boom",
            metadata={"duration_seconds": "0.5"},
        )
        assert finished.status is JobExecutionStatus.FAILED
        assert finished.error_message == "boom"
        assert finished.metadata["duration_seconds"] == "0.5"

    async def test_metadata_merges_with_starter(self) -> None:
        """Starter keys persist; terminal keys merge in on top."""
        repo = InMemoryJobExecutionRepository()
        start = await repo.record_start(
            "refresh_active_stocks",
            metadata={"started_by": "scheduler"},
        )
        finished = await repo.record_finish(
            start,
            status=JobExecutionStatus.SUCCEEDED,
            metadata={"duration_seconds": "1.0"},
        )
        assert finished.metadata == {
            "started_by": "scheduler",
            "duration_seconds": "1.0",
        }

    async def test_running_status_rejected(self) -> None:
        repo = InMemoryJobExecutionRepository()
        start = await repo.record_start("refresh_active_stocks")
        with pytest.raises(ValueError, match="record_finish requires a terminal"):
            await repo.record_finish(start, status=JobExecutionStatus.RUNNING)

    async def test_missing_row_raises(self) -> None:
        """Calling record_finish for an unknown execution raises ValueError."""
        repo = InMemoryJobExecutionRepository()
        # Build a fake handle that was never persisted
        start = await repo.record_start("refresh_active_stocks")
        repo.clear()
        with pytest.raises(ValueError, match="not found"):
            await repo.record_finish(start, status=JobExecutionStatus.SUCCEEDED)


@pytest.mark.asyncio
class TestLatest:
    async def test_returns_none_for_unknown_job(self) -> None:
        repo = InMemoryJobExecutionRepository()
        assert await repo.latest("never_run") is None

    async def test_returns_most_recent_by_started_at(self) -> None:
        repo = InMemoryJobExecutionRepository()
        first = await repo.record_start("refresh_active_stocks")
        # Force a small ordering gap so timestamps differ
        await asyncio.sleep(0.001)
        second = await repo.record_start("refresh_active_stocks")
        latest = await repo.latest("refresh_active_stocks")
        assert latest is not None
        assert latest.id == second.id
        # Sanity: not equal to first
        assert latest.id != first.id

    async def test_isolates_per_job(self) -> None:
        repo = InMemoryJobExecutionRepository()
        a = await repo.record_start("refresh_active_stocks")
        await repo.record_start("evaluate_triggers")
        latest_refresh = await repo.latest("refresh_active_stocks")
        assert latest_refresh is not None
        assert latest_refresh.id == a.id


@pytest.mark.asyncio
class TestListRecent:
    async def test_returns_newest_first(self) -> None:
        repo = InMemoryJobExecutionRepository()
        first = await repo.record_start("refresh_active_stocks")
        await asyncio.sleep(0.001)
        second = await repo.record_start("refresh_active_stocks")
        rows = await repo.list_recent("refresh_active_stocks")
        assert [r.id for r in rows] == [second.id, first.id]

    async def test_respects_limit(self) -> None:
        repo = InMemoryJobExecutionRepository()
        for _ in range(5):
            await repo.record_start("refresh_active_stocks")
            await asyncio.sleep(0.001)
        rows = await repo.list_recent("refresh_active_stocks", limit=2)
        assert len(rows) == 2

    async def test_no_filter_returns_all_jobs(self) -> None:
        repo = InMemoryJobExecutionRepository()
        await repo.record_start("refresh_active_stocks")
        await repo.record_start("evaluate_triggers")
        rows = await repo.list_recent()
        assert {r.job_name for r in rows} == {
            "refresh_active_stocks",
            "evaluate_triggers",
        }
