"""ExplorationTask API routes.

Phase C4 — REST endpoints for the human → agent task queue:

* ``POST /exploration-tasks`` — human creates a task.
* ``GET  /exploration-tasks`` — list (filterable by status / scope).
* ``GET  /exploration-tasks/{id}`` — fetch one.
* ``DELETE /exploration-tasks/{id}`` — owner abandons + deletes.
* ``POST /exploration-tasks/{id}/claim`` — agent (currently any
  authenticated user; will become API-key-gated in Phase C2) atomically
  claims the task.
* ``POST /exploration-tasks/{id}/findings`` — claiming agent submits
  findings, transitioning the task to DONE.

All routes are Clerk-Bearer-gated through ``CurrentUserDep`` until Phase
C2 lands the API-key path. Errors flow through the global exception
handlers (``InvalidExplorationTaskError`` -> 422; ``HTTPException`` ->
the standard ``ErrorResponse`` envelope).
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from zebu.adapters.inbound.api.dependencies import CurrentUserDep
from zebu.adapters.inbound.api.schemas import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from zebu.adapters.inbound.api.schemas.pagination import build_paginated_response
from zebu.adapters.outbound.database.exploration_task_repository import (
    SQLModelExplorationTaskRepository,
)
from zebu.domain.entities.exploration_task import (
    ExplorationConstraints,
    ExplorationFindings,
    ExplorationTask,
    ExplorationTaskStatus,
)
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/exploration-tasks", tags=["exploration-tasks"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ConstraintsPayload(BaseModel):
    """Wire shape for ``ExplorationConstraints``."""

    max_backtests: int | None = Field(default=None, gt=0)
    allow_live_activation: bool = True
    strategy_type_whitelist: list[str] | None = None

    @field_validator("strategy_type_whitelist")
    @classmethod
    def _validate_whitelist(cls, value: list[str] | None) -> list[str] | None:
        """Reject empty list — match the domain invariant."""
        if value is not None and len(value) == 0:
            raise ValueError("strategy_type_whitelist must be None or non-empty")
        return value


class CreateExplorationTaskRequest(BaseModel):
    """Request body for ``POST /exploration-tasks``.

    The ``prompt`` is the primary required field per resolved Q7 — every
    other field is optional. Missing optional fields land in the entity
    as ``None`` (no scope / no constraints), keeping the queue free-form
    by default.
    """

    prompt: str = Field(..., min_length=1, max_length=4000)
    target_portfolio_id: UUID | None = None
    tickers: list[str] | None = Field(default=None, max_length=50)
    constraints: ConstraintsPayload | None = None


class FindingsPayload(BaseModel):
    """Wire shape for ``ExplorationFindings`` on the submit-findings route."""

    summary: str = Field(..., min_length=1, max_length=4000)
    backtest_run_ids: list[UUID] = Field(default_factory=list)
    strategy_ids: list[UUID] = Field(default_factory=list)
    notes: list[str] | None = None


class ClaimRequest(BaseModel):
    """Optional body for ``POST /exploration-tasks/{id}/claim``.

    The agent identifier is free-form for now — typically a string label
    the agent picks (e.g. ``zebu-strategy-explorer-1``) or an API-key
    label once Phase C2 lands. Defaults to the user's UUID if absent so
    the route remains usable through Bearer auth.
    """

    agent_id: str | None = Field(default=None, min_length=1, max_length=200)


class ConstraintsResponse(BaseModel):
    """Response shape for constraints."""

    max_backtests: int | None
    allow_live_activation: bool
    strategy_type_whitelist: list[str] | None


class FindingsResponse(BaseModel):
    """Response shape for findings."""

    summary: str
    backtest_run_ids: list[UUID]
    strategy_ids: list[UUID]
    notes: list[str] | None


class ExplorationTaskResponse(BaseModel):
    """Response shape for ``ExplorationTask`` on every route."""

    id: UUID
    created_by: UUID
    prompt: str
    status: str
    target_portfolio_id: UUID | None
    tickers: list[str] | None
    constraints: ConstraintsResponse | None
    claimed_by: str | None
    claimed_at: str | None
    findings: FindingsResponse | None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload_to_constraints(
    payload: ConstraintsPayload | None,
) -> ExplorationConstraints | None:
    """Convert the wire-format constraints payload to a domain object.

    Returns ``None`` when no constraints are supplied. Raises
    ``InvalidExplorationTaskError`` (mapped to 422 by the global handler)
    when the entity rejects them.
    """
    if payload is None:
        return None
    whitelist: list[StrategyType] | None
    if payload.strategy_type_whitelist is None:
        whitelist = None
    else:
        # Convert each string to a StrategyType. Pydantic doesn't run the
        # enum conversion for us when the wire field is `list[str]`, so
        # we do it explicitly here. Invalid values raise ValueError, which
        # FastAPI surfaces as a 422 — desired behaviour.
        try:
            whitelist = [
                StrategyType(value) for value in payload.strategy_type_whitelist
            ]
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid strategy_type in whitelist: {exc}",
            ) from exc
    return ExplorationConstraints(
        max_backtests=payload.max_backtests,
        allow_live_activation=payload.allow_live_activation,
        strategy_type_whitelist=whitelist,
    )


def _to_response(task: ExplorationTask) -> ExplorationTaskResponse:
    """Convert a domain task to the wire response model."""
    constraints_response: ConstraintsResponse | None
    if task.constraints is None:
        constraints_response = None
    else:
        whitelist_strings: list[str] | None
        if task.constraints.strategy_type_whitelist is None:
            whitelist_strings = None
        else:
            whitelist_strings = [
                t.value for t in task.constraints.strategy_type_whitelist
            ]
        constraints_response = ConstraintsResponse(
            max_backtests=task.constraints.max_backtests,
            allow_live_activation=task.constraints.allow_live_activation,
            strategy_type_whitelist=whitelist_strings,
        )

    findings_response: FindingsResponse | None
    if task.findings is None:
        findings_response = None
    else:
        findings_response = FindingsResponse(
            summary=task.findings.summary,
            backtest_run_ids=task.findings.backtest_run_ids,
            strategy_ids=task.findings.strategy_ids,
            notes=task.findings.notes,
        )

    tickers_response: list[str] | None
    if task.tickers is None:
        tickers_response = None
    else:
        tickers_response = [t.symbol for t in task.tickers]

    return ExplorationTaskResponse(
        id=task.id,
        created_by=task.created_by,
        prompt=task.prompt,
        status=task.status.value,
        target_portfolio_id=task.target_portfolio_id,
        tickers=tickers_response,
        constraints=constraints_response,
        claimed_by=task.claimed_by,
        claimed_at=task.claimed_at.isoformat() if task.claimed_at else None,
        findings=findings_response,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


def _parse_status(raw: str | None) -> ExplorationTaskStatus | None:
    """Parse the ``status`` query parameter, returning None for absent."""
    if raw is None:
        return None
    try:
        return ExplorationTaskStatus(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid status: '{raw}'. Must be one of: "
                f"{', '.join(s.value for s in ExplorationTaskStatus)}"
            ),
        ) from exc


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=ExplorationTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exploration_task(
    request: CreateExplorationTaskRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ExplorationTaskResponse:
    """Create a new exploration task.

    The caller becomes the task's owner (``created_by``) and the task starts
    in OPEN status, ready for an agent to claim.
    """
    constraints = _payload_to_constraints(request.constraints)

    tickers: list[Ticker] | None
    if request.tickers is None:
        tickers = None
    else:
        # Constructing the Ticker validates the symbol format. Errors land
        # in the global handler as 400.
        tickers = [Ticker(symbol) for symbol in request.tickers]

    now = datetime.now(UTC)
    task = ExplorationTask(
        id=uuid4(),
        created_by=current_user,
        prompt=request.prompt,
        status=ExplorationTaskStatus.OPEN,
        created_at=now,
        updated_at=now,
        target_portfolio_id=request.target_portfolio_id,
        tickers=tickers,
        constraints=constraints,
    )

    repo = SQLModelExplorationTaskRepository(session)
    await repo.save(task)

    return _to_response(task)


@router.get("", response_model=PaginatedResponse[ExplorationTaskResponse])
async def list_exploration_tasks(
    current_user: CurrentUserDep,
    session: SessionDep,
    scope: str = Query(
        default="all",
        description=(
            "Which tasks to return: 'all' (default) returns the global queue "
            "filtered by status; 'mine' returns only tasks created by the "
            "current user (status filter still applied)."
        ),
        pattern="^(all|mine)$",
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description=(
            "Filter by task status. One of: OPEN, IN_PROGRESS, DONE, "
            "ABANDONED. When omitted under scope='all', returns OPEN tasks "
            "only (the queue view)."
        ),
    ),
    limit: int = Query(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Maximum number of tasks to return (1-100, default 20).",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of tasks to skip for pagination (default 0).",
    ),
) -> PaginatedResponse[ExplorationTaskResponse]:
    """List exploration tasks.

    Two scopes are supported:

    * ``scope=all`` (default) — returns the **queue view**: every task
      visible to any agent in the system, filtered by status. Defaults to
      ``status=OPEN`` so a bare ``GET /exploration-tasks`` returns the
      claimable backlog, oldest-first.
    * ``scope=mine`` — returns only tasks created by the current user,
      newest-first. ``status`` filter still applies if supplied.
    """
    parsed_status = _parse_status(status_filter)
    repo = SQLModelExplorationTaskRepository(session)

    if scope == "mine":
        items = await repo.list_for_user(
            current_user,
            status=parsed_status,
            limit=limit,
            offset=offset,
        )
        total = await repo.count_for_user(current_user, status=parsed_status)
    else:
        # scope == "all" — default to OPEN if no status filter given so the
        # queue view is the obvious URL.
        effective_status = parsed_status or ExplorationTaskStatus.OPEN
        items = await repo.list_by_status(
            effective_status,
            limit=limit,
            offset=offset,
        )
        total = await repo.count_by_status(effective_status)

    return build_paginated_response(
        items=[_to_response(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=ExplorationTaskResponse)
async def get_exploration_task(
    task_id: UUID,
    current_user: CurrentUserDep,  # noqa: ARG001 — required for auth
    session: SessionDep,
) -> ExplorationTaskResponse:
    """Fetch a single exploration task.

    Any authenticated user can read any task — agents need to inspect the
    queue regardless of who filed the task. Per-task scope-checking is a
    Phase D/E concern once API-key scopes land.
    """
    repo = SQLModelExplorationTaskRepository(session)
    task = await repo.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exploration task not found: {task_id}",
        )
    return _to_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exploration_task(
    task_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> None:
    """Abandon and remove a task.

    Only the task's creator (``created_by``) may delete it. The task does
    not need to be in any specific status — deleting an IN_PROGRESS task
    is allowed and is the human's "abort this exploration now" override.

    Note: this is a hard delete. For "abandon but keep the audit history",
    a future endpoint could expose the entity's ``abandon`` transition
    instead. The current cut prefers simplicity.
    """
    repo = SQLModelExplorationTaskRepository(session)
    task = await repo.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exploration task not found: {task_id}",
        )

    if task.created_by != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this task",
        )

    await repo.delete(task_id)


@router.post(
    "/{task_id}/claim",
    response_model=ExplorationTaskResponse,
)
async def claim_exploration_task(
    task_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    body: ClaimRequest | None = None,
) -> ExplorationTaskResponse:
    """Atomically claim an OPEN task.

    Race-safe: the underlying ``claim_atomic`` issues a single UPDATE
    that only matches rows currently in OPEN status, so two callers
    fighting for the same task can't both succeed.

    The caller supplies an ``agent_id`` (free-form label) in the body;
    if absent, the current user's UUID is used. Once Phase C2 lands the
    API-key path, the agent's key label will be the natural value here.

    Returns 409 Conflict when the task no longer exists or has already
    been claimed.
    """
    agent_id = (body.agent_id if body and body.agent_id else None) or str(current_user)

    repo = SQLModelExplorationTaskRepository(session)
    claimed = await repo.claim_atomic(
        task_id,
        agent_id=agent_id,
        claimed_at=datetime.now(UTC),
    )
    if claimed is None:
        # Either the task doesn't exist or it isn't OPEN. We need to tell
        # the caller which it is so polling agents can react sensibly.
        existing = await repo.get(task_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exploration task not found: {task_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Task {task_id} is in {existing.status.value} status and "
                "cannot be claimed"
            ),
        )

    return _to_response(claimed)


@router.post(
    "/{task_id}/findings",
    response_model=ExplorationTaskResponse,
)
async def submit_exploration_task_findings(
    task_id: UUID,
    findings_payload: FindingsPayload,
    current_user: CurrentUserDep,  # noqa: ARG001 — required for auth
    session: SessionDep,
) -> ExplorationTaskResponse:
    """Submit findings for a claimed task and transition it to DONE.

    The task must be in IN_PROGRESS status; otherwise the request is a
    409. Per-claimer enforcement (only the claiming agent may submit
    findings) is deferred to Phase D when API-key scopes land — for
    Phase C4 any authenticated user can submit findings on any
    IN_PROGRESS task.
    """
    findings = ExplorationFindings(
        summary=findings_payload.summary,
        backtest_run_ids=list(findings_payload.backtest_run_ids),
        strategy_ids=list(findings_payload.strategy_ids),
        notes=findings_payload.notes,
    )

    repo = SQLModelExplorationTaskRepository(session)
    task = await repo.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exploration task not found: {task_id}",
        )

    if task.status is not ExplorationTaskStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Task {task_id} is in {task.status.value} status; findings "
                "can only be submitted for IN_PROGRESS tasks"
            ),
        )

    completed = task.complete(findings=findings, completed_at=datetime.now(UTC))
    await repo.save(completed)

    return _to_response(completed)
