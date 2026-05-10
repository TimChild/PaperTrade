"""Admin-wide trigger kill-switch endpoint (Phase F-5).

Mounted under ``/admin/triggers`` so admin / kill-switch operations are
visible as their own URL family rather than being scattered through the
user-facing ``/triggers`` namespace.

Authentication: Clerk admin user only — uses :data:`AdminUserDep` from
:mod:`zebu.adapters.inbound.api.dependencies`. Per Phase-F design §4.3.2
the operation is logged at WARN level with the admin user ID.
"""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter

from zebu.adapters.inbound.api.dependencies import AdminUserDep
from zebu.adapters.inbound.api.schemas import DisableAllResponse
from zebu.adapters.outbound.database.strategy_condition_trigger_repository import (
    SQLModelTriggerRepository,
)
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/admin/triggers", tags=["admin-triggers"])

# Module-level structlog logger. Picks up the actor identity bound by
# get_current_user automatically — the admin user's clerk_user_id is on
# every log line emitted by this module.
logger = structlog.get_logger(__name__)


@router.post(
    "/disable-all",
    response_model=DisableAllResponse,
)
async def admin_disable_all_triggers(
    admin_user_id: AdminUserDep,
    session: SessionDep,
) -> DisableAllResponse:
    """Admin-wide kill switch — disable every non-terminal trigger across all users.

    Sets every ACTIVE / PAUSED trigger across the whole DB to
    :class:`TriggerStatus.MANUALLY_DISABLED`. Idempotent.

    Per Phase-F design §4.3.3, ``MANUALLY_DISABLED`` is terminal. To
    re-enable a disabled trigger, delete and recreate it.

    Logged at WARN level with the admin user ID. Auth: Clerk admin only
    (the env-driven ``ADMIN_USER_IDS`` allowlist gate via
    :data:`AdminUserDep`).
    """
    trigger_repo = SQLModelTriggerRepository(session)
    now = datetime.now(UTC)
    disabled = await trigger_repo.disable_all(at=now)

    logger.warning(
        "Admin-wide kill switch invoked — all triggers disabled",
        admin_user_id=str(admin_user_id),
        disabled_count=disabled,
    )

    return DisableAllResponse(disabled_count=disabled)
