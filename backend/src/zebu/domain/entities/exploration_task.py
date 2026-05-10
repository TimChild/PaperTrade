"""ExplorationTask entity — human-queued request for an agent to investigate.

The ``ExplorationTask`` is the primary input mechanism a human uses to direct
agent work in the Phase C/D agent platform. Humans create free-form prompts
("explore mean-reversion on AAPL/MSFT this quarter, watch FOMC reactions")
that agents claim, work, and submit findings against. See
``docs/planning/agent-platform-proposal.md`` §2 (the loop) and §3.4
(strategy authorability lanes) for the wider context.

Per resolved Q7, the prompt is **free-form from day one**; structured
``constraints`` are optional guardrails (e.g. "no live activation"), not the
primary input. ``findings`` are typed payloads agents submit when marking a
task DONE so the GUI can render results without parsing free-form text.

The entity enforces a small state machine:

    OPEN -> IN_PROGRESS -> DONE
              |
              `-> ABANDONED

OPEN -> ABANDONED is also allowed (a human cancelling an unclaimed task).
Once a task is DONE or ABANDONED it is terminal — no further transitions.

Invariants:

* ``status == IN_PROGRESS`` requires both ``claimed_by`` and ``claimed_at``.
* ``status == DONE`` requires ``findings`` (and the task must have been
  claimed first, so ``claimed_by`` and ``claimed_at`` are also non-null).
* ``status == ABANDONED`` keeps the historical claim metadata (so the
  audit trail records who walked away from the task) but does not require
  ``findings``.

The instance is immutable; transitions are performed by the helper methods
``claim``, ``complete``, ``abandon`` which return a new ``ExplorationTask``.
This matches the pattern used by ``BacktestRun`` and keeps the dataclass
fully ``frozen=True``.
"""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from zebu.domain.exceptions import InvalidEntityError
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker


class InvalidExplorationTaskError(InvalidEntityError):
    """Raised when ExplorationTask invariants are violated."""

    pass


class ExplorationTaskStatus(str, Enum):
    """Lifecycle status of an exploration task.

    Values:
        OPEN: Created by a human; available for any agent to claim.
        IN_PROGRESS: Claimed by an agent and being worked.
        DONE: Agent submitted findings and marked it complete.
        ABANDONED: The human (owner) cancelled it, or the agent gave up
            without findings. Terminal — keeps any prior claim metadata for
            audit purposes.
    """

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    ABANDONED = "ABANDONED"


@dataclass(frozen=True)
class ExplorationConstraints:
    """Optional structured guardrails attached to an exploration task.

    These are the limits a human wants the agent to respect while working
    the task. The free-form ``prompt`` is the primary input; constraints
    layer on top as machine-readable rules. All fields are optional — an
    instance with no fields populated is the default "no extra constraints"
    state.

    Attributes:
        max_backtests: If set, the agent should not run more than this many
            backtests while exploring. ``None`` means no cap.
        allow_live_activation: When ``True`` (the default), the agent may
            activate a strategy live on a portfolio if a variant looks
            good. When ``False``, the agent must stop after backtesting and
            present findings only — useful for read-only "research-only"
            tasks. Defaults to ``True`` so existing free-form prompts keep
            unrestricted authorisation; set to ``False`` to lock down a
            task.
        strategy_type_whitelist: If set, the agent should only consider
            these strategy types (e.g. ``[StrategyType.MOVING_AVERAGE_CROSSOVER]``
            for "MA-crossover only" tasks). ``None`` means any supported
            type is fair game.

    Raises:
        InvalidExplorationTaskError: If ``max_backtests`` is set to a
            value <= 0 (a zero or negative cap is meaningless).
    """

    max_backtests: int | None = None
    allow_live_activation: bool = True
    strategy_type_whitelist: list[StrategyType] | None = None

    def __post_init__(self) -> None:
        """Validate constraints invariants after initialization."""
        if self.max_backtests is not None and self.max_backtests <= 0:
            raise InvalidExplorationTaskError(
                f"max_backtests must be a positive integer if set, "
                f"got {self.max_backtests}"
            )
        if (
            self.strategy_type_whitelist is not None
            and len(self.strategy_type_whitelist) == 0
        ):
            raise InvalidExplorationTaskError(
                "strategy_type_whitelist must be None or a non-empty list"
            )


