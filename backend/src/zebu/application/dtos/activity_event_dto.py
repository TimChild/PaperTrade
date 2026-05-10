"""ActivityEvent DTO — Phase H2 unified activity feed entry.

The recent-activity feed at ``GET /api/v1/activity`` aggregates rows from
multiple writable tables (``transactions``, ``strategies``,
``strategy_activations``, ``backtest_runs``, ``exploration_tasks``,
``api_keys``) into a single chronological stream. Each row is projected
into this DTO before serialisation.

The ``actor_kind`` / ``actor_label`` distinction is the load-bearing one
for the UI: rows authored via Clerk Bearer (a human in the browser) carry
``actor_kind="user"`` and ``actor_label=None``; rows authored via API key
(an agent / scheduled task / MCP server) carry ``actor_kind="api_key"``
and the human-readable ``actor_label`` from the ``api_keys`` table. The
frontend renders the label so Tim can distinguish his own activity from
agent activity at a glance.

The DTO is a frozen dataclass (immutable) with primitive / serialisable
field types, ready to be wrapped in a Pydantic response model by the
inbound API layer.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class ActivityEventType(str, Enum):
    """Discriminator for the kind of underlying event a row represents.

    The values mirror the ``event_type`` query parameter accepted by the
    ``GET /api/v1/activity`` endpoint. Adding a new value is a wire
    addition — clients that don't recognise it should degrade gracefully
    by displaying the raw string.
    """

    TRADE = "trade"
    """A buy or sell transaction (NOT deposits/withdrawals — those would
    flood the feed with non-decision noise)."""

    BACKTEST = "backtest"
    """A backtest_run row was created (the run was filed)."""

    STRATEGY_CREATED = "strategy_created"
    """A new Strategy entity was persisted."""

    ACTIVATION_CREATED = "activation_created"
    """A StrategyActivation was created (live execution turned on)."""

    ACTIVATION_RUN = "activation_run"
    """An activation's last_executed_at fired — i.e. the strategy ran for
    the day. Surfaced because Tim wants to see "did the strategy actually
    execute?" without diving into the activation detail page."""

    TASK_FILED = "task_filed"
    """An ExplorationTask was created (a human queued work for an agent)."""

    TASK_CLAIMED = "task_claimed"
    """An ExplorationTask transitioned OPEN -> IN_PROGRESS (an agent
    picked it up). Note this currently relies on ``updated_at`` being the
    claim time, since ``claimed_at`` is the dedicated column."""

    TASK_DONE = "task_done"
    """An ExplorationTask transitioned IN_PROGRESS -> DONE (an agent
    submitted findings)."""

    API_KEY_MINTED = "api_key_minted"
    """A new ApiKey row was minted (the human enabled a new agent
    identity)."""


class ActorKind(str, Enum):
    """Whether the row was authored via Clerk Bearer or API key.

    - ``user``: Clerk Bearer-authenticated request (human via UI).
        ``actor_label`` is ``None``; the UI typically renders this as
        "you" since the feed is per-user.
    - ``api_key``: API-key-authenticated request (agent, scheduled task,
        MCP server). ``actor_label`` carries the human-readable label
        from ``api_keys.label`` so the UI can identify which credential
        wrote the row.
    """

    USER = "user"
    API_KEY = "api_key"


class SubjectType(str, Enum):
    """The kind of underlying entity the row points at.

    Each row's ``subject_id`` is the UUID of an entity of this type. The
    UI uses ``subject_type`` to choose the right detail-page route when
    Tim clicks on a row (e.g. ``portfolio`` -> ``/portfolio/{id}``).
    """

    PORTFOLIO = "portfolio"
    STRATEGY = "strategy"
    BACKTEST = "backtest"
    ACTIVATION = "activation"
    TASK = "task"
    API_KEY = "api_key"


@dataclass(frozen=True)
class ActivityEventDTO:
    """Unified activity-feed entry projected from one of several source tables.

    Attributes:
        type: Kind of underlying event.
        occurred_at: Timestamp the event happened (UTC, timezone-aware).
            Sorting key for the feed (DESC). For trades this is the trade
            timestamp; for backtests / strategies / activations / tasks
            it's the appropriate row's ``created_at`` or transition
            timestamp.
        actor_kind: Whether this came from a Clerk-authenticated human or
            an API-key-authenticated machine identity.
        actor_label: Human-readable label of the API key when
            ``actor_kind == "api_key"``; ``None`` when ``actor_kind ==
            "user"`` (the UI renders that as "you").
        actor_user_id: Clerk-derived UUID of the owning user. Always
            present — both auth paths resolve to the same UUID via
            ``uuid5(NAMESPACE_DNS, clerk_user_id)``. The activity feed is
            scoped to the calling user so this is mostly redundant for
            display, but it's preserved on the wire for future
            cross-user / admin views.
        subject_type: Type of the underlying entity the row points at.
            Drives the click-to-navigate behaviour on the frontend.
        subject_id: UUID of the underlying entity. The frontend uses this
            with ``subject_type`` to build the detail-page URL.
        subject_name: Optional display name for the subject (portfolio
            name, strategy name, backtest_name, task summary).
            ``None`` when the subject has no natural name (e.g. a trade
            row points at the portfolio's UUID, but the user-facing label
            is the ticker ID).
        summary: Short human-readable line for the row's "what happened"
            column. Examples: "Bought 10 AAPL @ $293.32", "Filed task:
            Investigate AAPL mean-reversion", "Backtest completed: +8.4%".
    """

    type: ActivityEventType
    occurred_at: datetime
    actor_kind: ActorKind
    actor_label: str | None
    actor_user_id: UUID
    subject_type: SubjectType
    subject_id: UUID
    subject_name: str | None
    summary: str
