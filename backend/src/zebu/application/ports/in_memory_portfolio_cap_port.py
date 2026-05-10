"""In-memory ``PortfolioCapPort`` adapter — Phase F-6.

Stateful test fake. Callers explicitly seed the cap defaults and the
current per-portfolio counters; the cap evaluation runs over that state
without consulting any real persistence layer.

The production adapter
(:class:`zebu.adapters.outbound.database.portfolio_cap_adapter.PortfolioCapRepositoryAdapter`)
computes the same numbers by reading today's BUY/SELL transactions where
``api_key_id IS NOT NULL``. The contract is the same; the difference is
where the counters come from.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from zebu.application.ports.portfolio_cap_port import CapCheckResult
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.daily_trade_volume_cap import DailyTradeVolumeCap


@dataclass
class _PortfolioState:
    """Current-day cap state for one portfolio."""

    count: int
    value_usd: Decimal


class InMemoryPortfolioCapPort:
    """Test-time :class:`PortfolioCapPort` with explicit state injection.

    Two operating modes:

    1. **Default cap** — set once on construction; applied to every
       portfolio without an override.
    2. **Per-portfolio override** — call :meth:`set_cap` to give a
       specific portfolio its own ``DailyTradeVolumeCap``.

    Counter state starts at zero; tests seed it via :meth:`set_state`
    to simulate "this portfolio has already used $4500 of its $5000
    today" scenarios without having to thread real transactions through.

    Calling :meth:`check` with a BUY/SELL decision that fits the caps
    advances the internal counters as if the trade landed (consistent
    with the production adapter where the SQL read sees the new row on
    the next check).
    """

    def __init__(
        self,
        *,
        default_cap_count: int = 10,
        default_cap_value_usd: Decimal = Decimal("5000"),
    ) -> None:
        """Initialise with default cap values.

        Args:
            default_cap_count: Default per-portfolio BUY/SELL count cap.
            default_cap_value_usd: Default per-portfolio cumulative
                ``|cash_change|`` cap.
        """
        self._default_cap_count = default_cap_count
        self._default_cap_value_usd = default_cap_value_usd
        self._overrides: dict[UUID, DailyTradeVolumeCap] = {}
        self._state: dict[UUID, _PortfolioState] = {}

    def set_cap(self, cap: DailyTradeVolumeCap) -> None:
        """Override the cap for a specific portfolio."""
        self._overrides[cap.portfolio_id] = cap

    def set_state(
        self,
        *,
        portfolio_id: UUID,
        count: int,
        value_usd: Decimal,
    ) -> None:
        """Seed the current-day cap usage for a portfolio.

        Args:
            portfolio_id: Target portfolio.
            count: BUY/SELL transactions executed today.
            value_usd: Cumulative ``|cash_change|`` so far today.
        """
        self._state[portfolio_id] = _PortfolioState(
            count=count, value_usd=value_usd
        )

    def _cap_for(self, portfolio_id: UUID) -> tuple[int, Decimal]:
        """Resolve the cap pair for a portfolio (override → default)."""
        override = self._overrides.get(portfolio_id)
        if override is not None:
            return override.cap_count, override.cap_value_usd
        return self._default_cap_count, self._default_cap_value_usd

    async def check(
        self,
        *,
        portfolio_id: UUID,
        attempted_decision: AgentDecision,
        attempted_value_usd: Decimal,
    ) -> CapCheckResult:
        """Evaluate the cap; advance counters if the trade is allowed.

        Non-BUY/SELL decisions trivially allow (cap doesn't apply per
        §10 Q7) — the counters are not touched.
        """
        cap_count, cap_value_usd = self._cap_for(portfolio_id)
        state = self._state.get(
            portfolio_id, _PortfolioState(count=0, value_usd=Decimal("0"))
        )

        if attempted_decision not in (AgentDecision.BUY, AgentDecision.SELL):
            return CapCheckResult(
                allowed=True,
                reason=(
                    "cap does not apply to "
                    f"{attempted_decision.value}; only BUY/SELL"
                ),
                cap_count=cap_count,
                cap_value_usd=cap_value_usd,
                current_count=state.count,
                current_value_usd=state.value_usd,
            )

        new_count = state.count + 1
        new_value = state.value_usd + attempted_value_usd

        if new_count > cap_count:
            return CapCheckResult(
                allowed=False,
                reason=(
                    f"would breach {cap_count}-trade daily cap "
                    f"(current {state.count}, attempted +1)"
                ),
                cap_count=cap_count,
                cap_value_usd=cap_value_usd,
                current_count=state.count,
                current_value_usd=state.value_usd,
            )
        if new_value > cap_value_usd:
            return CapCheckResult(
                allowed=False,
                reason=(
                    f"would exceed daily cap of ${cap_value_usd} "
                    f"(current ${state.value_usd}, attempted "
                    f"${attempted_value_usd})"
                ),
                cap_count=cap_count,
                cap_value_usd=cap_value_usd,
                current_count=state.count,
                current_value_usd=state.value_usd,
            )

        # Allowed — advance the counter so the next check on the same
        # portfolio sees the new state, mirroring the production
        # adapter's "next SQL read sees the just-written row".
        self._state[portfolio_id] = _PortfolioState(
            count=new_count, value_usd=new_value
        )
        return CapCheckResult(
            allowed=True,
            reason=None,
            cap_count=cap_count,
            cap_value_usd=cap_value_usd,
            current_count=new_count,
            current_value_usd=new_value,
        )


__all__ = ["InMemoryPortfolioCapPort"]
