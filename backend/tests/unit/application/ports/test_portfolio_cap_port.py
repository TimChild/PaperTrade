"""Tests for :class:`InMemoryPortfolioCapPort` (Phase F-6).

Behaviour-focused — exercises the cap policy across counters at, below,
and above the configured limits. The in-memory implementation is the
test fake; the SQL adapter is covered by an integration test that
populates real transactions.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.application.ports.in_memory_portfolio_cap_port import (
    InMemoryPortfolioCapPort,
)
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.daily_trade_volume_cap import DailyTradeVolumeCap


class TestBuySellUnderCapAllowed:
    """A BUY/SELL whose value fits within both caps is permitted."""

    async def test_first_buy_under_count_and_value_cap_allowed(self) -> None:
        port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )
        result = await port.check(
            portfolio_id=uuid4(),
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("1000"),
        )
        assert result.allowed is True
        assert result.reason is None
        assert result.current_count == 1
        assert result.current_value_usd == Decimal("1000")

    async def test_sell_advances_same_counter(self) -> None:
        """BUY and SELL both count toward the same per-portfolio cap."""
        port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )
        pid = uuid4()
        await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("500"),
        )
        sell_result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.SELL,
            attempted_value_usd=Decimal("750"),
        )
        assert sell_result.allowed is True
        assert sell_result.current_count == 2
        assert sell_result.current_value_usd == Decimal("1250")


class TestCapAtBoundary:
    """The cap is inclusive — current + attempted == cap is allowed."""

    async def test_exact_value_cap_allowed(self) -> None:
        port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )
        pid = uuid4()
        port.set_state(portfolio_id=pid, count=2, value_usd=Decimal("4000"))
        result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("1000"),  # exactly hits 5000
        )
        assert result.allowed is True
        assert result.current_value_usd == Decimal("5000")

    async def test_exact_count_cap_allowed(self) -> None:
        port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )
        pid = uuid4()
        port.set_state(portfolio_id=pid, count=9, value_usd=Decimal("100"))
        result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("50"),  # 10th trade
        )
        assert result.allowed is True
        assert result.current_count == 10


class TestCapOverBoundaryDenied:
    """A request that would push past either cap is denied."""

    async def test_over_value_cap_denied_with_descriptive_reason(self) -> None:
        port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )
        pid = uuid4()
        port.set_state(portfolio_id=pid, count=2, value_usd=Decimal("4000"))
        result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("6000"),
        )
        assert result.allowed is False
        assert result.reason is not None
        assert "$5000" in result.reason
        assert "$4000" in result.reason
        # Counter is unchanged on a denied attempt.
        assert result.current_count == 2
        assert result.current_value_usd == Decimal("4000")

    async def test_over_count_cap_denied_with_descriptive_reason(self) -> None:
        port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("100000"),
        )
        pid = uuid4()
        port.set_state(portfolio_id=pid, count=10, value_usd=Decimal("1000"))
        result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.SELL,
            attempted_value_usd=Decimal("50"),
        )
        assert result.allowed is False
        assert result.reason is not None
        assert "10-trade daily cap" in result.reason
        assert result.current_count == 10


class TestModifyStrategyExempt:
    """MODIFY_STRATEGY / HOLD / NEEDS_HUMAN bypass the cap (§10 Q7)."""

    async def test_modify_strategy_bypasses_cap_even_at_value_limit(self) -> None:
        port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )
        pid = uuid4()
        # Portfolio is already at the value cap.
        port.set_state(portfolio_id=pid, count=2, value_usd=Decimal("5000"))
        result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.MODIFY_STRATEGY,
            attempted_value_usd=Decimal("999999"),
        )
        assert result.allowed is True
        # Counter unchanged — MODIFY doesn't consume cap quota.
        assert result.current_count == 2
        assert result.current_value_usd == Decimal("5000")

    async def test_hold_bypasses_cap(self) -> None:
        port = InMemoryPortfolioCapPort()
        pid = uuid4()
        port.set_state(portfolio_id=pid, count=50, value_usd=Decimal("999999"))
        result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.HOLD,
            attempted_value_usd=Decimal("0"),
        )
        assert result.allowed is True

    async def test_needs_human_bypasses_cap(self) -> None:
        port = InMemoryPortfolioCapPort()
        pid = uuid4()
        port.set_state(portfolio_id=pid, count=50, value_usd=Decimal("999999"))
        result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.NEEDS_HUMAN,
            attempted_value_usd=Decimal("0"),
        )
        assert result.allowed is True


class TestPerPortfolioOverrides:
    """set_cap() applies to a specific portfolio."""

    async def test_override_takes_precedence_over_default(self) -> None:
        port = InMemoryPortfolioCapPort(
            default_cap_count=10,
            default_cap_value_usd=Decimal("5000"),
        )
        pid = uuid4()
        port.set_cap(
            DailyTradeVolumeCap(
                portfolio_id=pid,
                cap_count=2,
                cap_value_usd=Decimal("500"),
            )
        )
        # Default would have allowed this; override should deny.
        result = await port.check(
            portfolio_id=pid,
            attempted_decision=AgentDecision.BUY,
            attempted_value_usd=Decimal("600"),
        )
        assert result.allowed is False
        assert result.cap_value_usd == Decimal("500")


class TestDailyTradeVolumeCapValidation:
    """Domain VO rejects invalid construction."""

    def test_zero_cap_count_rejected(self) -> None:
        with pytest.raises(ValueError, match="cap_count must be >= 1"):
            DailyTradeVolumeCap(
                portfolio_id=uuid4(),
                cap_count=0,
                cap_value_usd=Decimal("5000"),
            )

    def test_zero_cap_value_rejected(self) -> None:
        with pytest.raises(ValueError, match="cap_value_usd must be > 0"):
            DailyTradeVolumeCap(
                portfolio_id=uuid4(),
                cap_count=10,
                cap_value_usd=Decimal("0"),
            )
