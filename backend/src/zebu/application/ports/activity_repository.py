"""ActivityRepository port — read-only contract for the unified activity feed.

Phase H2. The recent-activity feed at ``GET /api/v1/activity`` aggregates
rows from multiple writable tables (transactions, strategies, activations,
backtest_runs, exploration_tasks, api_keys) into a single chronological
stream. This port defines the contract that any activity reader must
satisfy — the SQLModel implementation does it via a multi-source UNION
query; an in-memory implementation could project from in-memory entity
collections.

The repository is intentionally read-only: every actor-tracking write
flows through the existing per-entity repositories (transaction, strategy,
etc.) which now stamp ``api_key_id`` on insert. This port only reads.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from zebu.application.dtos.activity_event_dto import (
    ActivityEventDTO,
    ActivityEventType,
)


@dataclass(frozen=True)
class ActivityFilter:
    """Filter / pagination params for an activity-feed query.

    Attributes:
        user_id: Owning user (Clerk-derived UUID). The feed is scoped to
            one user — admin cross-user views are out of scope for H2.
        limit: Max rows to return (1-200, validated at the API layer).
        offset: Number of rows to skip for pagination.
        since: Optional inclusive lower bound on ``occurred_at``. Rows
            older than this are excluded.
        actor_label: Optional API-key label filter — only rows whose
            ``api_key_id`` resolves to this label are returned. Useful
            when isolating one agent's activity. ``None`` returns all
            actors.
        event_types: Optional set of ``ActivityEventType`` values to
            include. Empty set / ``None`` means all types.
    """

    user_id: UUID
    limit: int
    offset: int
    since: datetime | None
    actor_label: str | None
    event_types: frozenset[ActivityEventType] | None


@dataclass(frozen=True)
class ActivityPage:
    """One page of activity events.

    Attributes:
        items: Events in DESC order by ``occurred_at``.
        total: Total matching rows across all pages (for the
            ``has_more`` calculation in ``PaginatedResponse``).
    """

    items: list[ActivityEventDTO]
    total: int


class ActivityRepository(Protocol):
    """Read-only port for the recent-activity feed."""

    async def list_events(self, filter_: ActivityFilter) -> ActivityPage:
        """Return one page of activity events matching the filter.

        Implementations MUST sort by ``occurred_at`` DESC (newest first)
        and apply ``limit`` / ``offset`` after the merge — the merge can
        produce more rows than ``limit`` from any single source so
        slicing too early would skip events that come from a different
        source.

        Args:
            filter_: Scoping / pagination parameters.

        Returns:
            ``ActivityPage`` containing the page of events plus the
            total matching-row count.
        """
        ...
