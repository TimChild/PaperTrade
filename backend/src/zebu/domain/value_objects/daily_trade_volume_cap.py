"""DailyTradeVolumeCap value object — Phase F-6.

Represents the hard platform-layer ceiling on agent-initiated trade
volume per portfolio per UTC day. Distinct from the per-API-key inbound
rate limiter (which gates ``run_backtest`` request frequency) and from
the operating-manual self-imposed soft caps (§4.2 — backtest count,
strategy count). The cap here bounds *cumulative paper-trade impact* so
a misbehaving agent can't drain a portfolio's cash in a single fire
cascade.

See ``docs/architecture/phase-f-agent-in-the-loop.md`` §6.3 for the
design rationale; §10 Q7 for the BUY/SELL-only scope decision; and
``docs/agents/operating-manual.md`` §4.2 for the user-facing
documentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class DailyTradeVolumeCap:
    """Per-portfolio per-UTC-day cap on agent-initiated trade volume.

    Two ceilings, both applied (whichever fires first denies):

    - ``cap_count``: maximum number of agent-initiated BUY/SELL
      transactions in a UTC day.
    - ``cap_value_usd``: maximum absolute cumulative cash impact (sum of
      ``|cash_change|`` across agent-initiated BUY/SELL transactions) in
      a UTC day. Always USD; mixed-currency portfolios are out of scope
      for v1 (the platform is USD-only today).

    Per design Q7, the cap applies *only to BUY and SELL* decisions.
    HOLD trivially passes (no trade), MODIFY_STRATEGY does not generate
    a transaction, and NEEDS_HUMAN files an ExplorationTask (also no
    transaction). So the cap is checked exactly when the orchestrator
    is about to call ``transaction_repo.save_all``.

    Attributes:
        portfolio_id: The portfolio the cap applies to. One cap per
            portfolio (the platform doesn't currently support
            per-strategy or per-symbol sub-caps).
        cap_count: Maximum BUY/SELL transactions per UTC day. ``>= 1``.
        cap_value_usd: Maximum cumulative ``|cash_change|`` per UTC day.
            ``> 0``. USD-only.
    """

    portfolio_id: UUID
    cap_count: int
    cap_value_usd: Decimal

    def __post_init__(self) -> None:
        """Validate invariants on construction."""
        if self.cap_count < 1:
            raise ValueError(
                f"cap_count must be >= 1; got {self.cap_count}"
            )
        if self.cap_value_usd <= Decimal("0"):
            raise ValueError(
                f"cap_value_usd must be > 0; got {self.cap_value_usd}"
            )


__all__ = ["DailyTradeVolumeCap"]