@dataclass(frozen=True)
class ExplorationFindingsMetrics:
    """Primary backtest metrics for the chosen candidate in a finding.

    Mirrors the metric naming on ``BacktestRun`` so an agent that ran a
    sweep can copy the winner's metrics directly. ``total_return_pct`` is
    the only required field — every other metric is optional because not
    every strategy / backtest produces it (e.g. a one-trade buy-and-hold
    has no meaningful Sharpe ratio).

    All percentage fields are stored as ``Decimal`` (e.g. ``Decimal("24.4")``
    means +24.4%, not 0.244) — same convention used on ``BacktestRun``.

    Attributes:
        total_return_pct: Total return over the backtest period, in percent.
            Required.
        sharpe_ratio: Annualised Sharpe ratio. Optional — short or
            single-trade backtests may not have a meaningful value.
        max_drawdown_pct: Maximum peak-to-trough drawdown over the period,
            in percent (typically negative or zero). Optional.
        n_trades: Number of buy/sell trades executed. Optional.
        annualized_return_pct: Annualised return over the period. Optional.

    Raises:
        InvalidExplorationTaskError: If ``n_trades`` is negative.
    """

    total_return_pct: Decimal
    sharpe_ratio: Decimal | None = None
    max_drawdown_pct: Decimal | None = None
    n_trades: int | None = None
    annualized_return_pct: Decimal | None = None

    def __post_init__(self) -> None:
        """Validate metric invariants after initialization."""
        if self.n_trades is not None and self.n_trades < 0:
            raise InvalidExplorationTaskError(
                f"ExplorationFindingsMetrics.n_trades cannot be negative, "
                f"got {self.n_trades}"
            )


@dataclass(frozen=True)
class ExplorationFindingsComparison:
    """Comparison of the chosen candidate to a baseline backtest.

    The baseline is typically a buy-and-hold run on the same tickers /
    period, but any backtest can serve as the baseline — the agent chooses.
    Deltas are signed: positive means the candidate outperforms the
    baseline on that metric.

    Attributes:
        baseline_strategy_id: Strategy ID of the baseline (typically a
            buy-and-hold strategy the agent created for comparison). The
            backtest run for the baseline should appear in the finding's
            ``backtest_run_ids`` so a reader can navigate to it.
        baseline_total_return_pct: The baseline's total return, in percent.
        delta_total_return_pct: Candidate's total return minus the
            baseline's. Positive = outperformed; negative = underperformed.
        delta_sharpe: Optional Sharpe-ratio delta. ``None`` means either
            the candidate or the baseline didn't have a Sharpe ratio.
    """

    baseline_strategy_id: UUID
    baseline_total_return_pct: Decimal
    delta_total_return_pct: Decimal
    delta_sharpe: Decimal | None = None


