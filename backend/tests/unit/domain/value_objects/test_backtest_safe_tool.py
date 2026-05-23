"""Unit tests for :class:`BacktestSafeTool` (Phase L-2 / Task #218).

Mirrors the surface of other StrEnum VOs (e.g.
:class:`BacktestAgentInvocationMode`) — enum membership, wire-string
values, round-trip semantics. The L-2 adapter relies on these values
matching the production MCP tool names, so the test enforces that
explicitly.
"""

from __future__ import annotations

import pytest

from zebu.domain.value_objects.backtest_safe_tool import (
    BACKTEST_SAFE_TOOL_NAMES,
    BacktestSafeTool,
)


class TestBacktestSafeTool:
    """Enum membership, wire strings, round-trip semantics."""

    def test_get_price_history_wire_value(self) -> None:
        assert BacktestSafeTool.GET_PRICE_HISTORY.value == "get_price_history"

    def test_get_portfolio_state_wire_value(self) -> None:
        assert BacktestSafeTool.GET_PORTFOLIO_STATE.value == "get_portfolio_state"

    def test_list_exploration_tasks_wire_value(self) -> None:
        assert BacktestSafeTool.LIST_EXPLORATION_TASKS.value == "list_exploration_tasks"

    def test_only_three_members(self) -> None:
        """The whitelist must stay tiny — any addition needs a spec update."""
        assert set(BacktestSafeTool) == {
            BacktestSafeTool.GET_PRICE_HISTORY,
            BacktestSafeTool.GET_PORTFOLIO_STATE,
            BacktestSafeTool.LIST_EXPLORATION_TASKS,
        }

    def test_str_enum_round_trips_via_value(self) -> None:
        """``BacktestSafeTool("get_price_history")`` round-trips from the wire."""
        assert (
            BacktestSafeTool("get_price_history") is BacktestSafeTool.GET_PRICE_HISTORY
        )
        assert (
            BacktestSafeTool("get_portfolio_state")
            is BacktestSafeTool.GET_PORTFOLIO_STATE
        )
        assert (
            BacktestSafeTool("list_exploration_tasks")
            is BacktestSafeTool.LIST_EXPLORATION_TASKS
        )

    def test_unknown_value_raises(self) -> None:
        """Defence in depth: any other tool name MUST be rejected."""
        with pytest.raises(ValueError):
            BacktestSafeTool("web_search")
        with pytest.raises(ValueError):
            BacktestSafeTool("get_current_price")  # banned — real-time leak

    def test_str_comparison_works(self) -> None:
        """StrEnum members compare equal to their wire strings."""
        assert BacktestSafeTool.GET_PRICE_HISTORY == "get_price_history"

    def test_safe_tool_names_tuple_matches_enum_values(self) -> None:
        """The pre-computed ``BACKTEST_SAFE_TOOL_NAMES`` tuple stays in sync."""
        assert BACKTEST_SAFE_TOOL_NAMES == (
            "get_price_history",
            "get_portfolio_state",
            "list_exploration_tasks",
        )
        assert set(BACKTEST_SAFE_TOOL_NAMES) == {t.value for t in BacktestSafeTool}
