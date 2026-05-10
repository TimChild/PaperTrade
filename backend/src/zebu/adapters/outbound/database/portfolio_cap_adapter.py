"""SQL adapter for :class:`PortfolioCapPort` — Phase F-6.

Reads agent-initiated BUY/SELL transactions for the portfolio in today's
UTC window and applies the configured caps. Agent-initiated is defined
as ``api_key_id IS NOT NULL`` — i.e. any write that authenticated via
the API-key path. Clerk Bearer writes (humans through the UI) have
``api_key_id IS NULL`` and are excluded; the cap only governs machine
identities.

The agent-trade cap defaults (10 trades, $5000 cumulative) are passed in
at construction time — typically resolved from env at the FastAPI
dependency layer. Per-portfolio overrides are not wired in v1 (one cap
for the whole platform); a future enhancement can layer them on without
breaking the port contract.

See ``docs/architecture/phase-f-agent-in-the-loop.md`` §6.3 for the
design rationale and §10 Q7 for the BUY/SELL-only scope.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import TransactionModel
from zebu.application.ports.portfolio_cap_port import CapCheckResult
from zebu.domain.entities.transaction import TransactionType
from zebu.domain.value_objects.agent_decision import AgentDecision


class PortfolioCapRepositoryAdapter:
    """SQL :class:`PortfolioCapPort` adapter.

    On each :meth:`check` call:

    1. Compute today's UTC day boundary (00:00:00 UTC of the current day
       to start-of-tomorrow). Transactions are compared by their
       ``timestamp`` column (the wall-clock time the trade occurred),
       not by ``created_at``.
    2. SUM ``ABS(cash_change_amount)`` and COUNT(*) over BUY/SELL
       transactions on the portfolio where ``api_key_id IS NOT NULL``
       within that window.
    3. Compare ``current + attempted`` against the configured caps and
       return :class:`CapCheckResult`.

    The SQL is a single round-trip per check — one ``SELECT
    SUM(...) AS s, COUNT(*) AS c FROM transactions WHERE ...``. The
    transactions table already has ``idx_transaction_portfolio_id`` and
    ``idx_transaction_portfolio_timestamp`` covering this query shape.

    Attributes:
        cap_count: Maximum BUY/SELL transactions per UTC day. Read from
            env via the dependency layer; passed in at construction.
        cap_value_usd: Maximum cumulative ``|cash_change|`` per UTC day.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        cap_count: int,
        cap_value_usd: Decimal,
    ) -> None:
        """Initialise the adapter.

        Args:
            session: Async DB session for the unit of work.
            cap_count: Per-portfolio BUY/SELL count ceiling.
            cap_value_usd: Per-portfolio cumulative ``|cash_change|``
                ceiling. Always USD.
        """
        self._session = session
        self.cap_count = cap_count
        self.cap_value_usd = cap_value_usd

    async def check(
        self,
        *,
        portfolio_id: UUID,
        attempted_decision: AgentDecision,
        attempted_value_usd: Decimal,
    ) -> CapCheckResult:
        """Evaluate the cap against today's agent-trade volume.

        Non-BUY/SELL decisions trivially allow — the cap doesn't apply
        per design Q7. The query is still issued for current_count /
        current_value_usd so the audit can show "this trade was checked,
        but the decision type was exempt."
        """
        current_count, current_value_usd = await self._fetch_today_state(
            portfolio_id=portfolio_id
        )

        if attempted_decision not in (AgentDecision.BUY, AgentDecision.SELL):
            return CapCheckResult(
                allowed=True,
                reason=(
                    "cap does not apply to "
                    f"{attempted_decision.value}; only BUY/SELL"
                ),
                cap_count=self.cap_count,
                cap_value_usd=self.cap_value_usd,
                current_count=current_count,
                current_value_usd=current_value_usd,
            )

        new_count = current_count + 1
        new_value = current_value_usd + attempted_value_usd

        if new_count > self.cap_count:
            return CapCheckResult(
                allowed=False,
                reason=(
                    f"would breach {self.cap_count}-trade daily cap "
                    f"(current {current_count}, attempted +1)"
                ),
                cap_count=self.cap_count,
                cap_value_usd=self.cap_value_usd,
                current_count=current_count,
                current_value_usd=current_value_usd,
            )
        if new_value > self.cap_value_usd:
            return CapCheckResult(
                allowed=False,
                reason=(
                    f"would exceed daily cap of ${self.cap_value_usd} "
                    f"(current ${current_value_usd}, attempted "
                    f"${attempted_value_usd})"
                ),
                cap_count=self.cap_count,
                cap_value_usd=self.cap_value_usd,
                current_count=current_count,
                current_value_usd=current_value_usd,
            )

        return CapCheckResult(
            allowed=True,
            reason=None,
            cap_count=self.cap_count,
            cap_value_usd=self.cap_value_usd,
            current_count=current_count,
            current_value_usd=current_value_usd,
        )

    async def _fetch_today_state(
        self, *, portfolio_id: UUID
    ) -> tuple[int, Decimal]:
        """Return (count, |sum cash_change|) for today's agent-driven trades."""
        now = datetime.now(UTC)
        day_start_utc = datetime.combine(now.date(), time.min, tzinfo=UTC)
        day_end_utc = day_start_utc + timedelta(days=1)

        # Postgres TIMESTAMP WITHOUT TIME ZONE — strip tzinfo (matches
        # the way TransactionModel.from_domain stores them).
        day_start_naive = day_start_utc.replace(tzinfo=None)
        day_end_naive = day_end_utc.replace(tzinfo=None)

        # SUM(ABS(...)) over BUY/SELL trades stamped with an api_key_id
        # gives today's agent-initiated cumulative cash impact. The
        # ``type: ignore`` are noise stemming from SQLModel's column
        # descriptors not exposing SQLAlchemy's column methods to the
        # type checker.
        abs_sum = func.coalesce(  # type: ignore[arg-type]
            func.sum(func.abs(TransactionModel.cash_change_amount)),
            0,
        )
        statement = (
            select(func.count(), abs_sum)
            .select_from(TransactionModel)
            .where(
                TransactionModel.portfolio_id == portfolio_id,
                TransactionModel.api_key_id.is_not(None),  # type: ignore[union-attr]
                TransactionModel.transaction_type.in_(  # type: ignore[union-attr]
                    [TransactionType.BUY.value, TransactionType.SELL.value]
                ),
                TransactionModel.timestamp >= day_start_naive,
                TransactionModel.timestamp < day_end_naive,
            )
        )
        result = await self._session.exec(statement)
        row = result.one()
        count_val, sum_val = row
        # ``COUNT`` always returns an int; ``COALESCE(SUM, 0)`` always
        # returns a numeric (the COALESCE guarantees non-null). Cast to
        # ensure the return types match the protocol (int, Decimal).
        count_int = int(count_val)
        value_dec = Decimal(str(sum_val)) if sum_val is not None else Decimal("0")
        return count_int, value_dec


__all__ = ["PortfolioCapRepositoryAdapter"]
