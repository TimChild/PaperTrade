"""Smoke tests for the TriggerStatus enum (Phase F-1).

The state-machine transitions are tested on
:class:`StrategyConditionTrigger` itself; this file covers the enum's
shape (StrEnum, value strings) and the ``ValueError`` adapter-side
guardrail relied on when stored rows drift from the enum.
"""

import pytest

from zebu.domain.value_objects.trigger_status import TriggerStatus


class TestTriggerStatus:
    def test_str_enum_round_trip(self) -> None:
        """StrEnum stores its value as the string."""
        assert TriggerStatus.ACTIVE.value == "ACTIVE"
        assert TriggerStatus.PAUSED.value == "PAUSED"
        assert TriggerStatus.EXPIRED.value == "EXPIRED"
        assert TriggerStatus.MANUALLY_DISABLED.value == "MANUALLY_DISABLED"

    def test_construct_from_string(self) -> None:
        """``TriggerStatus("ACTIVE")`` round-trips back to the enum value."""
        assert TriggerStatus("ACTIVE") is TriggerStatus.ACTIVE
        assert TriggerStatus("MANUALLY_DISABLED") is TriggerStatus.MANUALLY_DISABLED

    def test_unknown_string_raises_value_error(self) -> None:
        """Adapter relies on this — drifted rows surface as ValueError."""
        with pytest.raises(ValueError):
            TriggerStatus("NOT_A_REAL_STATUS")
