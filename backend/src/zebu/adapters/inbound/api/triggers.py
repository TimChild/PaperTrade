"""Trigger CRUD + fire-log + per-user kill-switch API routes (Phase F-5).

Endpoints (per Phase-F design §7):

* ``POST  /activations/{activation_id}/triggers`` — attach a trigger.
* ``GET   /activations/{activation_id}/triggers`` — list (paginated).
* ``GET   /triggers/{trigger_id}`` — fetch one.
* ``PATCH /triggers/{trigger_id}`` — update mutable fields.
* ``DELETE /triggers/{trigger_id}`` — soft-delete (transition to EXPIRED).
* ``GET   /triggers/{trigger_id}/fires`` — paginated fire log.
* ``POST  /triggers/disable-all`` — per-user kill switch.

All routes require an authenticated identity (Clerk Bearer or API key).
Ownership is enforced on every route — the caller's ``current_user`` UUID
must match the trigger's (or activation's) ``user_id``.

Per Phase-F design Q3, lifting ``MANUALLY_DISABLED`` via PATCH is
intentionally rejected with 422; the documented lift path is
"delete and recreate". This is enforced in :func:`update_trigger`.

Per Phase-F design §1.1, the ``DELETE`` route is a *soft* delete: the
row stays so the fire-log endpoints can render history. The trigger
transitions to ``EXPIRED`` (which the entity treats as terminal) but
keeps its ID + audit metadata.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from zebu.adapters.inbound.api.dependencies import (
    ActiveApiKeyIdDep,
    CurrentUserDep,
)
from zebu.adapters.inbound.api.schemas import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    CreateTriggerRequest,
    DisableAllResponse,
    PaginatedResponse,
    TriggerFireResponse,
    TriggerResponse,
    UpdateTriggerRequest,
)
from zebu.adapters.inbound.api.schemas.pagination import build_paginated_response
from zebu.adapters.outbound.database.strategy_activation_repository import (
    SQLModelStrategyActivationRepository,
)
from zebu.adapters.outbound.database.strategy_condition_trigger_repository import (
    SQLModelTriggerRepository,
)
from zebu.adapters.outbound.database.trigger_fire_repository import (
    SQLModelTriggerFireRepository,
)
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.trigger_fire_record import TriggerFireRecord
from zebu.domain.exceptions import InvalidTriggerError
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    params_from_dict,
)
from zebu.domain.value_objects.trigger_invocation_mode import TriggerInvocationMode
from zebu.domain.value_objects.trigger_status import TriggerStatus
from zebu.infrastructure.database import SessionDep

# Two routers — one mounted under ``/activations`` for the
# ``/{activation_id}/triggers`` collection and one under ``/triggers``
# for the per-trigger paths. Both share the same module + tag.

activations_triggers_router = APIRouter(
    prefix="/activations",
    tags=["triggers"],
)
triggers_router = APIRouter(prefix="/triggers", tags=["triggers"])

# Module-level structlog logger. Picks up the actor identity bound by
# get_current_user (auth_method, clerk_user_id, api_key_id, api_key_label)
# automatically via structlog.contextvars — Phase H5.
logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trigger_to_response(trigger: StrategyConditionTrigger) -> TriggerResponse:
    """Convert a domain :class:`StrategyConditionTrigger` to its wire response."""
    return TriggerResponse(
        id=trigger.id,
        activation_id=trigger.activation_id,
        user_id=trigger.user_id,
        condition_type=trigger.condition_type.value,
        # to_dict() returns a fresh dict so caller-side mutation can't
        # round-trip back to the domain entity's frozen mapping.
        condition_params=dict(trigger.condition_params.to_dict()),
        agent_prompt=trigger.agent_prompt,
        cooldown_seconds=trigger.cooldown_seconds,
        last_fired_at=(
            trigger.last_fired_at.isoformat()
            if trigger.last_fired_at is not None
            else None
        ),
        status=trigger.status.value,
        priority=trigger.priority,
        default_api_key_id=trigger.default_api_key_id,
        expires_at=(
            trigger.expires_at.isoformat() if trigger.expires_at is not None else None
        ),
        created_at=trigger.created_at.isoformat(),
        created_by=trigger.created_by,
        updated_at=trigger.updated_at.isoformat(),
        mode=trigger.mode.value,
    )


def _parse_invocation_mode(raw: str) -> TriggerInvocationMode:
    """Parse ``mode`` from the wire payload, returning a 422 on bad input."""
    try:
        return TriggerInvocationMode(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid mode: '{raw}'. Must be one of: "
                f"{', '.join(m.value for m in TriggerInvocationMode)}"
            ),
        ) from exc


def _fire_to_response(record: TriggerFireRecord) -> TriggerFireResponse:
    """Convert a domain :class:`TriggerFireRecord` to its wire response."""
    return TriggerFireResponse(
        id=record.id,
        trigger_id=record.trigger_id,
        activation_id=record.activation_id,
        fired_at=record.fired_at.isoformat(),
        condition_evaluation_data=dict(record.condition_evaluation_data),
        invocation_mode=record.invocation_mode.value,
        agent_invocation_id=record.agent_invocation_id,
        agent_response=(
            record.agent_response.value if record.agent_response is not None else None
        ),
        agent_response_raw=record.agent_response_raw,
        resulting_trade_id=record.resulting_trade_id,
        resulting_modify_payload=(
            dict(record.resulting_modify_payload)
            if record.resulting_modify_payload is not None
            else None
        ),
        resulting_exploration_task_id=record.resulting_exploration_task_id,
        latency_ms=record.latency_ms,
        api_key_id_used=record.api_key_id_used,
    )


def _parse_condition_type(raw: str) -> ConditionType:
    """Parse ``condition_type`` from the wire payload, returning a 422 on bad input."""
    try:
        return ConditionType(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid condition_type: '{raw}'. Must be one of: "
                f"{', '.join(c.value for c in ConditionType)}"
            ),
        ) from exc


def _parse_expires_at(raw: str | None) -> datetime | None:
    """Parse the optional ``expires_at`` ISO-8601 string from the wire body."""
    if raw is None:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid expires_at — expected ISO-8601 string, got: {raw!r}",
        ) from exc
    if parsed.tzinfo is None:
        # Domain treats naive timestamps as UTC; surface the tz so the
        # entity's invariant comparisons all use the same wall-clock.
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


# ---------------------------------------------------------------------------
# Routes — under /activations
# ---------------------------------------------------------------------------


@activations_triggers_router.post(
    "/{activation_id}/triggers",
    response_model=TriggerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trigger(
    activation_id: UUID,
    request: CreateTriggerRequest,
    current_user: CurrentUserDep,
    api_key_id: ActiveApiKeyIdDep,
    session: SessionDep,
) -> TriggerResponse:
    """Attach a new trigger to an activation.

    Validates that the caller owns the activation (403 otherwise) and that
    the supplied ``condition_params`` shape matches the
    ``condition_type`` discriminator (422 otherwise). The new trigger
    starts in :class:`TriggerStatus.ACTIVE`.

    Per Phase-F design Q1, the ``CUSTOM_RULE`` condition type is
    rejected at construction time with a clear 422.
    """
    activation_repo = SQLModelStrategyActivationRepository(session)
    trigger_repo = SQLModelTriggerRepository(session)

    activation = await activation_repo.get(activation_id)
    if activation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activation not found: {activation_id}",
        )
    if activation.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to attach a trigger to this activation",
        )

    condition_type = _parse_condition_type(request.condition_type)
    expires_at = _parse_expires_at(request.expires_at)
    mode = _parse_invocation_mode(request.mode)

    # The domain factory validates the params shape against the
    # discriminator and raises ``InvalidTriggerError`` (mapped to 422 by
    # the global handler) on mismatch / missing fields.
    try:
        condition_params = params_from_dict(condition_type, request.condition_params)
    except InvalidTriggerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    now = datetime.now(UTC)
    try:
        trigger = StrategyConditionTrigger(
            id=uuid4(),
            activation_id=activation_id,
            user_id=current_user,
            condition_type=condition_type,
            condition_params=condition_params,
            agent_prompt=request.agent_prompt,
            cooldown_seconds=request.cooldown_seconds,
            priority=request.priority,
            default_api_key_id=request.default_api_key_id,
            expires_at=expires_at,
            status=TriggerStatus.ACTIVE,
            created_at=now,
            created_by=current_user,
            updated_at=now,
            mode=mode,
        )
    except InvalidTriggerError as exc:
        # Surface entity-level invariant violations (e.g. agent_prompt too
        # short after stripping whitespace) as 422.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await trigger_repo.save(trigger, api_key_id=api_key_id)
    logger.info(
        "Trigger created",
        trigger_id=str(trigger.id),
        activation_id=str(activation_id),
        condition_type=condition_type.value,
        mode=mode.value,
    )
    return _trigger_to_response(trigger)


@activations_triggers_router.get(
    "/{activation_id}/triggers",
    response_model=PaginatedResponse[TriggerResponse],
)
async def list_triggers_for_activation(
    activation_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    limit: int = Query(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Maximum number of triggers to return (1-100, default 20).",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of triggers to skip for pagination (default 0).",
    ),
) -> PaginatedResponse[TriggerResponse]:
    """List the activation's triggers (including terminal-status), paginated.

    Includes terminal-status rows (EXPIRED / MANUALLY_DISABLED) so the UI
    can render history, matching the
    :meth:`TriggerRepository.list_for_activation` contract.

    403 when the caller doesn't own the activation.
    """
    activation_repo = SQLModelStrategyActivationRepository(session)
    trigger_repo = SQLModelTriggerRepository(session)

    activation = await activation_repo.get(activation_id)
    if activation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activation not found: {activation_id}",
        )
    if activation.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this activation's triggers",
        )

    triggers = await trigger_repo.list_for_activation(activation_id)
    # Page in Python — trigger volume per activation is small (a handful);
    # SQL push-down isn't worth the per-route complexity. Matches the
    # activation list endpoint pattern.
    total = len(triggers)
    page = triggers[offset : offset + limit]
    items = [_trigger_to_response(t) for t in page]
    return build_paginated_response(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Routes — under /triggers
# ---------------------------------------------------------------------------


@triggers_router.post(
    "/disable-all",
    response_model=DisableAllResponse,
)
async def disable_all_for_user(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> DisableAllResponse:
    """Per-user kill switch — disable every non-terminal trigger this user owns.

    Sets every ACTIVE / PAUSED trigger owned by ``current_user`` to
    :class:`TriggerStatus.MANUALLY_DISABLED`. Idempotent — a user with no
    non-terminal triggers gets ``disabled_count=0``.

    Per Phase-F design Q3 + §4.3.3, ``MANUALLY_DISABLED`` is terminal. To
    re-enable a disabled trigger, delete and recreate it.

    Logged at WARN level with the actor identity bound by
    :func:`_bind_actor_to_log_context` (Phase H5) — auth method,
    clerk_user_id, api_key_id, and api_key_label all flow through
    structlog contextvars.
    """
    trigger_repo = SQLModelTriggerRepository(session)
    now = datetime.now(UTC)
    disabled = await trigger_repo.disable_all_for_user(current_user, at=now)

    logger.warning(
        "Per-user kill switch invoked — triggers disabled",
        user_id=str(current_user),
        disabled_count=disabled,
    )

    return DisableAllResponse(disabled_count=disabled)


@triggers_router.get(
    "/{trigger_id}",
    response_model=TriggerResponse,
)
async def get_trigger(
    trigger_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> TriggerResponse:
    """Fetch a single trigger by ID.

    403 when the caller doesn't own it.
    """
    trigger_repo = SQLModelTriggerRepository(session)
    trigger = await trigger_repo.get(trigger_id)
    if trigger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger not found: {trigger_id}",
        )
    if trigger.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this trigger",
        )
    return _trigger_to_response(trigger)


@triggers_router.patch(
    "/{trigger_id}",
    response_model=TriggerResponse,
)
async def update_trigger(
    trigger_id: UUID,
    request: UpdateTriggerRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> TriggerResponse:
    """Update mutable fields on a trigger.

    Mutable fields:

    * ``agent_prompt`` — same constraints as create.
    * ``cooldown_seconds`` — non-negative integer.
    * ``priority`` — ``[-100, 100]``.
    * ``condition_params`` — replaces the typed VO; must validate against
      the existing ``condition_type``.
    * ``status`` — only ``ACTIVE`` (resume) or ``PAUSED`` (pause).
      Lifting ``MANUALLY_DISABLED`` via this endpoint is intentionally
      rejected with 422 per Phase-F design Q3 — the documented lift path
      is "delete and recreate".

    Forbidden mutations (rejected via Pydantic field absence):

    * ``activation_id``, ``user_id``, ``condition_type``, ``created_at``,
      ``created_by`` — these are entity identity / type-discriminator
      columns and never change.
    * ``last_fired_at`` — only the trigger evaluator can advance this.
    """
    trigger_repo = SQLModelTriggerRepository(session)
    trigger = await trigger_repo.get(trigger_id)
    if trigger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger not found: {trigger_id}",
        )
    if trigger.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this trigger",
        )

    now = datetime.now(UTC)
    updated = trigger

    # Parse the optional mode early so we can fold it into the same
    # reconstruction pass below (avoids an extra entity rebuild when both
    # mode and other fields change in the same PATCH).
    mode_override: TriggerInvocationMode | None = None
    if request.mode is not None:
        mode_override = _parse_invocation_mode(request.mode)

    # Apply non-status updates first via dataclasses.replace-equivalent
    # so the entity's __post_init__ re-validates the new values. We
    # reconstruct via the dataclass constructor to keep the path explicit.
    if (
        request.agent_prompt is not None
        or request.cooldown_seconds is not None
        or request.priority is not None
        or request.condition_params is not None
        or mode_override is not None
    ):
        new_condition_params = updated.condition_params
        if request.condition_params is not None:
            try:
                new_condition_params = params_from_dict(
                    updated.condition_type, request.condition_params
                )
            except InvalidTriggerError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc

        try:
            updated = StrategyConditionTrigger(
                id=updated.id,
                activation_id=updated.activation_id,
                user_id=updated.user_id,
                condition_type=updated.condition_type,
                condition_params=new_condition_params,
                agent_prompt=(
                    request.agent_prompt
                    if request.agent_prompt is not None
                    else updated.agent_prompt
                ),
                cooldown_seconds=(
                    request.cooldown_seconds
                    if request.cooldown_seconds is not None
                    else updated.cooldown_seconds
                ),
                priority=(
                    request.priority
                    if request.priority is not None
                    else updated.priority
                ),
                default_api_key_id=updated.default_api_key_id,
                expires_at=updated.expires_at,
                status=updated.status,
                last_fired_at=updated.last_fired_at,
                created_at=updated.created_at,
                created_by=updated.created_by,
                updated_at=now,
                mode=mode_override if mode_override is not None else updated.mode,
            )
        except InvalidTriggerError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    # Apply the status transition last so it observes any updated fields
    # in the same persisted entity (avoids two saves).
    if request.status is not None:
        try:
            target_status = TriggerStatus(request.status)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid status: '{request.status}'. PATCH accepts only "
                    "ACTIVE (resume) or PAUSED (pause)."
                ),
            ) from exc

        # Per Phase-F design Q3, terminal-state lift via PATCH is
        # rejected. The user's path to re-enable a disabled trigger is
        # to delete + recreate.
        if target_status in {
            TriggerStatus.EXPIRED,
            TriggerStatus.MANUALLY_DISABLED,
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "PATCH cannot transition a trigger to a terminal state. "
                    "Use DELETE /triggers/{id} for soft-delete (EXPIRED), "
                    "or POST /triggers/disable-all for the per-user kill "
                    "switch (MANUALLY_DISABLED)."
                ),
            )

        # Reject re-enabling a MANUALLY_DISABLED trigger via PATCH —
        # documented lift path is "delete and recreate".
        if updated.status is TriggerStatus.MANUALLY_DISABLED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Cannot transition a MANUALLY_DISABLED trigger via PATCH. "
                    "MANUALLY_DISABLED is terminal — delete and recreate the "
                    "trigger instead (Phase-F design Q3)."
                ),
            )
        if updated.status is TriggerStatus.EXPIRED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Cannot transition an EXPIRED trigger via PATCH. "
                    "EXPIRED is terminal — create a new trigger instead."
                ),
            )

        try:
            if target_status is TriggerStatus.PAUSED:
                updated = updated.pause(at=now)
            elif target_status is TriggerStatus.ACTIVE:
                updated = updated.resume(at=now)
        except InvalidTriggerError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    await trigger_repo.save(updated)
    logger.info(
        "Trigger updated",
        trigger_id=str(trigger_id),
        new_status=updated.status.value,
    )
    return _trigger_to_response(updated)


@triggers_router.delete(
    "/{trigger_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_trigger(
    trigger_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> None:
    """Soft-delete a trigger.

    Per Phase-F design §1.1 the row stays so the fire-log endpoint can
    render history; the trigger transitions to ``EXPIRED`` (terminal).
    The entity's :meth:`expire` requires ``expires_at`` to be set and
    lapsed, so this route bypasses it via direct construction — it's
    semantically "user-driven termination", not "evaluator saw expiry."

    204 on success. 403 when the caller doesn't own the trigger.
    """
    trigger_repo = SQLModelTriggerRepository(session)
    trigger = await trigger_repo.get(trigger_id)
    if trigger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger not found: {trigger_id}",
        )
    if trigger.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this trigger",
        )

    if trigger.status in {
        TriggerStatus.EXPIRED,
        TriggerStatus.MANUALLY_DISABLED,
    }:
        # Already terminal — DELETE is idempotent.
        return None

    now = datetime.now(UTC)
    # User-driven soft-delete: the row keeps an ``expires_at`` set to
    # "now" so the entity's terminal-state invariant (EXPIRED requires
    # a non-null lapsed expires_at) holds. ``last_fired_at`` and
    # ``created_at`` are preserved so the audit trail stays intact.
    try:
        terminated = StrategyConditionTrigger(
            id=trigger.id,
            activation_id=trigger.activation_id,
            user_id=trigger.user_id,
            condition_type=trigger.condition_type,
            condition_params=trigger.condition_params,
            agent_prompt=trigger.agent_prompt,
            cooldown_seconds=trigger.cooldown_seconds,
            priority=trigger.priority,
            default_api_key_id=trigger.default_api_key_id,
            expires_at=now,
            status=TriggerStatus.EXPIRED,
            last_fired_at=trigger.last_fired_at,
            created_at=trigger.created_at,
            created_by=trigger.created_by,
            updated_at=now,
            mode=trigger.mode,
        )
    except InvalidTriggerError as exc:  # pragma: no cover — defensive
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await trigger_repo.save(terminated)
    logger.info(
        "Trigger soft-deleted (transitioned to EXPIRED)",
        trigger_id=str(trigger_id),
    )
    return None


@triggers_router.get(
    "/{trigger_id}/fires",
    response_model=PaginatedResponse[TriggerFireResponse],
)
async def list_fires_for_trigger(
    trigger_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    limit: int = Query(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Maximum number of fire records to return (1-100, default 20).",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of fire records to skip for pagination (default 0).",
    ),
) -> PaginatedResponse[TriggerFireResponse]:
    """List the trigger's fire-log records (newest-first), paginated.

    Ownership: 403 when the caller doesn't own the trigger. The fire
    repository itself is owner-agnostic (a fire is identified by trigger
    + activation), so the trigger-side check is the ownership boundary.
    """
    trigger_repo = SQLModelTriggerRepository(session)
    fire_repo = SQLModelTriggerFireRepository(session)

    trigger = await trigger_repo.get(trigger_id)
    if trigger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger not found: {trigger_id}",
        )
    if trigger.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this trigger's fires",
        )

    records = await fire_repo.list_for_trigger(trigger_id, limit=limit, offset=offset)
    total = await fire_repo.count_for_trigger(trigger_id)
    items = [_fire_to_response(r) for r in records]
    return build_paginated_response(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
