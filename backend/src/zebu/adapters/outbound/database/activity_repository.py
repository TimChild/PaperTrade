"""SQLModel implementation of ActivityRepository — recent activity feed.

Phase H2. Aggregates rows from six source tables into a unified, sorted,
paginated stream:

* ``transactions`` — buy / sell trades (deposits / withdrawals are
  intentionally excluded; they're not decisions Tim wants to see in a
  decision-stream view).
* ``strategies`` — strategy creation events.
* ``strategy_activations`` — both creation events and the most-recent
  ``last_executed_at`` (one row per fired execution, projected at read
  time since we don't have a dedicated ``activation_runs`` history
  table yet).
* ``backtest_runs`` — backtest creation events.
* ``exploration_tasks`` — task filed / claimed / done transitions
  (projected from the same row at multiple timestamps).
* ``api_keys`` — key minting events. Joined for actor labels too.

Strategy: pull one batch from each source (limit + offset → an
upper-bound pull of ``limit + offset`` rows per source from the user's
own data), project each row to one or more :class:`ActivityEventDTO`
instances, sort the merged list by ``occurred_at`` DESC, then slice to
``[offset:offset+limit]``.

The pull-per-source is bounded by ``limit + offset`` so we don't fetch
the full history. This keeps the typical "first 50 rows" query fast even
for a user with thousands of transactions. ``total`` is computed by
counting rows from each source independently and summing — it's an
upper-bound estimate that's exact in the typical case.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import (
    BacktestRunModel,
    ExplorationTaskModel,
    PortfolioModel,
    StrategyActivationModel,
    StrategyModel,
    TransactionModel,
)
from zebu.application.dtos.activity_event_dto import (
    ActivityEventDTO,
    ActivityEventType,
    ActorKind,
    SubjectType,
)
from zebu.application.ports.activity_repository import (
    ActivityFilter,
    ActivityPage,
)
from zebu.application.ports.api_key_repository import ApiKeyRepository
from zebu.domain.entities.api_key import ApiKey


def _utc(dt: datetime) -> datetime:
    """Re-attach UTC to a naive datetime read from the DB."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class SQLModelActivityRepository:
    """SQLModel implementation of :class:`ActivityRepository`.

    The repository owns no domain logic — it projects DB rows into the
    flat :class:`ActivityEventDTO` shape and merges them. All filtering /
    pagination semantics live in :meth:`list_events` so the API layer
    just adapts query params to :class:`ActivityFilter`.

    The api-key repository is injected (rather than queried directly) so
    test fixtures that swap the api-key adapter for an in-memory variant
    are still consistent with this aggregator. Production wiring uses
    the SQLModel api-key repo bound to the same session.
    """

    def __init__(
        self,
        session: AsyncSession,
        api_key_repository: ApiKeyRepository,
    ) -> None:
        """Initialise the repository.

        Args:
            session: Async DB session for this unit of work.
            api_key_repository: Repository used to resolve api_key ids
                back to human-readable labels. Injected so the
                in-memory test fixture remains the single source of
                truth for labels in tests.
        """
        self._session = session
        self._api_keys = api_key_repository

    async def list_events(self, filter_: ActivityFilter) -> ActivityPage:
        """Return one page of activity events for the given filter.

        Args:
            filter_: Scoping / pagination params (validated at the API
                layer; this method assumes ``limit > 0`` and
                ``offset >= 0``).

        Returns:
            :class:`ActivityPage` with events sorted DESC by
            ``occurred_at`` and total matching-row count.
        """
        # Resolve API-key labels once for the whole feed. The map is
        # small (one user has at most a handful of keys) so it's cheap
        # to load eagerly.
        labels = await self._load_api_key_labels(filter_.user_id)

        # Phase H2 fetches all matching rows per source and merges /
        # slices in Python. This keeps ``total`` exact so ``has_more`` on
        # the wire envelope is honest. For users with high activity
        # volume the per-source SELECT can be replaced with separate
        # COUNT + paginated queries — tracked as a follow-up perf task.
        #
        # The ``cap`` here is a safety upper bound — each individual
        # source can produce at most this many rows even if the user has
        # vastly more. It's set high enough (10x the per-source query) so
        # legitimate activity patterns are covered while a runaway
        # producer can't blow up memory.
        cap = max(2000, (filter_.limit + filter_.offset) * 10)

        # User's own portfolios — needed to scope transactions.
        portfolio_ids = await self._user_portfolio_ids(filter_.user_id)
        portfolio_names = await self._portfolio_name_map(portfolio_ids)

        events: list[ActivityEventDTO] = []
        if self._wants(filter_, ActivityEventType.TRADE):
            events.extend(
                await self._read_trades(
                    filter_=filter_,
                    portfolio_ids=portfolio_ids,
                    portfolio_names=portfolio_names,
                    labels=labels,
                    cap=cap,
                )
            )

        if self._wants(filter_, ActivityEventType.STRATEGY_CREATED):
            events.extend(
                await self._read_strategies(
                    filter_=filter_,
                    labels=labels,
                    cap=cap,
                )
            )

        if self._wants(filter_, ActivityEventType.BACKTEST):
            events.extend(
                await self._read_backtests(
                    filter_=filter_,
                    labels=labels,
                    cap=cap,
                )
            )

        wants_activation_created = self._wants(
            filter_, ActivityEventType.ACTIVATION_CREATED
        )
        wants_activation_run = self._wants(filter_, ActivityEventType.ACTIVATION_RUN)
        if wants_activation_created or wants_activation_run:
            events.extend(
                await self._read_activations(
                    filter_=filter_,
                    labels=labels,
                    cap=cap,
                    include_created=wants_activation_created,
                    include_runs=wants_activation_run,
                )
            )

        wants_task_filed = self._wants(filter_, ActivityEventType.TASK_FILED)
        wants_task_claimed = self._wants(filter_, ActivityEventType.TASK_CLAIMED)
        wants_task_done = self._wants(filter_, ActivityEventType.TASK_DONE)
        if wants_task_filed or wants_task_claimed or wants_task_done:
            events.extend(
                await self._read_tasks(
                    filter_=filter_,
                    labels=labels,
                    cap=cap,
                    include_filed=wants_task_filed,
                    include_claimed=wants_task_claimed,
                    include_done=wants_task_done,
                )
            )

        if self._wants(filter_, ActivityEventType.API_KEY_MINTED):
            events.extend(
                await self._read_api_keys(
                    filter_=filter_,
                    labels=labels,
                    cap=cap,
                )
            )

        # Apply ``actor_label`` filter post-merge (the source-specific
        # queries already narrowed by user_id, but they didn't all join
        # to api_keys to filter on label). This keeps each source query
        # simple at the cost of pulling slightly more rows than strictly
        # needed when the label filter is set.
        if filter_.actor_label is not None:
            events = [e for e in events if e.actor_label == filter_.actor_label]

        # Apply ``since`` filter post-merge for the same simplicity
        # reason. Each per-source query already pre-filters on the
        # corresponding timestamp column, but for activation runs and
        # task transitions we project the row at multiple timestamps so
        # the post-merge filter is the tidy single source of truth.
        if filter_.since is not None:
            since = filter_.since
            if since.tzinfo is None:
                since = since.replace(tzinfo=UTC)
            events = [e for e in events if e.occurred_at >= since]

        # Sort DESC by occurred_at; stable-tied by subject_id for
        # deterministic test assertions.
        events.sort(key=lambda e: (e.occurred_at, e.subject_id), reverse=True)

        total = len(events)
        page = events[filter_.offset : filter_.offset + filter_.limit]
        return ActivityPage(items=page, total=total)

    # --- source-specific projections ---------------------------------------

    @staticmethod
    def _wants(filter_: ActivityFilter, event_type: ActivityEventType) -> bool:
        """Return True if the filter selects this event type."""
        if filter_.event_types is None:
            return True
        return event_type in filter_.event_types

    async def _load_api_key_labels(self, user_id: UUID) -> dict[UUID, str]:
        """Return a {api_key_id: label} map for the user's keys.

        Uses the injected ``ApiKeyRepository`` port rather than querying
        :class:`ApiKeyModel` directly so test fixtures that swap in an
        in-memory api-key adapter resolve to the same labels.
        """
        keys: list[ApiKey] = await self._api_keys.get_by_user(user_id)
        return {key.id: key.label for key in keys}

    async def _user_portfolio_ids(self, user_id: UUID) -> list[UUID]:
        """Return the list of portfolio ids owned by the user."""
        statement = select(PortfolioModel.id).where(PortfolioModel.user_id == user_id)
        result = await self._session.exec(statement)
        return [row for row in result.all()]

    async def _portfolio_name_map(self, portfolio_ids: list[UUID]) -> dict[UUID, str]:
        """Return a {portfolio_id: name} map for the given ids."""
        if not portfolio_ids:
            return {}
        statement = select(PortfolioModel).where(
            col(PortfolioModel.id).in_(portfolio_ids)
        )
        result = await self._session.exec(statement)
        return {row.id: row.name for row in result.all()}

    def _actor_kind_label(
        self,
        api_key_id: UUID | None,
        labels: dict[UUID, str],
    ) -> tuple[ActorKind, str | None]:
        """Resolve actor kind + label from a row's stored ``api_key_id``."""
        if api_key_id is None:
            return (ActorKind.USER, None)
        label = labels.get(api_key_id)
        # If the api_key was deleted (FK ON DELETE SET NULL would set the
        # column to NULL anyway, but defend against an in-flight rows
        # whose api_key_id no longer matches an extant key) we still
        # render as api_key with a synthetic label so the UI doesn't
        # silently flip to "you".
        return (ActorKind.API_KEY, label if label is not None else "deleted-key")

    async def _read_trades(
        self,
        *,
        filter_: ActivityFilter,
        portfolio_ids: list[UUID],
        portfolio_names: dict[UUID, str],
        labels: dict[UUID, str],
        cap: int,
    ) -> list[ActivityEventDTO]:
        """Read BUY / SELL transactions for the user's portfolios."""
        if not portfolio_ids:
            return []

        statement = (
            select(TransactionModel)
            .where(col(TransactionModel.portfolio_id).in_(portfolio_ids))
            .where(col(TransactionModel.transaction_type).in_(["BUY", "SELL"]))
            .order_by(col(TransactionModel.timestamp).desc())
            .limit(cap)
        )
        if filter_.since is not None:
            since_naive = (
                filter_.since.astimezone(UTC).replace(tzinfo=None)
                if filter_.since.tzinfo is not None
                else filter_.since
            )
            statement = statement.where(TransactionModel.timestamp >= since_naive)

        result = await self._session.exec(statement)
        rows = result.all()

        events: list[ActivityEventDTO] = []
        for row in rows:
            kind, label = self._actor_kind_label(row.api_key_id, labels)
            ticker = row.ticker or "?"
            qty = row.quantity if row.quantity is not None else 0
            price = (
                row.price_per_share_amount
                if row.price_per_share_amount is not None
                else 0
            )
            verb = "Bought" if row.transaction_type == "BUY" else "Sold"
            summary = f"{verb} {qty:g} {ticker} @ ${price:.2f}"
            events.append(
                ActivityEventDTO(
                    type=ActivityEventType.TRADE,
                    occurred_at=_utc(row.timestamp),
                    actor_kind=kind,
                    actor_label=label,
                    actor_user_id=filter_.user_id,
                    subject_type=SubjectType.PORTFOLIO,
                    subject_id=row.portfolio_id,
                    subject_name=portfolio_names.get(row.portfolio_id),
                    summary=summary,
                )
            )
        return events

    async def _read_strategies(
        self,
        *,
        filter_: ActivityFilter,
        labels: dict[UUID, str],
        cap: int,
    ) -> list[ActivityEventDTO]:
        """Read strategy-creation rows for the user."""
        statement = (
            select(StrategyModel)
            .where(StrategyModel.user_id == filter_.user_id)
            .order_by(col(StrategyModel.created_at).desc())
            .limit(cap)
        )
        if filter_.since is not None:
            since_naive = (
                filter_.since.astimezone(UTC).replace(tzinfo=None)
                if filter_.since.tzinfo is not None
                else filter_.since
            )
            statement = statement.where(StrategyModel.created_at >= since_naive)

        result = await self._session.exec(statement)
        rows = result.all()

        events: list[ActivityEventDTO] = []
        for row in rows:
            kind, label = self._actor_kind_label(row.api_key_id, labels)
            events.append(
                ActivityEventDTO(
                    type=ActivityEventType.STRATEGY_CREATED,
                    occurred_at=_utc(row.created_at),
                    actor_kind=kind,
                    actor_label=label,
                    actor_user_id=filter_.user_id,
                    subject_type=SubjectType.STRATEGY,
                    subject_id=row.id,
                    subject_name=row.name,
                    summary=f"Created strategy: {row.name}",
                )
            )
        return events

    async def _read_backtests(
        self,
        *,
        filter_: ActivityFilter,
        labels: dict[UUID, str],
        cap: int,
    ) -> list[ActivityEventDTO]:
        """Read backtest-run creation rows for the user."""
        statement = (
            select(BacktestRunModel)
            .where(BacktestRunModel.user_id == filter_.user_id)
            .order_by(col(BacktestRunModel.created_at).desc())
            .limit(cap)
        )
        if filter_.since is not None:
            since_naive = (
                filter_.since.astimezone(UTC).replace(tzinfo=None)
                if filter_.since.tzinfo is not None
                else filter_.since
            )
            statement = statement.where(BacktestRunModel.created_at >= since_naive)

        result = await self._session.exec(statement)
        rows = result.all()

        events: list[ActivityEventDTO] = []
        for row in rows:
            kind, label = self._actor_kind_label(row.api_key_id, labels)
            events.append(
                ActivityEventDTO(
                    type=ActivityEventType.BACKTEST,
                    occurred_at=_utc(row.created_at),
                    actor_kind=kind,
                    actor_label=label,
                    actor_user_id=filter_.user_id,
                    subject_type=SubjectType.BACKTEST,
                    subject_id=row.id,
                    subject_name=row.backtest_name,
                    summary=f"Filed backtest: {row.backtest_name}",
                )
            )
        return events

    async def _read_activations(
        self,
        *,
        filter_: ActivityFilter,
        labels: dict[UUID, str],
        cap: int,
        include_created: bool,
        include_runs: bool,
    ) -> list[ActivityEventDTO]:
        """Read activation rows; project to creation + run events as needed."""
        statement = (
            select(StrategyActivationModel)
            .where(StrategyActivationModel.user_id == filter_.user_id)
            .order_by(col(StrategyActivationModel.created_at).desc())
            .limit(cap)
        )

        result = await self._session.exec(statement)
        rows = result.all()

        events: list[ActivityEventDTO] = []
        for row in rows:
            kind, label = self._actor_kind_label(row.api_key_id, labels)

            if include_created:
                events.append(
                    ActivityEventDTO(
                        type=ActivityEventType.ACTIVATION_CREATED,
                        occurred_at=_utc(row.created_at),
                        actor_kind=kind,
                        actor_label=label,
                        actor_user_id=filter_.user_id,
                        subject_type=SubjectType.ACTIVATION,
                        subject_id=row.id,
                        subject_name=None,
                        summary="Activated strategy for live execution",
                    )
                )

            if include_runs and row.last_executed_at is not None:
                # The activation's most recent execution. We don't have a
                # full execution-history table yet; if/when one lands the
                # projection here can fan out to one event per run.
                events.append(
                    ActivityEventDTO(
                        type=ActivityEventType.ACTIVATION_RUN,
                        occurred_at=_utc(row.last_executed_at),
                        # Scheduler-driven runs are not API-key-authored.
                        actor_kind=ActorKind.USER,
                        actor_label=None,
                        actor_user_id=filter_.user_id,
                        subject_type=SubjectType.ACTIVATION,
                        subject_id=row.id,
                        subject_name=None,
                        summary="Strategy executed on schedule",
                    )
                )
        return events

    async def _read_tasks(
        self,
        *,
        filter_: ActivityFilter,
        labels: dict[UUID, str],
        cap: int,
        include_filed: bool,
        include_claimed: bool,
        include_done: bool,
    ) -> list[ActivityEventDTO]:
        """Read task rows; project filed / claimed / done events."""
        statement = (
            select(ExplorationTaskModel)
            .where(ExplorationTaskModel.created_by == filter_.user_id)
            .order_by(col(ExplorationTaskModel.created_at).desc())
            .limit(cap)
        )

        result = await self._session.exec(statement)
        rows = result.all()

        events: list[ActivityEventDTO] = []
        for row in rows:
            kind, label = self._actor_kind_label(row.api_key_id, labels)
            # Truncate the prompt for the summary line — feed entries are
            # one-liners and prompts can be 4000 chars.
            short = row.prompt if len(row.prompt) <= 80 else row.prompt[:77] + "..."

            if include_filed:
                events.append(
                    ActivityEventDTO(
                        type=ActivityEventType.TASK_FILED,
                        occurred_at=_utc(row.created_at),
                        actor_kind=kind,
                        actor_label=label,
                        actor_user_id=filter_.user_id,
                        subject_type=SubjectType.TASK,
                        subject_id=row.id,
                        subject_name=short,
                        summary=f"Filed task: {short}",
                    )
                )

            if include_claimed and row.claimed_at is not None:
                # Claim is performed by an agent so the actor is the
                # claiming credential — but we don't currently record
                # which API-key issued the claim; the row's stored
                # ``api_key_id`` is the *creator's* credential, not the
                # claimer's. For Phase H2 we render the claim with
                # ``actor_kind="api_key"`` and the agent identifier
                # (``claimed_by``) as the label, since that's what's
                # actually identifying-information here.
                claim_actor: ActorKind = ActorKind.API_KEY
                claim_label = row.claimed_by
                events.append(
                    ActivityEventDTO(
                        type=ActivityEventType.TASK_CLAIMED,
                        occurred_at=_utc(row.claimed_at),
                        actor_kind=claim_actor,
                        actor_label=claim_label,
                        actor_user_id=filter_.user_id,
                        subject_type=SubjectType.TASK,
                        subject_id=row.id,
                        subject_name=short,
                        summary=f"Task claimed by {claim_label or 'agent'}",
                    )
                )

            if include_done and row.status == "DONE":
                # Mark "done" at the row's updated_at — the entity sets
                # this on transition. The completion actor is the agent
                # that submitted findings, same as claim_by.
                completion_label = row.claimed_by
                events.append(
                    ActivityEventDTO(
                        type=ActivityEventType.TASK_DONE,
                        occurred_at=_utc(row.updated_at),
                        actor_kind=ActorKind.API_KEY,
                        actor_label=completion_label,
                        actor_user_id=filter_.user_id,
                        subject_type=SubjectType.TASK,
                        subject_id=row.id,
                        subject_name=short,
                        summary=f"Task completed by {completion_label or 'agent'}",
                    )
                )
        return events

    async def _read_api_keys(
        self,
        *,
        filter_: ActivityFilter,
        labels: dict[UUID, str],
        cap: int,
    ) -> list[ActivityEventDTO]:
        """Read api_key rows projecting "minted" events.

        API keys are minted only via the Clerk-gated route, so the actor
        is always the user (no parent api_key_id is recorded on this
        row). The label projected is the *minted* key's own label so the
        UI shows "you minted: claude-laptop".

        Uses the injected ``ApiKeyRepository`` port (rather than querying
        :class:`ApiKeyModel` directly) so tests with an in-memory api-key
        adapter share the same view of issued keys.
        """
        del labels  # not needed for this projection — actor is always user
        keys: list[ApiKey] = await self._api_keys.get_by_user(filter_.user_id)

        # Apply ``since`` post-fetch since the protocol doesn't accept it.
        # The list is small (one user has at most a handful of keys) so
        # this is cheap.
        if filter_.since is not None:
            since = filter_.since
            if since.tzinfo is None:
                since = since.replace(tzinfo=UTC)
            keys = [k for k in keys if k.created_at >= since]

        # Repository returns oldest-first; project to events sorted-DESC
        # in the merge step at the top of list_events.
        keys_recent_first = sorted(keys, key=lambda k: k.created_at, reverse=True)[:cap]

        events: list[ActivityEventDTO] = []
        for key in keys_recent_first:
            events.append(
                ActivityEventDTO(
                    type=ActivityEventType.API_KEY_MINTED,
                    occurred_at=key.created_at
                    if key.created_at.tzinfo is not None
                    else key.created_at.replace(tzinfo=UTC),
                    actor_kind=ActorKind.USER,
                    actor_label=None,
                    actor_user_id=filter_.user_id,
                    subject_type=SubjectType.API_KEY,
                    subject_id=key.id,
                    subject_name=key.label,
                    summary=f"Minted API key: {key.label}",
                )
            )
        return events


__all__ = ["SQLModelActivityRepository"]
