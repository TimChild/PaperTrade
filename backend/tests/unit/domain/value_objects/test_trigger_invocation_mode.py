"""Unit tests for :class:`TriggerInvocationMode` (Phase J — Task #213)."""

from __future__ import annotations

import pytest

from zebu.domain.value_objects.trigger_invocation_mode import TriggerInvocationMode


class TestTriggerInvocationModeEnum:
    """Verify the StrEnum surface matches what the rest of the codebase expects."""

    def test_direct_value_is_lowercase_string(self) -> None:
        """``DIRECT.value`` is the wire-shape lowercase token."""
        assert TriggerInvocationMode.DIRECT.value == "direct"

    def test_queue_value_is_lowercase_string(self) -> None:
        """``QUEUE.value`` is the wire-shape lowercase token."""
        assert TriggerInvocationMode.QUEUE.value == "queue"

    def test_only_two_members(self) -> None:
        """No accidental third mode — keeps the dispatch table small."""
        assert set(TriggerInvocationMode) == {
            TriggerInvocationMode.DIRECT,
            TriggerInvocationMode.QUEUE,
        }

    def test_str_enum_round_trips_via_value(self) -> None:
        """``TriggerInvocationMode("direct")`` round-trips from the wire string."""
        assert TriggerInvocationMode("direct") is TriggerInvocationMode.DIRECT
        assert TriggerInvocationMode("queue") is TriggerInvocationMode.QUEUE

    def test_unknown_value_raises(self) -> None:
        """Drifted DB values surface loudly so the loader can map them to 422."""
        with pytest.raises(ValueError):
            TriggerInvocationMode("inline")

    def test_string_comparison_works(self) -> None:
        """StrEnum members compare equal to their string values (matches other VOs)."""
        assert TriggerInvocationMode.DIRECT == "direct"
        assert TriggerInvocationMode.QUEUE == "queue"
