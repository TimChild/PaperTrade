"""Unit tests for StrategyConditionTrigger entity (Phase F-1).

Covers:

* Construction-time invariant checks (status / condition pairing,
  cooldown, priority, prompt length, timestamp invariants).
* Lifecycle transitions (pause / resume / disable / expire / record_fire)
  including the immutable-replacement pattern.
* Derived predicates (is_terminal, is_in_cooldown, is_evaluable).
* Identity / hashing / repr.

The state machine described in the design doc §1.3 is the load-bearing
shape — make sure each transition is checked from each legal start
state and rejected from each illegal one.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.domain.entities.strategy_condition_trigger import (
    StrategyConditionTrigger,
)
from zebu.domain.exceptions import InvalidTriggerError
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    DrawdownParams,
    VolatilityParams,
)
from zebu.domain.value_objects.trigger_invocation_mode import TriggerInvocationMode
from zebu.domain.value_objects.trigger_status import TriggerStatus


def _make_trigger(**overrides: object) -> StrategyConditionTrigger:
    """Factory for valid ACTIVE DRAWDOWN_THRESHOLD triggers."""
    now = datetime.now(UTC) - timedelta(minutes=1)
    defaults: dict[str, object] = {
        "id": uuid4(),
        "activation_id": uuid4(),
        "user_id": uuid4(),
        "condition_type": ConditionType.DRAWDOWN_THRESHOLD,
        "condition_params": DrawdownParams(
            threshold_pct=Decimal("5"),
            lookback_days=30,
        ),
        "agent_prompt": "Decide whether to hold based on news context",
        "status": TriggerStatus.ACTIVE,
        "created_at": now,
        "updated_at": now,
        "created_by": uuid4(),
    }
    defaults.update(overrides)
    return StrategyConditionTrigger(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_minimal_valid_construction(self) -> None:
        """All defaults take effect: priority=0, cooldown=21600, expires=None."""
        trigger = _make_trigger()
        assert trigger.status is TriggerStatus.ACTIVE
        assert trigger.priority == 0
        assert trigger.cooldown_seconds == 21600
        assert trigger.last_fired_at is None
        assert trigger.expires_at is None
        assert trigger.default_api_key_id is None

    def test_with_full_optional_payload(self) -> None:
        """Every optional field accepts a value."""
        api_key_id = uuid4()
        now = datetime.now(UTC) - timedelta(seconds=30)
        trigger = _make_trigger(
            cooldown_seconds=600,
            priority=50,
            default_api_key_id=api_key_id,
            expires_at=now + timedelta(days=30),
        )
        assert trigger.cooldown_seconds == 600
        assert trigger.priority == 50
        assert trigger.default_api_key_id == api_key_id
        assert trigger.expires_at is not None

    def test_condition_type_mismatch_raises(self) -> None:
        """DRAWDOWN_THRESHOLD type with VolatilityParams must reject."""
        with pytest.raises(
            InvalidTriggerError, match="condition_params type does not match"
        ):
            _make_trigger(
                condition_type=ConditionType.VOLATILITY_SPIKE,
                # Still passing DrawdownParams here.
            )

    def test_volatility_with_volatility_params(self) -> None:
        """Correct pairing for VOLATILITY_SPIKE works."""
        trigger = _make_trigger(
            condition_type=ConditionType.VOLATILITY_SPIKE,
            condition_params=VolatilityParams(
                threshold_pct=Decimal("40"),
                over_days=20,
            ),
        )
        assert trigger.condition_type is ConditionType.VOLATILITY_SPIKE


class TestPromptInvariants:
    """agent_prompt: 10–4000 chars after trimming."""

    def test_prompt_too_short_raises(self) -> None:
        with pytest.raises(InvalidTriggerError, match="at least 10"):
            _make_trigger(agent_prompt="too short")

    def test_prompt_only_whitespace_raises(self) -> None:
        with pytest.raises(InvalidTriggerError, match="at least 10"):
            _make_trigger(agent_prompt="   " * 100)  # whitespace only

    def test_prompt_too_long_raises(self) -> None:
        with pytest.raises(InvalidTriggerError, match="at most 4000"):
            _make_trigger(agent_prompt="x" * 4001)

    def test_prompt_exactly_4000_valid(self) -> None:
        trigger = _make_trigger(agent_prompt="x" * 4000)
        assert len(trigger.agent_prompt) == 4000

    def test_prompt_with_leading_whitespace_counts_after_strip(self) -> None:
        """Prompt length is checked AFTER stripping whitespace.

        ``"     short"`` is 10 chars total but only 5 after strip, so
        the entity rejects it with the "at least 10" error.
        """
        with pytest.raises(InvalidTriggerError, match="at least 10"):
            _make_trigger(agent_prompt="     short")


class TestCooldownInvariants:
    def test_negative_cooldown_raises(self) -> None:
        with pytest.raises(InvalidTriggerError, match="cooldown_seconds"):
            _make_trigger(cooldown_seconds=-1)

    def test_zero_cooldown_valid(self) -> None:
        """Zero is a legitimate "fire on every tick" choice."""
        trigger = _make_trigger(cooldown_seconds=0)
        assert trigger.cooldown_seconds == 0

    def test_bool_cooldown_rejected(self) -> None:
        with pytest.raises(InvalidTriggerError):
            _make_trigger(cooldown_seconds=True)


class TestPriorityInvariants:
    @pytest.mark.parametrize("priority", [-101, -200, 101, 1000])
    def test_priority_out_of_range_raises(self, priority: int) -> None:
        with pytest.raises(InvalidTriggerError, match="priority"):
            _make_trigger(priority=priority)

    @pytest.mark.parametrize("priority", [-100, -50, 0, 50, 100])
    def test_priority_in_range_valid(self, priority: int) -> None:
        trigger = _make_trigger(priority=priority)
        assert trigger.priority == priority


class TestTimestampInvariants:
    def test_future_created_at_raises(self) -> None:
        future = datetime.now(UTC) + timedelta(minutes=10)
        with pytest.raises(
            InvalidTriggerError, match="created_at cannot be in the future"
        ):
            _make_trigger(created_at=future, updated_at=future)

    def test_updated_before_created_raises(self) -> None:
        now = datetime.now(UTC) - timedelta(minutes=1)
        with pytest.raises(InvalidTriggerError, match="updated_at cannot be before"):
            _make_trigger(
                created_at=now,
                updated_at=now - timedelta(minutes=10),
            )

    def test_last_fired_before_created_raises(self) -> None:
        now = datetime.now(UTC) - timedelta(minutes=1)
        with pytest.raises(InvalidTriggerError, match="last_fired_at cannot be before"):
            _make_trigger(
                created_at=now,
                updated_at=now,
                last_fired_at=now - timedelta(hours=1),
            )

    def test_last_fired_in_future_raises(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(
            InvalidTriggerError, match="last_fired_at cannot be in the future"
        ):
            _make_trigger(
                created_at=now - timedelta(minutes=5),
                updated_at=now - timedelta(minutes=4),
                last_fired_at=now + timedelta(minutes=10),
            )

    def test_expires_at_before_created_raises(self) -> None:
        now = datetime.now(UTC) - timedelta(minutes=1)
        with pytest.raises(
            InvalidTriggerError, match="expires_at must be strictly after"
        ):
            _make_trigger(
                created_at=now,
                updated_at=now,
                expires_at=now - timedelta(seconds=1),
            )

    def test_naive_datetimes_treated_as_utc(self) -> None:
        """Naive datetimes accepted and normalised to UTC."""
        naive_now = datetime.now(UTC).replace(tzinfo=None)
        trigger = _make_trigger(
            created_at=naive_now - timedelta(minutes=2),
            updated_at=naive_now - timedelta(minutes=1),
            last_fired_at=naive_now,
        )
        assert trigger.last_fired_at is not None


class TestExpiredStatusInvariant:
    def test_expired_without_expires_at_raises(self) -> None:
        """EXPIRED status requires expires_at to be set."""
        with pytest.raises(InvalidTriggerError, match="EXPIRED trigger must have"):
            _make_trigger(status=TriggerStatus.EXPIRED)

    def test_expired_with_future_expires_at_raises(self) -> None:
        """EXPIRED requires expires_at <= now."""
        future = datetime.now(UTC) + timedelta(days=10)
        with pytest.raises(
            InvalidTriggerError, match="EXPIRED trigger must have expires_at <="
        ):
            _make_trigger(
                status=TriggerStatus.EXPIRED,
                expires_at=future,
            )

    def test_expired_with_lapsed_expires_at_valid(self) -> None:
        """EXPIRED with a past expires_at is valid."""
        now = datetime.now(UTC) - timedelta(minutes=10)
        past = datetime.now(UTC) - timedelta(seconds=5)
        trigger = _make_trigger(
            created_at=now,
            updated_at=now,
            status=TriggerStatus.EXPIRED,
            expires_at=past,
        )
        assert trigger.status is TriggerStatus.EXPIRED


# ---------------------------------------------------------------------------
# State machine — pause / resume / disable / expire / record_fire
# ---------------------------------------------------------------------------


class TestPauseResume:
    def test_pause_active_trigger(self) -> None:
        """ACTIVE -> PAUSED."""
        trigger = _make_trigger()
        when = datetime.now(UTC)
        paused = trigger.pause(at=when)
        assert paused.status is TriggerStatus.PAUSED
        assert paused.updated_at == when
        # Original instance unchanged (immutable).
        assert trigger.status is TriggerStatus.ACTIVE

    def test_pause_already_paused_raises(self) -> None:
        trigger = _make_trigger().pause(at=datetime.now(UTC))
        with pytest.raises(
            InvalidTriggerError, match="only ACTIVE triggers can be paused"
        ):
            trigger.pause(at=datetime.now(UTC))

    def test_resume_paused_trigger(self) -> None:
        """PAUSED -> ACTIVE."""
        trigger = _make_trigger().pause(at=datetime.now(UTC))
        resumed = trigger.resume(at=datetime.now(UTC))
        assert resumed.status is TriggerStatus.ACTIVE

    def test_resume_active_raises(self) -> None:
        trigger = _make_trigger()
        with pytest.raises(
            InvalidTriggerError, match="only PAUSED triggers can be resumed"
        ):
            trigger.resume(at=datetime.now(UTC))


class TestDisable:
    def test_disable_active_trigger(self) -> None:
        """ACTIVE -> MANUALLY_DISABLED."""
        trigger = _make_trigger()
        disabled = trigger.disable(at=datetime.now(UTC))
        assert disabled.status is TriggerStatus.MANUALLY_DISABLED

    def test_disable_paused_trigger(self) -> None:
        """PAUSED -> MANUALLY_DISABLED is allowed."""
        trigger = _make_trigger().pause(at=datetime.now(UTC))
        disabled = trigger.disable(at=datetime.now(UTC))
        assert disabled.status is TriggerStatus.MANUALLY_DISABLED

    def test_disable_terminal_raises(self) -> None:
        trigger = _make_trigger().disable(at=datetime.now(UTC))
        with pytest.raises(InvalidTriggerError, match="already terminal"):
            trigger.disable(at=datetime.now(UTC))


class TestExpire:
    def test_expire_active_trigger(self) -> None:
        """ACTIVE -> EXPIRED when expires_at has lapsed."""
        now = datetime.now(UTC) - timedelta(seconds=30)
        # Make the trigger with a past expires_at; it must not be EXPIRED
        # at construction (we'd need expires_at <= now AND status to be
        # EXPIRED; constructing with status=ACTIVE + lapsed expires_at is
        # legal — the entity does not enforce the lapse on ACTIVE; the
        # evaluator triggers the transition).
        past = datetime.now(UTC) - timedelta(seconds=10)
        trigger = _make_trigger(
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=10),
            expires_at=past,
        )
        expired = trigger.expire(at=datetime.now(UTC))
        assert expired.status is TriggerStatus.EXPIRED

    def test_expire_without_expires_at_raises(self) -> None:
        trigger = _make_trigger()
        with pytest.raises(InvalidTriggerError, match="without an expires_at"):
            trigger.expire(at=datetime.now(UTC))

    def test_expire_before_expires_at_raises(self) -> None:
        future = datetime.now(UTC) + timedelta(days=10)
        trigger = _make_trigger(expires_at=future)
        with pytest.raises(InvalidTriggerError, match="Cannot expire trigger before"):
            trigger.expire(at=datetime.now(UTC))

    def test_expire_terminal_raises(self) -> None:
        trigger = _make_trigger().disable(at=datetime.now(UTC))
        with pytest.raises(InvalidTriggerError, match="already terminal"):
            trigger.expire(at=datetime.now(UTC))


class TestRecordFire:
    def test_record_fire_updates_last_fired_at(self) -> None:
        trigger = _make_trigger()
        when = datetime.now(UTC)
        fired = trigger.record_fire(fired_at=when)
        assert fired.last_fired_at == when
        assert fired.updated_at == when
        # Status unchanged.
        assert fired.status is TriggerStatus.ACTIVE

    def test_record_fire_subsequent_fire_advances_timestamp(self) -> None:
        """A second fire updates last_fired_at to the new timestamp."""
        trigger = _make_trigger()
        first = trigger.record_fire(fired_at=datetime.now(UTC) - timedelta(seconds=20))
        when = datetime.now(UTC)
        second = first.record_fire(fired_at=when)
        assert second.last_fired_at == when


# ---------------------------------------------------------------------------
# Derived predicates
# ---------------------------------------------------------------------------


class TestIsTerminal:
    def test_active_not_terminal(self) -> None:
        assert _make_trigger().is_terminal is False

    def test_paused_not_terminal(self) -> None:
        trigger = _make_trigger().pause(at=datetime.now(UTC))
        assert trigger.is_terminal is False

    def test_expired_terminal(self) -> None:
        past = datetime.now(UTC) - timedelta(seconds=10)
        trigger = _make_trigger(
            status=TriggerStatus.EXPIRED,
            expires_at=past,
            created_at=datetime.now(UTC) - timedelta(minutes=10),
            updated_at=datetime.now(UTC) - timedelta(minutes=10),
        )
        assert trigger.is_terminal is True

    def test_manually_disabled_terminal(self) -> None:
        trigger = _make_trigger().disable(at=datetime.now(UTC))
        assert trigger.is_terminal is True


class TestCooldown:
    def test_no_last_fired_means_no_cooldown(self) -> None:
        trigger = _make_trigger()
        assert trigger.is_in_cooldown(at=datetime.now(UTC)) is False

    def test_recently_fired_in_cooldown(self) -> None:
        trigger = _make_trigger(cooldown_seconds=300)
        when = datetime.now(UTC)
        fired = trigger.record_fire(fired_at=when)
        # 30 seconds after fire — still in cooldown.
        assert fired.is_in_cooldown(at=when + timedelta(seconds=30)) is True

    def test_cooldown_lapsed(self) -> None:
        # Need an old enough trigger so last_fired_at can also be old.
        old = datetime.now(UTC) - timedelta(minutes=10)
        trigger = _make_trigger(
            cooldown_seconds=60,
            created_at=old,
            updated_at=old,
        )
        # last_fired_at = 120s ago — cooldown is 60s, so it has lapsed.
        when = datetime.now(UTC) - timedelta(seconds=120)
        fired = trigger.record_fire(fired_at=when)
        assert fired.is_in_cooldown(at=datetime.now(UTC)) is False

    def test_zero_cooldown_never_in_cooldown(self) -> None:
        """zero cooldown means the trigger is always immediately re-evaluable."""
        trigger = _make_trigger(cooldown_seconds=0)
        fired = trigger.record_fire(fired_at=datetime.now(UTC))
        assert (
            fired.is_in_cooldown(at=datetime.now(UTC) + timedelta(milliseconds=1))
            is False
        )


class TestIsEvaluable:
    def test_active_no_cooldown_no_expiry_evaluable(self) -> None:
        trigger = _make_trigger()
        assert trigger.is_evaluable(at=datetime.now(UTC)) is True

    def test_paused_not_evaluable(self) -> None:
        trigger = _make_trigger().pause(at=datetime.now(UTC))
        assert trigger.is_evaluable(at=datetime.now(UTC)) is False

    def test_in_cooldown_not_evaluable(self) -> None:
        trigger = _make_trigger(cooldown_seconds=300)
        when = datetime.now(UTC)
        fired = trigger.record_fire(fired_at=when)
        assert fired.is_evaluable(at=when + timedelta(seconds=30)) is False

    def test_past_expires_at_not_evaluable(self) -> None:
        past = datetime.now(UTC) - timedelta(seconds=10)
        trigger = _make_trigger(
            created_at=datetime.now(UTC) - timedelta(minutes=10),
            updated_at=datetime.now(UTC) - timedelta(minutes=10),
            expires_at=past,
        )
        assert trigger.is_evaluable(at=datetime.now(UTC)) is False

    def test_terminal_not_evaluable(self) -> None:
        trigger = _make_trigger().disable(at=datetime.now(UTC))
        assert trigger.is_evaluable(at=datetime.now(UTC)) is False


# ---------------------------------------------------------------------------
# Identity, hashing, frozenness, repr
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_equality_by_id(self) -> None:
        same_id = uuid4()
        a = _make_trigger(id=same_id)
        b = _make_trigger(id=same_id, agent_prompt="something different")
        assert a == b

    def test_inequality_with_different_id(self) -> None:
        a = _make_trigger()
        b = _make_trigger()
        assert a != b

    def test_inequality_with_non_trigger(self) -> None:
        trigger = _make_trigger()
        assert trigger != "not a trigger"
        assert trigger != object()

    def test_hash_uses_id(self) -> None:
        trigger = _make_trigger()
        assert hash(trigger) == hash(trigger.id)
        # Usable as a set member.
        assert {trigger, trigger} == {trigger}

    def test_repr_contains_key_fields(self) -> None:
        trigger = _make_trigger()
        text = repr(trigger)
        assert str(trigger.id) in text
        assert "DRAWDOWN_THRESHOLD" in text
        assert "ACTIVE" in text


class TestFrozen:
    def test_cannot_mutate_status(self) -> None:
        trigger = _make_trigger()
        with pytest.raises(FrozenInstanceError):
            trigger.status = TriggerStatus.PAUSED  # type: ignore[misc]

    def test_cannot_mutate_priority(self) -> None:
        trigger = _make_trigger()
        with pytest.raises(FrozenInstanceError):
            trigger.priority = 50  # type: ignore[misc]


class TestInvocationMode:
    """Phase J / Task #213 — ``mode`` field defaults to DIRECT and round-trips."""

    def test_default_mode_is_direct(self) -> None:
        """Backwards compatibility — every pre-Phase-J trigger reads as DIRECT."""
        trigger = _make_trigger()
        assert trigger.mode is TriggerInvocationMode.DIRECT

    def test_explicit_direct_mode(self) -> None:
        trigger = _make_trigger(mode=TriggerInvocationMode.DIRECT)
        assert trigger.mode is TriggerInvocationMode.DIRECT

    def test_explicit_queue_mode(self) -> None:
        trigger = _make_trigger(mode=TriggerInvocationMode.QUEUE)
        assert trigger.mode is TriggerInvocationMode.QUEUE

    def test_mode_is_frozen(self) -> None:
        trigger = _make_trigger()
        with pytest.raises(FrozenInstanceError):
            trigger.mode = TriggerInvocationMode.QUEUE  # type: ignore[misc]
