"""StrategyActivation entity - links a Strategy to a Portfolio for live execution.

A StrategyActivation expresses the user's intent that a saved ``Strategy`` should
execute on a schedule against a specific ``Portfolio``. The entity is the
bookkeeping record the live-execution scheduler reads from each cycle: it tracks
which strategies are running, when they last ran, and any failures.

This entity is the foundation of Phase C1 of the agent-platform proposal — the
scheduler job (Phase C1.2) and API endpoints (Phase C1.3) operate on instances
of this entity. See ``agent_docs/tasks/210_live_strategy_execution.md`` for the
full feature plan.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from zebu.domain.exceptions import InvalidStrategyActivationError
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyActivation:
    """Represents a user's intent to execute a strategy on a recurring schedule.

    A ``StrategyActivation`` is the persistent record of "this user wants this
    strategy to run against this portfolio". The scheduler queries the
    repository for activations with ``status == ACTIVE`` each cycle and runs
    them; the result of each run mutates ``last_executed_at`` (and possibly
    ``last_error``/``status`` on failure).

    The entity is fully immutable — to "update" an activation, callers
    construct a new instance with the desired field values and persist it.
    Equality and hashing are based on ``id`` only so activations work in sets
    and as dict keys.

    Attributes:
        id: Unique activation identifier.
        user_id: Owner of the activation. Not enforced via FK in the database
            (users live in Clerk, not Postgres) but the field is required so
            list_for_user() can scope queries.
        strategy_id: FK to ``strategies.id``. Cascade-deletes with the strategy.
        portfolio_id: FK to ``portfolios.id``. Cascade-deletes with the
            portfolio.
        status: Current lifecycle state. See :class:`ActivationStatus` for the
            informal state machine.
        frequency: Execution cadence. Phase C1.1 ships only
            ``DAILY_MARKET_CLOSE`` but the enum is forward-compatible.
        last_executed_at: Timestamp of the most recent execution attempt
            (success or failure). ``None`` until the first run completes.
        last_error: Human-readable failure reason. Should be set when
            ``status == ERROR``; a warning is logged otherwise. ``None`` for
            healthy activations.
        created_at: When the activation was first created (UTC).
        updated_at: When the activation was last mutated (UTC). Must be ``>=``
            ``created_at``.

    Raises:
        InvalidStrategyActivationError: If any invariant is violated
            (mismatched status/frequency types, ``updated_at < created_at``,
            ``status == ERROR`` with no ``last_error``, etc.).
    """

    id: UUID
    user_id: UUID
    strategy_id: UUID
    portfolio_id: UUID
    status: ActivationStatus
    frequency: ActivationFrequency
    created_at: datetime
    updated_at: datetime
    last_executed_at: datetime | None = None
    last_error: str | None = None

    def __post_init__(self) -> None:
        """Validate StrategyActivation invariants after initialization."""
        # Note: ``status`` and ``frequency`` are typed as ``ActivationStatus`` /
        # ``ActivationFrequency``. Strict type-checking enforces this at every
        # construction site; the adapter layer (``StrategyActivationModel.to_domain``)
        # uses ``ActivationStatus(...)`` / ``ActivationFrequency(...)`` which
        # raise ``ValueError`` if a stored value drifts from the enum. So no
        # runtime isinstance guard is needed here.

        # Time invariant: updated_at cannot precede created_at.
        if self.updated_at < self.created_at:
            raise InvalidStrategyActivationError(
                f"updated_at ({self.updated_at!r}) cannot be before created_at "
                f"({self.created_at!r})"
            )

        # Both timestamps cannot be in the future.
        now = datetime.now(UTC)
        created_at_aware = (
            self.created_at
            if self.created_at.tzinfo is not None
            else self.created_at.replace(tzinfo=UTC)
        )
        if created_at_aware > now:
            raise InvalidStrategyActivationError("created_at cannot be in the future")

        # If we have a last_executed_at, sanity-check it sits in the activation's
        # lifetime: not before created_at, not in the future. This catches
        # construction bugs (e.g. wrong timestamp passed for the wrong field)
        # before they leak into reporting.
        if self.last_executed_at is not None:
            last_aware = (
                self.last_executed_at
                if self.last_executed_at.tzinfo is not None
                else self.last_executed_at.replace(tzinfo=UTC)
            )
            if last_aware < created_at_aware:
                raise InvalidStrategyActivationError(
                    "last_executed_at cannot be before created_at"
                )
            if last_aware > now:
                raise InvalidStrategyActivationError(
                    "last_executed_at cannot be in the future"
                )

        # Soft invariant: ERROR status should be paired with a last_error
        # message so the user / operator has something to act on. We warn
        # rather than raise — recovering from a corrupted DB row should be
        # possible without bypassing validation.
        if self.status is ActivationStatus.ERROR and not self.last_error:
            _logger.warning(
                "StrategyActivation %s has status=ERROR but no last_error message",
                self.id,
            )

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only.

        Args:
            other: Object to compare.

        Returns:
            True if other is StrategyActivation with the same ID.
        """
        if not isinstance(other, StrategyActivation):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets.

        Returns:
            Hash of activation ID.
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like
            ``StrategyActivation(id=..., strategy_id=..., status=ACTIVE)``.
        """
        return (
            f"StrategyActivation(id={self.id}, strategy_id={self.strategy_id}, "
            f"status={self.status.value})"
        )
