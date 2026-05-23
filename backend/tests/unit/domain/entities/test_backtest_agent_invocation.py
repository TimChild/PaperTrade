"""Unit tests for :class:`BacktestAgentInvocation` (Phase L-1 / Task #217).

Covers:

* Identity, hashing, repr.
* Each entity invariant raises :class:`InvalidBacktestAgentInvocationError`.
* Per-mode cross-checks (MOCK / LIVE) — the entity is permissive only
  where the spec says so.
* JSON payload defensive copying.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from zebu.domain.entities.backtest_agent_invocation import BacktestAgentInvocation
from zebu.domain.exceptions import (
    InvalidBacktestAgentInvocationError,
    InvalidEntityError,
)
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_mock(**overrides: Any) -> BacktestAgentInvocation:
    """Factory for a valid MOCK-mode invocation row."""
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "backtest_run_id": uuid4(),
        "simulated_date": date(2024, 6, 1),
        "trigger_id": uuid4(),
        "condition_evaluation_data": {
            "schema_version": 1,
            "drawdown_pct": "5.5",
        },
        "rationale": "",
        "latency_ms": 0,
        "model": "",
        "invocation_mode": BacktestAgentInvocationMode.MOCK,
        "created_at": datetime.now(UTC) - timedelta(seconds=5),
        "agent_decision": None,
        "decision_payload": None,
        "decision_executed": False,
        "simulated_trade_id": None,
        "agent_invocation_id": None,
    }
    defaults.update(overrides)
    return BacktestAgentInvocation(**defaults)


def _make_live(**overrides: Any) -> BacktestAgentInvocation:
    """Factory for a valid LIVE-mode HOLD invocation row."""
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "backtest_run_id": uuid4(),
        "simulated_date": date(2024, 6, 1),
        "trigger_id": uuid4(),
        "condition_evaluation_data": {
            "schema_version": 1,
            "drawdown_pct": "5.5",
        },
        "agent_decision": AgentDecision.HOLD,
        "rationale": "Decided to hold given lack of catalyst.",
        "decision_payload": {"notes": "no clear signal"},
        "decision_executed": False,
        "simulated_trade_id": None,
        "invocation_mode": BacktestAgentInvocationMode.LIVE,
        "agent_invocation_id": "msg_01abc",
        "latency_ms": 1234,
        "model": "claude-haiku-4-5-20251001",
        "created_at": datetime.now(UTC) - timedelta(seconds=2),
    }
    defaults.update(overrides)
    return BacktestAgentInvocation(**defaults)


# ---------------------------------------------------------------------------
# Identity & immutability
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_equality_is_id_based(self) -> None:
        """Equality is by ``id`` only, not field-by-field."""
        shared = uuid4()
        a = _make_mock(id=shared)
        b = _make_mock(id=shared, simulated_date=date(2024, 6, 2))
        assert a == b

    def test_different_ids_not_equal(self) -> None:
        a = _make_mock()
        b = _make_mock()
        assert a != b

    def test_hash_is_id_based(self) -> None:
        shared = uuid4()
        a = _make_mock(id=shared)
        b = _make_mock(id=shared)
        assert hash(a) == hash(b)

    def test_frozen_dataclass_blocks_mutation(self) -> None:
        record = _make_mock()
        with pytest.raises(FrozenInstanceError):
            record.rationale = "mutated"  # type: ignore[misc]

    def test_repr_contains_key_fields(self) -> None:
        record = _make_live()
        text = repr(record)
        assert "BacktestAgentInvocation" in text
        assert str(record.id) in text
        assert record.simulated_date.isoformat() in text
        assert "HOLD" in text


# ---------------------------------------------------------------------------
# Cross-mode invariants
# ---------------------------------------------------------------------------


class TestSharedInvariants:
    def test_latency_ms_negative_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="latency_ms"):
            _make_live(latency_ms=-1)

    def test_latency_ms_bool_raises(self) -> None:
        """``True`` is technically an int — reject the foot-gun."""
        with pytest.raises(InvalidBacktestAgentInvocationError, match="latency_ms"):
            _make_live(latency_ms=True)

    def test_rationale_too_long_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="rationale"):
            _make_live(rationale="x" * 8001)

    def test_model_too_long_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="model"):
            _make_live(model="m" * 101)

    def test_created_at_naive_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="created_at"):
            _make_live(created_at=datetime.now())

    def test_condition_data_must_be_mapping(self) -> None:
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="condition_evaluation_data"
        ):
            _make_live(condition_evaluation_data=["not", "a", "mapping"])  # type: ignore[arg-type]

    def test_condition_data_is_defensively_copied(self) -> None:
        """Mutating the caller's dict after construction must not affect the row."""
        payload: dict[str, object] = {"schema_version": 1, "metric": "PRICE"}
        record = _make_live(condition_evaluation_data=payload)
        payload["metric"] = "DRAWDOWN"
        assert record.condition_evaluation_data["metric"] == "PRICE"

    def test_decision_payload_defensively_copied(self) -> None:
        payload: dict[str, object] = {"notes": "first"}
        record = _make_live(decision_payload=payload)
        payload["notes"] = "second"
        assert record.decision_payload is not None
        assert record.decision_payload["notes"] == "first"

    def test_decision_payload_must_be_mapping(self) -> None:
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="decision_payload"
        ):
            _make_live(decision_payload=["not", "a", "mapping"])  # type: ignore[arg-type]

    def test_invocation_mode_none_raises(self) -> None:
        """``NONE`` is a run-level concept; no audit row should carry it."""
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="invocation_mode=NONE"
        ):
            _make_live(invocation_mode=BacktestAgentInvocationMode.NONE)


