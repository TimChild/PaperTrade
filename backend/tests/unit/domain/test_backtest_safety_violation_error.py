"""Unit tests for :class:`BacktestSafetyViolationError` (Phase L-2 / Task #218).

Validates the exception subclass relationship (so L-3 can catch it via
``AgentInvocationError``), the carried fields (the L-3 executor reads
these onto :class:`BacktestAgentInvocation.rationale`), and the message
formatting.
"""

from __future__ import annotations

from datetime import date

import pytest

from zebu.domain.exceptions import (
    AgentInvocationError,
    BacktestSafetyViolationError,
    DomainException,
)


class TestBacktestSafetyViolationError:
    """Subclass relationship, attribute carry-through, message formatting."""

    def test_subclass_of_agent_invocation_error(self) -> None:
        """L-3 catches this via the broader :class:`AgentInvocationError` clause."""
        assert issubclass(BacktestSafetyViolationError, AgentInvocationError)

    def test_subclass_of_domain_exception(self) -> None:
        """All domain errors inherit from :class:`DomainException`."""
        assert issubclass(BacktestSafetyViolationError, DomainException)

    def test_carries_tool_name(self) -> None:
        exc = BacktestSafetyViolationError(
            tool_name="get_price_history",
            simulated_date=date(2024, 3, 15),
            reason="end date 2024-03-16 exceeds simulated_date",
        )
        assert exc.tool_name == "get_price_history"

    def test_carries_simulated_date(self) -> None:
        exc = BacktestSafetyViolationError(
            tool_name="get_price_history",
            simulated_date=date(2024, 3, 15),
            reason="violation",
        )
        assert exc.simulated_date == date(2024, 3, 15)

    def test_carries_reason(self) -> None:
        exc = BacktestSafetyViolationError(
            tool_name="get_price_history",
            simulated_date=date(2024, 3, 15),
            reason="end date 2024-03-16 exceeds simulated_date 2024-03-15",
        )
        assert exc.reason == "end date 2024-03-16 exceeds simulated_date 2024-03-15"

    def test_message_includes_tool_name(self) -> None:
        exc = BacktestSafetyViolationError(
            tool_name="web_search",
            simulated_date=date(2024, 3, 15),
            reason="not in BACKTEST_SAFE_TOOLS",
        )
        assert "'web_search'" in str(exc)
        assert "not in BACKTEST_SAFE_TOOLS" in str(exc)
        assert "2024-03-15" in str(exc)

    def test_message_when_tool_name_none(self) -> None:
        """``tool_name=None`` for non-tool-bound violations (defensive path)."""
        exc = BacktestSafetyViolationError(
            tool_name=None,
            simulated_date=date(2024, 3, 15),
            reason="unbound parameter check",
        )
        assert "Backtest safety violation" in str(exc)
        # Tool-name fragment is omitted entirely.
        assert "on tool" not in str(exc)

    def test_raisable_and_catchable_via_parent(self) -> None:
        """``except AgentInvocationError`` catches the subclass — L-3 relies on this."""
        with pytest.raises(AgentInvocationError):
            raise BacktestSafetyViolationError(
                tool_name="get_price_history",
                simulated_date=date(2024, 3, 15),
                reason="x",
            )

    def test_raisable_and_catchable_directly(self) -> None:
        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            raise BacktestSafetyViolationError(
                tool_name="get_portfolio_state",
                simulated_date=date(2025, 1, 1),
                reason="as_of 2025-01-02 exceeds simulated_date 2025-01-01",
            )
        assert exc_info.value.tool_name == "get_portfolio_state"
