"""Tests for :class:`InMemoryBacktestAgentInvocationRepository` (Phase L-1)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from zebu.application.ports.in_memory_backtest_agent_invocation_repository import (
    InMemoryBacktestAgentInvocationRepository,
)
from zebu.domain.entities.backtest_agent_invocation import BacktestAgentInvocation
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)


def _make_mock(**overrides: Any) -> BacktestAgentInvocation:
    """Factory for a MOCK-mode invocation row."""
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "backtest_run_id": uuid4(),
        "simulated_date": date(2024, 6, 1),
        "trigger_id": uuid4(),
        "condition_evaluation_data": {"schema_version": 1},
        "rationale": "",
        "latency_ms": 0,
        "model": "",
        "invocation_mode": BacktestAgentInvocationMode.MOCK,
        "created_at": datetime.now(UTC) - timedelta(seconds=5),
    }
    defaults.update(overrides)
    return BacktestAgentInvocation(**defaults)


def _make_live_hold(**overrides: Any) -> BacktestAgentInvocation:
    """Factory for a LIVE HOLD invocation row."""
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "backtest_run_id": uuid4(),
        "simulated_date": date(2024, 6, 1),
        "trigger_id": uuid4(),
        "condition_evaluation_data": {"schema_version": 1},
        "agent_decision": AgentDecision.HOLD,
        "rationale": "Decided to hold.",
        "decision_payload": {"notes": "no signal"},
        "decision_executed": False,
        "invocation_mode": BacktestAgentInvocationMode.LIVE,
        "agent_invocation_id": "msg_01abc",
        "latency_ms": 1500,
        "model": "claude-haiku-4-5-20251001",
        "created_at": datetime.now(UTC) - timedelta(seconds=2),
    }
    defaults.update(overrides)
    return BacktestAgentInvocation(**defaults)


# ---------------------------------------------------------------------------
# Basic round-trips
# ---------------------------------------------------------------------------


class TestBasicRoundTrips:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        repo = InMemoryBacktestAgentInvocationRepository()
        record = _make_mock()
        await repo.save(record)
        loaded = await repo.get(record.id)
        assert loaded == record

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self) -> None:
        repo = InMemoryBacktestAgentInvocationRepository()
        result = await repo.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_save_duplicate_id_raises(self) -> None:
        repo = InMemoryBacktestAgentInvocationRepository()
        record = _make_mock()
        await repo.save(record)
        with pytest.raises(ValueError, match="already exists"):
            await repo.save(record)


# ---------------------------------------------------------------------------
# save_all bulk insert
# ---------------------------------------------------------------------------


class TestSaveAll:
    @pytest.mark.asyncio
    async def test_save_all_mixed_modes_round_trips(self) -> None:
        """Bulk insert preserves mode-specific shape of each row."""
        repo = InMemoryBacktestAgentInvocationRepository()
        run_id = uuid4()
        rows = [
            _make_mock(backtest_run_id=run_id, simulated_date=date(2024, 6, 1)),
            _make_live_hold(backtest_run_id=run_id, simulated_date=date(2024, 6, 2)),
            _make_mock(backtest_run_id=run_id, simulated_date=date(2024, 6, 3)),
        ]
        await repo.save_all(rows)

        for row in rows:
            loaded = await repo.get(row.id)
            assert loaded == row

    @pytest.mark.asyncio
    async def test_save_all_empty_is_noop(self) -> None:
        repo = InMemoryBacktestAgentInvocationRepository()
        await repo.save_all([])
        assert await repo.count_for_backtest_run(uuid4()) == 0

    @pytest.mark.asyncio
    async def test_save_all_duplicate_within_batch_raises(self) -> None:
        """Same id appearing twice in the batch fails before any row lands."""
        repo = InMemoryBacktestAgentInvocationRepository()
        shared = _make_mock()
        twin = _make_mock(id=shared.id, simulated_date=date(2024, 6, 5))
        with pytest.raises(ValueError, match="Duplicate id"):
            await repo.save_all([shared, twin])
        # Neither row should have been persisted.
        assert await repo.get(shared.id) is None

    @pytest.mark.asyncio
    async def test_save_all_duplicate_against_existing_raises(self) -> None:
        """An id already present in storage fails the batch."""
        repo = InMemoryBacktestAgentInvocationRepository()
        existing = _make_mock()
        await repo.save(existing)
        twin = _make_mock(id=existing.id)
        with pytest.raises(ValueError, match="already exists"):
            await repo.save_all([twin])


# ---------------------------------------------------------------------------
# list / count semantics
# ---------------------------------------------------------------------------


class TestListAndCount:
    @pytest.mark.asyncio
    async def test_list_chronological_order_simulated_date(self) -> None:
        """Ordering: simulated_date asc, then created_at asc."""
        repo = InMemoryBacktestAgentInvocationRepository()
        run_id = uuid4()
        latest = _make_mock(
            backtest_run_id=run_id,
            simulated_date=date(2024, 6, 3),
        )
        earliest = _make_mock(
            backtest_run_id=run_id,
            simulated_date=date(2024, 6, 1),
        )
        middle = _make_mock(
            backtest_run_id=run_id,
            simulated_date=date(2024, 6, 2),
        )
        # Save in non-chronological order.
        for r in [latest, earliest, middle]:
            await repo.save(r)

        result = await repo.list_for_backtest_run(run_id)
        assert [r.id for r in result] == [earliest.id, middle.id, latest.id]

    @pytest.mark.asyncio
    async def test_list_ties_broken_by_created_at(self) -> None:
        """Same simulated_date: order by created_at ascending."""
        repo = InMemoryBacktestAgentInvocationRepository()
        run_id = uuid4()
        sim_day = date(2024, 6, 1)
        first = _make_mock(
            backtest_run_id=run_id,
            simulated_date=sim_day,
            created_at=datetime.now(UTC) - timedelta(seconds=20),
        )
        second = _make_mock(
            backtest_run_id=run_id,
            simulated_date=sim_day,
            created_at=datetime.now(UTC) - timedelta(seconds=10),
        )
        # Insert in reverse wall-clock order.
        await repo.save(second)
        await repo.save(first)

        result = await repo.list_for_backtest_run(run_id)
        assert [r.id for r in result] == [first.id, second.id]

    @pytest.mark.asyncio
    async def test_list_filters_by_run(self) -> None:
        """Rows for a different run must not appear."""
        repo = InMemoryBacktestAgentInvocationRepository()
        run_a, run_b = uuid4(), uuid4()
        row_a = _make_mock(backtest_run_id=run_a)
        row_b = _make_mock(backtest_run_id=run_b)
        await repo.save(row_a)
        await repo.save(row_b)

        result = await repo.list_for_backtest_run(run_a)
        assert [r.id for r in result] == [row_a.id]

    @pytest.mark.asyncio
    async def test_list_pagination(self) -> None:
        repo = InMemoryBacktestAgentInvocationRepository()
        run_id = uuid4()
        rows = [
            _make_mock(
                backtest_run_id=run_id,
                simulated_date=date(2024, 6, 1) + timedelta(days=i),
            )
            for i in range(5)
        ]
        await repo.save_all(rows)

        page_1 = await repo.list_for_backtest_run(run_id, limit=2, offset=0)
        assert [r.id for r in page_1] == [rows[0].id, rows[1].id]
        page_2 = await repo.list_for_backtest_run(run_id, limit=2, offset=2)
        assert [r.id for r in page_2] == [rows[2].id, rows[3].id]
        page_3 = await repo.list_for_backtest_run(run_id, limit=2, offset=4)
        assert [r.id for r in page_3] == [rows[4].id]

    @pytest.mark.asyncio
    async def test_count_matches_list(self) -> None:
        repo = InMemoryBacktestAgentInvocationRepository()
        run_id = uuid4()
        for i in range(3):
            await repo.save(
                _make_mock(
                    backtest_run_id=run_id,
                    simulated_date=date(2024, 6, 1) + timedelta(days=i),
                )
            )
        # Add a row for a different run — must not be counted.
        await repo.save(_make_mock(backtest_run_id=uuid4()))

        count = await repo.count_for_backtest_run(run_id)
        rows = await repo.list_for_backtest_run(run_id)
        assert count == len(rows) == 3

    @pytest.mark.asyncio
    async def test_count_empty_run_is_zero(self) -> None:
        repo = InMemoryBacktestAgentInvocationRepository()
        assert await repo.count_for_backtest_run(uuid4()) == 0


# ---------------------------------------------------------------------------
# Adapter-only helpers
# ---------------------------------------------------------------------------


class TestClearHelper:
    @pytest.mark.asyncio
    async def test_clear_resets_storage(self) -> None:
        repo = InMemoryBacktestAgentInvocationRepository()
        await repo.save(_make_mock())
        repo.clear()
        assert await repo.count_for_backtest_run(uuid4()) == 0