# ---------------------------------------------------------------------------
# MOCK-mode invariants
# ---------------------------------------------------------------------------


class TestMockMode:
    def test_mock_with_none_decision_valid(self) -> None:
        record = _make_mock(agent_decision=None)
        assert record.agent_decision is None
        assert record.invocation_mode is BacktestAgentInvocationMode.MOCK

    def test_mock_with_hold_decision_valid(self) -> None:
        record = _make_mock(agent_decision=AgentDecision.HOLD)
        assert record.agent_decision is AgentDecision.HOLD

    def test_mock_with_non_hold_decision_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="MOCK"):
            _make_mock(agent_decision=AgentDecision.BUY)

    def test_mock_with_decision_payload_raises(self) -> None:
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="decision_payload"
        ):
            _make_mock(decision_payload={"some": "data"})

    def test_mock_with_nonempty_rationale_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="rationale"):
            _make_mock(rationale="hello")

    def test_mock_with_nonempty_model_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="model"):
            _make_mock(model="claude-haiku")

    def test_mock_with_positive_latency_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="latency"):
            _make_mock(latency_ms=100)

    def test_mock_with_invocation_id_raises(self) -> None:
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="agent_invocation_id"
        ):
            _make_mock(agent_invocation_id="msg_01abc")

    def test_mock_with_decision_executed_raises(self) -> None:
        # decision_executed=True triggers the global cross-check first
        # (decision_executed=True requires LIVE mode), so check the
        # global guard message.
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="decision_executed=True"
        ):
            _make_mock(decision_executed=True)


# ---------------------------------------------------------------------------
# LIVE-mode invariants
# ---------------------------------------------------------------------------


class TestLiveMode:
    def test_live_with_decision_and_model_valid(self) -> None:
        record = _make_live()
        assert record.agent_decision is AgentDecision.HOLD
        assert record.model != ""

    def test_live_without_decision_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="agent_decision"):
            _make_live(agent_decision=None)

    def test_live_with_empty_model_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="model"):
            _make_live(model="")

    def test_live_with_empty_rationale_and_non_failed_decision_raises(self) -> None:
        with pytest.raises(InvalidBacktestAgentInvocationError, match="rationale"):
            _make_live(rationale="")

    def test_live_with_invocation_failed_allows_empty_rationale(self) -> None:
        record = _make_live(
            agent_decision=AgentDecision.INVOCATION_FAILED,
            rationale="",
            decision_payload=None,
        )
        assert record.agent_decision is AgentDecision.INVOCATION_FAILED
        assert record.rationale == ""

    def test_live_allows_null_invocation_id(self) -> None:
        """Transport error before the SDK assigned a message id."""
        record = _make_live(agent_invocation_id=None)
        assert record.agent_invocation_id is None


# ---------------------------------------------------------------------------
# decision_executed cross-checks
# ---------------------------------------------------------------------------


class TestDecisionExecuted:
    def test_executed_buy_in_live_valid(self) -> None:
        record = _make_live(
            agent_decision=AgentDecision.BUY,
            decision_payload={"ticker": "AAPL", "notes": "catalyst"},
            decision_executed=True,
            simulated_trade_id=uuid4(),
        )
        assert record.decision_executed is True

    def test_executed_sell_in_live_valid(self) -> None:
        record = _make_live(
            agent_decision=AgentDecision.SELL,
            decision_payload={"ticker": "AAPL", "notes": "exit"},
            decision_executed=True,
            simulated_trade_id=uuid4(),
        )
        assert record.decision_executed is True

    def test_executed_modify_in_live_valid(self) -> None:
        record = _make_live(
            agent_decision=AgentDecision.MODIFY_STRATEGY,
            decision_payload={
                "parameter_overrides": {"ma_period": 50},
                "notes": "tighten",
            },
            decision_executed=True,
        )
        assert record.decision_executed is True

    def test_executed_hold_raises(self) -> None:
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="decision_executed=True"
        ):
            _make_live(
                agent_decision=AgentDecision.HOLD,
                decision_executed=True,
            )

    def test_executed_needs_human_raises(self) -> None:
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="decision_executed=True"
        ):
            _make_live(
                agent_decision=AgentDecision.NEEDS_HUMAN,
                decision_payload={"summary": "Need help", "urgency": "low"},
                decision_executed=True,
            )

    def test_executed_invocation_failed_raises(self) -> None:
        with pytest.raises(
            InvalidBacktestAgentInvocationError, match="decision_executed=True"
        ):
            _make_live(
                agent_decision=AgentDecision.INVOCATION_FAILED,
                rationale="",
                decision_executed=True,
            )


# ---------------------------------------------------------------------------
# Optional trigger_id / orphan recovery
# ---------------------------------------------------------------------------


class TestTriggerOrphan:
    def test_trigger_id_can_be_none(self) -> None:
        """``ON DELETE SET NULL`` on the FK — entity must accept the recovered state."""
        record = _make_live(trigger_id=None)
        assert record.trigger_id is None


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_subclasses_invalid_entity_error(self) -> None:
        """Catching ``InvalidEntityError`` should also catch ours."""
        try:
            _make_live(latency_ms=-1)
        except InvalidEntityError:
            pass
        else:
            pytest.fail("Expected InvalidEntityError (or subclass) to be raised")
