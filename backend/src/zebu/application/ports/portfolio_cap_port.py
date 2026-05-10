"""Portfolio agent-trade volume cap port — Phase F-6.

Abstracts the "is this BUY/SELL within the per-portfolio per-day cap?"
check. The orchestrator calls this immediately before executing an
agent-driven trade; a deny downgrades the decision to HOLD with a
descriptive rationale captured on the :class:`TriggerFireRecord`.

References:
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §6.3 — cap shape +
  rationale.
- ``docs/architecture/phase-f-agent-in-the-loop.md`` §10 Q7 — BUY/SELL
  only (MODIFY_STRATEGY / HOLD / NEEDS_HUMAN bypass).
- ``docs/agents/operating-manual.md`` §4.2 — user-facing documentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from zebu.domain.value_objects.agent_decision import AgentDecision


@dataclass(frozen=True)
class CapCheckResult:
    """Result of a portfolio-cap check.

    Attributes:
        allowed: True when the attempted trade is within both ceilings;
            False when it would breach the count or value cap.
        reason: Human-readable reason when ``allowed=False``; populated
            with the binding limit ("would exceed daily cap of $5000",
            "would breach 10-trade daily cap"). ``None`` on allow.
        cap_count: The count ceiling applied during this check.
        cap_value_usd: The value ceiling applied during this check.
        current_count: BUY/SELL transactions executed for the portfolio
            so far today (UTC). Includes the attempted trade when
            ``allowed=True`` (cap was checked and passed); does NOT
            include it when denied (the attempt was rejected).
        current_value_usd: Cumulative ``|cash_change|`` for the
            portfolio so far today (UTC). Same inclusion semantics as
            ``current_count``.
    """

    allowed: bool
    reason: str | None
    cap_count: int
    cap_value_usd: Decimal
    current_count: int
    current_value_usd: Decimal


class PortfolioCapPort(Protocol):
    """Per-portfolio per-UTC-day cap for agent-initiated trades.

    Implementations:

    - ``PortfolioCapRepositoryAdapter`` (in
      ``zebu.adapters.outbound.database.portfolio_cap_adapter``) —
      production adapter that SUMs / COUNTs ``transactions`` rows where
      ``api_key_id IS NOT NULL`` (i.e. agent-initiated) for the
      portfolio over today's UTC window.
    - ``InMemoryPortfolioCapPort`` (in
      ``zebu.application.ports.in_memory_portfolio_cap_port``) — test
      fake with explicit state injection.

    Only BUY/SELL decisions need a cap check (§10 Q7). Callers must
    short-circuit other decision types BEFORE calling
    :meth:`check`. The port still accepts the decision for type-safety
    and to keep the audit trail symmetric — calling with a non-trade
    decision returns ``allowed=True`` with an "n/a" reason.
    """

    async def check(
        self,
        *,
        portfolio_id: UUID,
        attempted_decision: AgentDecision,
        attempted_value_usd: Decimal,
    ) -> CapCheckResult:
        """Check whether an attempted agent-driven trade fits the caps.

        The cap state is read fresh from the underlying store (no in-VM
        caching) so two concurrent fires on the same portfolio see each
        other's writes via the database — race-free up to Postgres
        snapshot-isolation semantics. For the in-memory test adapter the
        state is whatever's been seeded; the cap is enforced inclusively
        (``current + attempted <= cap`` is allowed, ``> cap`` denied).

        Args:
            portfolio_id: The portfolio the trade would land on.
            attempted_decision: The decision the agent emitted.
                Non-BUY/SELL decisions trivially allow (cap doesn't
                apply per §10 Q7).
            attempted_value_usd: Absolute USD cash impact of the
                attempted trade (``quantity * price_per_share``). The
                caller must pass an unsigned value — the cap sums
                ``|cash_change|``.

        Returns:
            :class:`CapCheckResult` carrying the post-check state. When
            denied, ``reason`` cites the binding limit so the
            orchestrator can capture it in the audit row.
        """
        ...


__all__ = [
    "CapCheckResult",
    "PortfolioCapPort",
]
