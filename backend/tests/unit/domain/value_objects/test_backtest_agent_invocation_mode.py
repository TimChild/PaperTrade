"""Unit tests for :class:`BacktestAgentInvocationMode` (Phase L-1 / Task #217).

Mirrors the trigger-invocation-mode test (Task #213) — exercises enum
membership, lowercase wire serialisation, and round-trip semantics.
"""

from __future__ import annotations

import pytest

from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)


class TestBacktestAgentInvocationModeEnum:
    """Verify the StrEnum surface matches what the rest of the codebase expects."""

    def test_none_value_is_lowercase_string(self) -> None:
        """``NONE.value`` is the wire-shape lowercase token."""
        assert BacktestAgentInvocationMode.NONE.value == "none"

    def test_mock_value_is_lowercase_string(self) -> None:
        """``MOCK.value`` is the wire-shape lowercase token."""
        assert BacktestAgentInvocationMode.MOCK.value == "mock"

    def test_live_value_is_lowercase_string(self) -> None:
        """``LIVE.value`` is the wire-shape lowercase token."""
        assert BacktestAgentInvocationMode.LIVE.value == "live"

    def test_only_three_members(self) -> None:
        """No accidental fourth mode — keeps the dispatch table small."""
        assert set(BacktestAgentInvocationMode) == {
            BacktestAgentInvocationMode.NONE,
            BacktestAgentInvocationMode.MOCK,
            BacktestAgentInvocationMode.LIVE,
        }

    def test_str_enum_round_trips_via_value(self) -> None:
        """``BacktestAgentInvocationMode("none")`` round-trips from the wire string."""
        assert BacktestAgentInvocationMode("none") is BacktestAgentInvocationMode.NONE
        assert BacktestAgentInvocationMode("mock") is BacktestAgentInvocationMode.MOCK
        assert BacktestAgentInvocationMode("live") is BacktestAgentInvocationMode.LIVE

    def test_unknown_value_raises(self) -> None:
        """Drifted DB values surface loudly so the loader can map them to 422."""
        with pytest.raises(ValueError):
            BacktestAgentInvocationMode("offline")

    def test_string_comparison_works(self) -> None:
        """StrEnum members compare equal to their string values."""
        assert BacktestAgentInvocationMode.NONE == "none"
        assert BacktestAgentInvocationMode.MOCK == "mock"
        assert BacktestAgentInvocationMode.LIVE == "live"
