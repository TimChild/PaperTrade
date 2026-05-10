"""Recent-activity API route — Phase H2.

Exposes ``GET /api/v1/activity`` — a cross-table aggregator that blends
trades, strategy creations, backtest filings, activation lifecycle events,
exploration-task transitions, and API-key minting into a single
chronological feed.

The endpoint is read-only and per-user. Filtering by ``actor_label`` lets
the UI surface "what has agent X been doing?" while ``event_type``
filtering supports tab-style narrowing in the dashboard panel.

Authentication: any authenticated identity (Clerk Bearer or API key with
``read`` scope) sees their own activity. Cross-user / admin views are
out of scope for H2.
"""

from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from zebu.adapters.inbound.api.dependencies import (
    ApiKeyRepositoryDep,
    CurrentUserDep,
)
from zebu.adapters.inbound.api.schemas import (
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from zebu.adapters.inbound.api.schemas.pagination import build_paginated_response
from zebu.adapters.outbound.database.activity_repository import (
    SQLModelActivityRepository,
)
from zebu.application.dtos.activity_event_dto import (
    ActivityEventDTO,
    ActivityEventType,
    ActorKind,
    SubjectType,
)
from zebu.application.ports.activity_repository import (
    ActivityFilter,
    ActivityRepository,
)
from zebu.infrastructure.database import SessionDep

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])


# Phase H2 keeps the page cap at the platform-wide ``MAX_PAGE_LIMIT`` (100)
# rather than the task spec's suggested 200. ``PaginatedResponse`` validates
# its ``limit`` field at ``<=MAX_PAGE_LIMIT``, so bumping this cap requires
# a coordinated update to the envelope. The dashboard panel's typical page
# is 50 events; agents pulling history can paginate. Bumping to 200 is
# tracked as a follow-up.
ACTIVITY_MAX_LIMIT = MAX_PAGE_LIMIT
DEFAULT_ACTIVITY_LIMIT = 50


def get_activity_repository(
    session: SessionDep,
    api_key_repository: ApiKeyRepositoryDep,
) -> ActivityRepository:
    """Build a SQLModel-backed activity repository for this request.

    Args:
        session: Per-request DB session.
        api_key_repository: Repository for resolving api_key labels.
            Injected through the dependency so test fixtures swapping in
            an in-memory api-key adapter remain consistent.

    Returns:
        SQLModelActivityRepository conforming to the ActivityRepository
        protocol.
    """
    return SQLModelActivityRepository(session, api_key_repository=api_key_repository)


ActivityRepositoryDep = Annotated[ActivityRepository, Depends(get_activity_repository)]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ActivityEventResponse(BaseModel):
    """API response shape for a single activity event.

    Mirrors :class:`ActivityEventDTO` but with stringified timestamp +
    UUID fields for wire transport. The Pydantic model is what the
    OpenAPI schema is generated from.
    """

    type: ActivityEventType
    occurred_at: str = Field(
        description="ISO-8601 UTC timestamp at which the event happened.",
    )
    actor_kind: ActorKind
    actor_label: str | None = Field(
        default=None,
        description=(
            "Human-readable API-key label when ``actor_kind == 'api_key'``;"
            " ``null`` when ``actor_kind == 'user'`` (the UI renders that as"
            " 'you')."
        ),
    )
    actor_user_id: str = Field(
        description=(
            "Clerk-derived UUID of the owning user. Always present;"
            " preserved on the wire for future cross-user / admin views."
        ),
    )
    subject_type: SubjectType
    subject_id: str = Field(
        description=(
            "UUID of the underlying entity. The frontend uses this with"
            " ``subject_type`` to build the detail-page URL."
        ),
    )
    subject_name: str | None = Field(
        default=None,
        description=(
            "Optional display name for the subject (portfolio name,"
            " strategy name, backtest name, prompt summary, key label)."
        ),
    )
    summary: str = Field(
        description="Short human-readable line for the row's 'what happened' column.",
    )


def _to_response(event: ActivityEventDTO) -> ActivityEventResponse:
    """Convert an internal DTO into the wire response shape."""
    return ActivityEventResponse(
        type=event.type,
        occurred_at=event.occurred_at.isoformat(),
        actor_kind=event.actor_kind,
        actor_label=event.actor_label,
        actor_user_id=str(event.actor_user_id),
        subject_type=event.subject_type,
        subject_id=str(event.subject_id),
        subject_name=event.subject_name,
        summary=event.summary,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[ActivityEventResponse])
async def list_activity(
    user_id: CurrentUserDep,
    repo: ActivityRepositoryDep,
    limit: int = Query(
        default=DEFAULT_ACTIVITY_LIMIT,
        ge=1,
        le=ACTIVITY_MAX_LIMIT,
        description=(
            "Maximum number of events to return"
            f" (1-{ACTIVITY_MAX_LIMIT}, default {DEFAULT_ACTIVITY_LIMIT})."
        ),
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of events to skip for pagination (default 0).",
    ),
    since: Annotated[
        datetime | None,
        Query(
            description=(
                "Optional inclusive lower bound on ``occurred_at`` (ISO-8601)."
                " Events older than this are excluded."
            ),
        ),
    ] = None,
    actor_label: Annotated[
        str | None,
        Query(
            description=(
                "Optional API-key label filter — only rows whose API-key label"
                " matches are returned."
            ),
        ),
    ] = None,
    event_type: Annotated[
        list[ActivityEventType] | None,
        Query(
            description=(
                "Optional repeatable event-type filter."
                " Pass multiple values (``?event_type=trade&event_type=backtest``)"
                " to narrow the feed to specific kinds."
            ),
        ),
    ] = None,
) -> PaginatedResponse[ActivityEventResponse]:
    """Return a paginated activity feed for the authenticated user.

    The feed merges rows from multiple writable tables (transactions,
    strategies, activations, backtest_runs, exploration_tasks, api_keys)
    sorted DESC by ``occurred_at``. The actor identity column distinguishes
    Clerk-Bearer-authored rows ("you") from API-key-authored rows (the
    key's human label) so agent activity is visually separable from human
    activity at a glance.

    Args:
        user_id: Clerk-derived UUID of the authenticated user.
        repo: Activity repository (injected).
        limit: Page size.
        offset: Pagination offset.
        since: Optional ISO-8601 lower bound on event timestamps.
        actor_label: Optional API-key label filter.
        event_type: Optional repeatable event-type filter.

    Returns:
        ``PaginatedResponse[ActivityEventResponse]`` matching the standard
        list-endpoint envelope.
    """
    event_types = (
        frozenset(event_type) if event_type is not None and event_type else None
    )

    filter_ = ActivityFilter(
        user_id=user_id,
        limit=limit,
        offset=offset,
        since=since,
        actor_label=actor_label,
        event_types=event_types,
    )

    page = await repo.list_events(filter_)

    items = [_to_response(event) for event in page.items]

    logger.info(
        "Activity feed page returned",
        user_id=str(user_id),
        limit=limit,
        offset=offset,
        item_count=len(items),
        total=page.total,
        actor_label_filter=actor_label,
        event_type_filter=[t.value for t in (event_types or frozenset())] or None,
    )

    return build_paginated_response(
        items=items,
        total=page.total,
        limit=limit,
        offset=offset,
    )


__all__ = ["router", "get_activity_repository"]
