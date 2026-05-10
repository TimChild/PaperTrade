"""Unit tests for TriggerFireRecord entity (Phase F-1).

Covers:

* Construction-time invariants per Phase-F design §1.4:
  - latency_ms >= 0,
  - exactly one of resulting_trade_id / resulting_modify_payload /
    resulting_exploration_task_id set (UNLESS response is HOLD or
    INVOCATION_FAILED, then all three are null),
  - decision-specific cross-checks (BUY/SELL must point at trade,
    MODIFY_STRATEGY at payload, NEEDS_HUMAN at task).
* Append-only immutability (frozen).
* JSON-payload defensive copying.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from zebu.domain.entities.trigger_fire_record import TriggerFireRecord
from zebu.domain.exceptions import InvalidTriggerFireError
from zebu.domain.value_objects.agent_decision import AgentDecision


def _make_record(**overrides: object) -> TriggerFireRecord:
    """Factory for valid HOLD records — easy to mutate in tests."""
    defaults: dict[str, object] = {
        "id": uuid4(),
        "trigger_id": uuid4(),
        "activation_id": uuid4(),
        "fired_at": datetime.now(UTC) - timedelta(seconds=10),
        "condition_evaluation_data": {
            "schema_version": 1,
            "drawdown_pct": "5.5",
            "metric": "PORTFOLIO_TOTAL",
        },
        "agent_response": AgentDecision.HOLD,
        "agent_response_raw": "Holding — no clear signal.",
        "latency_ms": 1234,
        "api_key_id_used": uuid4(),
    }
    defaults.update(overrides)
    return TriggerFireRecord(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Happy paths — one per decision value
# ---------------------------------------------------------------------------


class TestHoldRecord:
    def test_hold_with_no_pointers_valid(self) -> None:
        """HOLD requires all three resulting_* pointers to be null."""
        record = _make_record()
        assert record.agent_response is AgentDecision.HOLD
        assert record.resulting_trade_id is None
        assert record.resulting_modify_payload is None
        assert record.resulting_exploration_task_id is None

    def test_hold_with_trade_id_raises(self) -> None:
        """HOLD must not have any resulting pointer set."""
        with pytest.raises(
            InvalidTriggerFireError, match="HOLD requires all resulting_"
        ):
            _make_record(resulting_trade_id=uuid4())


class TestInvocationFailedRecord:
    def test_invocation_failed_with_no_pointers_valid(self) -> None:
        """INVOCATION_FAILED requires all three resulting_* to be null."""
        record = _make_record(
            agent_response=AgentDecision.INVOCATION_FAILED,
            agent_response_raw="Anthropic API timeout",
        )
        assert record.agent_response is AgentDecision.INVOCATION_FAILED

    def test_invocation_failed_with_modify_payload_raises(self) -> None:
        with pytest.raises(
            InvalidTriggerFireError, match="INVOCATION_FAILED requires all"
        ):
            _make_record(
                agent_response=AgentDecision.INVOCATION_FAILED,
                resulting_modify_payload={"some": "payload"},
            )


class TestBuySellRecord:
    def test_buy_with_trade_id_valid(self) -> None:
        record = _make_record(
            agent_response=AgentDecision.BUY,
            resulting_trade_id=uuid4(),
        )
        assert record.agent_response is AgentDecision.BUY
        assert record.resulting_trade_id is not None

    def test_sell_with_trade_id_valid(self) -> None:
        record = _make_record(
            agent_response=AgentDecision.SELL,
            resulting_trade_id=uuid4(),
        )
        assert record.agent_response is AgentDecision.SELL

    def test_buy_without_any_pointer_raises(self) -> None:
        """BUY with no resulting_* set is rejected by cardinality first."""
        with pytest.raises(
            InvalidTriggerFireError,
            match="exactly one of",
        ):
            _make_record(agent_response=AgentDecision.BUY)

    def test_sell_with_wrong_pointer_raises(self) -> None:
        """SELL pointing at a modify_payload (not trade) is rejected.

        The cardinality check passes (exactly one set) but the
        decision-specific check then catches the wrong-pointer case.
        """
        with pytest.raises(
            InvalidTriggerFireError,
            match="SELL requires.*resulting_trade_id",
        ):
            _make_record(
                agent_response=AgentDecision.SELL,
                resulting_modify_payload={"x": 1},
            )

    def test_buy_with_modify_payload_raises_cardinality(self) -> None:
        """Two pointers populated -> cardinality violation."""
        with pytest.raises(InvalidTriggerFireError, match="exactly one of"):
            _make_record(
                agent_response=AgentDecision.BUY,
                resulting_trade_id=uuid4(),
                resulting_modify_payload={"x": 1},
            )


class TestModifyStrategyRecord:
    def test_modify_with_payload_valid(self) -> None:
        record = _make_record(
            agent_response=AgentDecision.MODIFY_STRATEGY,
            resulting_modify_payload={"invest_fraction": "0.25"},
        )
        assert record.agent_response is AgentDecision.MODIFY_STRATEGY
        assert record.resulting_modify_payload == {"invest_fraction": "0.25"}

    def test_modify_without_payload_raises(self) -> None:
        """MODIFY_STRATEGY with no resulting_* set is rejected.

        The cardinality check fires first (zero populated when one is
        required), so the error message is the cardinality one. The
        decision-specific check is a defence-in-depth layer that fires
        when exactly one IS populated but it's the wrong one.
        """
        with pytest.raises(
            InvalidTriggerFireError,
            match="exactly one of",
        ):
            _make_record(agent_response=AgentDecision.MODIFY_STRATEGY)

    def test_modify_with_wrong_pointer_raises(self) -> None:
        """MODIFY_STRATEGY pointing at a trade_id (not modify_payload) is rejected."""
        with pytest.raises(
            InvalidTriggerFireError,
            match="MODIFY_STRATEGY requires resulting_modify_payload",
        ):
            _make_record(
                agent_response=AgentDecision.MODIFY_STRATEGY,
                resulting_trade_id=uuid4(),
            )


class TestNeedsHumanRecord:
    def test_needs_human_with_exploration_task_id_valid(self) -> None:
        record = _make_record(
            agent_response=AgentDecision.NEEDS_HUMAN,
            resulting_exploration_task_id=uuid4(),
        )
        assert record.agent_response is AgentDecision.NEEDS_HUMAN

    def test_needs_human_without_task_id_raises(self) -> None:
        """NEEDS_HUMAN with no resulting_* set is rejected by cardinality."""
        with pytest.raises(
            InvalidTriggerFireError,
            match="exactly one of",
        ):
            _make_record(agent_response=AgentDecision.NEEDS_HUMAN)

    def test_needs_human_with_wrong_pointer_raises(self) -> None:
        """NEEDS_HUMAN pointing at a trade (not exploration_task) is rejected."""
        with pytest.raises(
            InvalidTriggerFireError,
            match="NEEDS_HUMAN requires resulting_exploration_task_id",
        ):
            _make_record(
                agent_response=AgentDecision.NEEDS_HUMAN,
                resulting_trade_id=uuid4(),
            )


# ---------------------------------------------------------------------------
# Numeric / timestamp invariants
# ---------------------------------------------------------------------------


class TestLatencyInvariants:
    def test_negative_latency_raises(self) -> None:
        with pytest.raises(InvalidTriggerFireError, match="latency_ms"):
            _make_record(latency_ms=-1)

    def test_zero_latency_valid(self) -> None:
        """Zero latency is unusual but possible (instant in-memory test)."""
        record = _make_record(latency_ms=0)
        assert record.latency_ms == 0

    def test_bool_latency_rejected(self) -> None:
        with pytest.raises(InvalidTriggerFireError):
            _make_record(latency_ms=True)


class TestRawBodyInvariants:
    def test_raw_body_too_long_raises(self) -> None:
        """Raw body must be capped at 8000 chars at write time."""
        with pytest.raises(
            InvalidTriggerFireError, match="agent_response_raw must be at most"
        ):
            _make_record(agent_response_raw="x" * 8001)

    def test_raw_body_exactly_8000_valid(self) -> None:
        record = _make_record(agent_response_raw="x" * 8000)
        assert len(record.agent_response_raw) == 8000


class TestFiredAtInvariants:
    def test_future_fired_at_raises(self) -> None:
        future = datetime.now(UTC) + timedelta(minutes=10)
        with pytest.raises(
            InvalidTriggerFireError, match="fired_at cannot be in the future"
        ):
            _make_record(fired_at=future)

    def test_naive_fired_at_treated_as_utc(self) -> None:
        """Naive datetime is accepted and normalised."""
        naive = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=5)
        record = _make_record(fired_at=naive)
        assert record.fired_at == naive


# ---------------------------------------------------------------------------
# JSON payload defensive copying
# ---------------------------------------------------------------------------


class TestPayloadDefensiveCopy:
    def test_condition_evaluation_data_is_copied(self) -> None:
        """Mutating the source dict after construction must not affect the record."""
        original = {"schema_version": 1, "drawdown_pct": "5.5"}
        record = _make_record(condition_evaluation_data=original)
        original["drawdown_pct"] = "TAMPERED"
        assert record.condition_evaluation_data["drawdown_pct"] == "5.5"

    def test_modify_payload_is_copied(self) -> None:
        original = {"invest_fraction": "0.5"}
        record = _make_record(
            agent_response=AgentDecision.MODIFY_STRATEGY,
            resulting_modify_payload=original,
        )
        original["invest_fraction"] = "TAMPERED"
        assert record.resulting_modify_payload is not None
        assert record.resulting_modify_payload["invest_fraction"] == "0.5"


# ---------------------------------------------------------------------------
# Identity, hashing, frozenness, repr
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_equality_by_id(self) -> None:
        same_id = uuid4()
        a = _make_record(id=same_id)
        b = _make_record(id=same_id, latency_ms=999)
        assert a == b

    def test_inequality_with_different_id(self) -> None:
        a = _make_record()
        b = _make_record()
        assert a != b

    def test_inequality_with_non_record(self) -> None:
        record = _make_record()
        assert record != "not a record"

    def test_hash_uses_id(self) -> None:
        record = _make_record()
        assert hash(record) == hash(record.id)

    def test_repr_includes_key_fields(self) -> None:
        record = _make_record()
        text = repr(record)
        assert str(record.id) in text
        assert "HOLD" in text
        assert "1234" in text  # latency


class TestFrozen:
    def test_cannot_mutate_agent_response(self) -> None:
        record = _make_record()
        with pytest.raises(FrozenInstanceError):
            record.agent_response = AgentDecision.BUY  # type: ignore[misc]

    def test_cannot_mutate_latency(self) -> None:
        record = _make_record()
        with pytest.raises(FrozenInstanceError):
            record.latency_ms = 5000  # type: ignore[misc]