@dataclass(frozen=True)
class ExplorationFindings:
    """Typed payload an agent submits when completing an exploration task.

    The agent's narrative reasoning lives in ``summary``; structured
    references to the work it produced live in ``backtest_run_ids`` and
    ``strategy_ids``. Free-form ``notes`` lets the agent leave additional
    context (e.g. "tried 5 parameter sweeps, #3 had best Sharpe but #1 had
    lowest drawdown") that does not fit a single summary line.

    Phase E2 added structured fields for the most common agent output —
    parameter-sweep results — so the GUI can render the recommendation
    meaningfully instead of parsing the free-form summary. Every E2 field
    is optional; agents may submit just ``summary`` for narrative findings
    (negative results, free-form prose, no clear winner).

    Attributes:
        summary: Free-form narrative — the agent's primary writeup. Required
            (1–4000 chars). Surfaces directly in the human's GUI dashboard
            as the readable wrapper around the structured fields.
        backtest_run_ids: List of ``BacktestRun`` IDs the agent created
            while exploring. Empty list when no backtests were run (e.g. a
            "research-only" task whose findings are pure prose).
        strategy_ids: List of ``Strategy`` IDs the agent authored while
            exploring. Empty when no strategies were created.
        notes: Optional list of additional bullet-point observations.
            ``None`` (default) means "no extra notes"; an empty list is
            allowed and treated the same way.
        recommended_strategy_id: The chosen winner from the sweep. When
            set, this ID **should** also appear in ``strategy_ids`` (the
            entity raises if it doesn't, so the recommendation isn't
            dangling). ``None`` means "no clear winner / narrative finding".
        recommended_parameters: The chosen parameter combo for the
            recommended strategy. Free-form ``dict[str, Any]`` because
            the shape varies by strategy type (MA-crossover has
            ``fast_window``/``slow_window``/``invest_fraction``; DCA has
            ``frequency_days``/``amount_per_period``/``allocation``; etc.).
            ``Any`` is permitted here as a documented exception — see the
            class-level note.
        metrics: Primary backtest metrics for the recommended candidate.
            ``None`` when no candidate was recommended.
        comparison_to_baseline: Comparison of the recommended candidate
            to a baseline backtest (typically buy-and-hold on the same
            tickers/period). ``None`` when no baseline was run.
        confidence: Agent's qualitative confidence in the recommendation,
            in [0.0, 1.0]. Optional. ``None`` means "unspecified".

    Raises:
        InvalidExplorationTaskError: If ``summary`` is empty/whitespace,
            exceeds the 4000-character cap, ``confidence`` falls outside
            [0, 1], or ``recommended_strategy_id`` is set but does not
            appear in ``strategy_ids``.

    Note:
        ``recommended_parameters`` deliberately uses ``dict[str, Any]``.
        The parameter shape varies per strategy type and the value
        objects describing each shape live in
        ``zebu.domain.value_objects.strategy_parameters``. Encoding them
        here as a typed union would require keeping this entity in sync
        with every new strategy type — instead we forward the dict as-is.
        Callers that need a typed value should use ``parameters_from_dict``
        from the strategy_parameters module against the recommended
        strategy's type.
    """

    summary: str
    backtest_run_ids: list[UUID] = field(default_factory=list)
    strategy_ids: list[UUID] = field(default_factory=list)
    notes: list[str] | None = None
    recommended_strategy_id: UUID | None = None
    # ``Any`` is intentional here — see class docstring. Parameter shape
    # varies per strategy type; encoding the discriminated union would
    # couple the entity to every new strategy type added.
    recommended_parameters: dict[str, Any] | None = None
    metrics: ExplorationFindingsMetrics | None = None
    comparison_to_baseline: ExplorationFindingsComparison | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        """Validate findings invariants after initialization."""
        if not self.summary or not self.summary.strip():
            raise InvalidExplorationTaskError(
                "ExplorationFindings.summary cannot be empty or whitespace"
            )
        if len(self.summary) > 4000:
            raise InvalidExplorationTaskError(
                f"ExplorationFindings.summary must be at most 4000 characters, "
                f"got {len(self.summary)}"
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise InvalidExplorationTaskError(
                f"ExplorationFindings.confidence must be in [0.0, 1.0] if set, "
                f"got {self.confidence}"
            )
        if (
            self.recommended_strategy_id is not None
            and self.recommended_strategy_id not in self.strategy_ids
        ):
            raise InvalidExplorationTaskError(
                "ExplorationFindings.recommended_strategy_id must appear in "
                "strategy_ids — the recommendation cannot reference a "
                "strategy the finding doesn't list."
            )


_TERMINAL_STATUSES: frozenset[ExplorationTaskStatus] = frozenset(
    {ExplorationTaskStatus.DONE, ExplorationTaskStatus.ABANDONED}
)


@dataclass(frozen=True)
class ExplorationTask:
    """An exploration task queued by a human for an agent to work.

    See module docstring for the lifecycle and architectural context.

    Attributes:
        id: Unique task identifier.
        created_by: User ID of the human who created the task.
        prompt: Free-form natural-language description of what the human
            wants the agent to investigate. Required (1–4000 chars).
        target_portfolio_id: Optional portfolio for portfolio-specific
            exploration (e.g. "explore strategies for portfolio P"). When
            ``None``, the task is not bound to any single portfolio.
        tickers: Optional list of tickers the agent should focus on. Empty
            list / ``None`` means "any tickers" — fully free-form.
        constraints: Optional structured guardrails. ``None`` means no
            additional constraints beyond the prompt.
        status: Current lifecycle status.
        claimed_by: Agent identifier (free-form for now — could be an API
            key label, a Claude session ID, etc.) of whoever claimed the
            task. Required when ``status`` is IN_PROGRESS or DONE; allowed
            but not required for ABANDONED (a task can be abandoned before
            ever being claimed).
        claimed_at: Timestamp of when the task was claimed. Paired with
            ``claimed_by``.
        findings: Typed payload the agent submitted at completion.
            Required when ``status`` is DONE; otherwise ``None``.
        created_at: When the task was created.
        updated_at: When the task last transitioned. Set to ``created_at``
            on initial construction.

    Raises:
        InvalidExplorationTaskError: If any invariant is violated.
    """

    id: UUID
    created_by: UUID
    prompt: str
    status: ExplorationTaskStatus
    created_at: datetime
    updated_at: datetime
    target_portfolio_id: UUID | None = None
    tickers: list[Ticker] | None = None
    constraints: ExplorationConstraints | None = None
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    findings: ExplorationFindings | None = None

    def __post_init__(self) -> None:
        """Validate ExplorationTask invariants after initialization."""
        if not self.prompt or not self.prompt.strip():
            raise InvalidExplorationTaskError(
                "ExplorationTask.prompt cannot be empty or whitespace"
            )
        if len(self.prompt) > 4000:
            raise InvalidExplorationTaskError(
                f"ExplorationTask.prompt must be at most 4000 characters, "
                f"got {len(self.prompt)}"
            )

        if self.tickers is not None and len(self.tickers) > 50:
            raise InvalidExplorationTaskError(
                f"ExplorationTask.tickers must be at most 50 entries if set, "
                f"got {len(self.tickers)}"
            )

        # Status-specific invariants
        if self.status is ExplorationTaskStatus.IN_PROGRESS:
            if self.claimed_by is None or self.claimed_at is None:
                raise InvalidExplorationTaskError(
                    "ExplorationTask in IN_PROGRESS status must have both "
                    "claimed_by and claimed_at set"
                )
            if self.findings is not None:
                raise InvalidExplorationTaskError(
                    "ExplorationTask in IN_PROGRESS status must not have findings"
                )
        elif self.status is ExplorationTaskStatus.DONE:
            if self.claimed_by is None or self.claimed_at is None:
                raise InvalidExplorationTaskError(
                    "ExplorationTask in DONE status must retain claimed_by "
                    "and claimed_at from the IN_PROGRESS transition"
                )
            if self.findings is None:
                raise InvalidExplorationTaskError(
                    "ExplorationTask in DONE status requires findings"
                )
        elif self.status is ExplorationTaskStatus.OPEN:
            if self.claimed_by is not None or self.claimed_at is not None:
                raise InvalidExplorationTaskError(
                    "ExplorationTask in OPEN status must not have "
                    "claimed_by or claimed_at"
                )
            if self.findings is not None:
                raise InvalidExplorationTaskError(
                    "ExplorationTask in OPEN status must not have findings"
                )
        elif self.status is ExplorationTaskStatus.ABANDONED:
            # ABANDONED keeps any prior claim metadata for audit, so we do
            # not require claimed_by / claimed_at to be either set or unset.
            # findings are also not required (the task may have been
            # abandoned before any work was completed).
            pass

        # Timestamp invariants
        now = datetime.now(UTC)
        created_at_utc = (
            self.created_at
            if self.created_at.tzinfo is not None
            else self.created_at.replace(tzinfo=UTC)
        )
        if created_at_utc > now:
            raise InvalidExplorationTaskError(
                "ExplorationTask.created_at cannot be in the future"
            )

        updated_at_utc = (
            self.updated_at
            if self.updated_at.tzinfo is not None
            else self.updated_at.replace(tzinfo=UTC)
        )
        if updated_at_utc < created_at_utc:
            raise InvalidExplorationTaskError(
                "ExplorationTask.updated_at cannot be before created_at"
            )

        if self.claimed_at is not None:
            claimed_at_utc = (
                self.claimed_at
                if self.claimed_at.tzinfo is not None
                else self.claimed_at.replace(tzinfo=UTC)
            )
            if claimed_at_utc < created_at_utc:
                raise InvalidExplorationTaskError(
                    "ExplorationTask.claimed_at cannot be before created_at"
                )

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only.

        Args:
            other: Object to compare

        Returns:
            True if other is ExplorationTask with same ID
        """
        if not isinstance(other, ExplorationTask):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets.

        Returns:
            Hash of task ID
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "ExplorationTask(id=UUID('...'), status=OPEN)"
        """
        return (
            f"ExplorationTask(id={self.id}, status={self.status.value}, "
            f"created_by={self.created_by})"
        )

    @property
    def is_terminal(self) -> bool:
        """Whether the task has reached a terminal state (DONE or ABANDONED).

        Returns:
            True when no further transitions are allowed.
        """
        return self.status in _TERMINAL_STATUSES

    def claim(self, *, agent_id: str, claimed_at: datetime) -> "ExplorationTask":
        """Transition OPEN -> IN_PROGRESS.

        Args:
            agent_id: Identifier of the agent claiming the task.
                Free-form (could be an API-key label, a Claude session ID,
                etc.). Must be non-empty.
            claimed_at: Timestamp at which the claim happens.

        Returns:
            A new ExplorationTask with status=IN_PROGRESS, claimed_by and
            claimed_at populated, and updated_at set to ``claimed_at``.

        Raises:
            InvalidExplorationTaskError: If the current status is not OPEN
                or ``agent_id`` is empty/whitespace.
        """
        if self.status is not ExplorationTaskStatus.OPEN:
            raise InvalidExplorationTaskError(
                f"Cannot claim ExplorationTask in {self.status.value} status; "
                "only OPEN tasks can be claimed"
            )
        if not agent_id or not agent_id.strip():
            raise InvalidExplorationTaskError(
                "ExplorationTask.claim requires a non-empty agent_id"
            )

        return replace(
            self,
            status=ExplorationTaskStatus.IN_PROGRESS,
            claimed_by=agent_id,
            claimed_at=claimed_at,
            updated_at=claimed_at,
        )

    def complete(
        self, *, findings: ExplorationFindings, completed_at: datetime
    ) -> "ExplorationTask":
        """Transition IN_PROGRESS -> DONE with findings.

        Args:
            findings: Typed findings payload.
            completed_at: Timestamp of completion.

        Returns:
            A new ExplorationTask with status=DONE, findings populated,
            and updated_at set to ``completed_at``.

        Raises:
            InvalidExplorationTaskError: If the current status is not
                IN_PROGRESS.
        """
        if self.status is not ExplorationTaskStatus.IN_PROGRESS:
            raise InvalidExplorationTaskError(
                f"Cannot complete ExplorationTask in {self.status.value} "
                "status; only IN_PROGRESS tasks can be completed"
            )

        return replace(
            self,
            status=ExplorationTaskStatus.DONE,
            findings=findings,
            updated_at=completed_at,
        )

    def abandon(self, *, abandoned_at: datetime) -> "ExplorationTask":
        """Transition OPEN or IN_PROGRESS -> ABANDONED.

        Preserves any prior claim metadata for audit purposes.

        Args:
            abandoned_at: Timestamp of abandonment.

        Returns:
            A new ExplorationTask with status=ABANDONED and updated_at set
            to ``abandoned_at``.

        Raises:
            InvalidExplorationTaskError: If the current status is already
                terminal (DONE or ABANDONED).
        """
        if self.is_terminal:
            raise InvalidExplorationTaskError(
                f"Cannot abandon ExplorationTask in {self.status.value} "
                "status; task is already terminal"
            )

        return replace(
            self,
            status=ExplorationTaskStatus.ABANDONED,
            updated_at=abandoned_at,
        )
