"""Admin job-health endpoint (Phase J — Task #212 Layer 1).

Mounted under ``/admin/jobs`` so admin / observability operations are
visible as their own URL family rather than being scattered through the
user-facing namespace.

Authentication: Clerk admin user only — uses :data:`AdminUserDep` from
:mod:`zebu.adapters.inbound.api.dependencies`. Matches the pattern used
by ``/admin/triggers``.

Exposes one endpoint:

* ``GET /admin/jobs/health`` — returns the latest audit row for every
  scheduled job, with a computed ``is_stale`` flag based on each job's
  expected cadence.

The thresholds live in :data:`JOB_HEALTH_THRESHOLDS` — a per-job
mapping of expected cadence (seconds) plus a stale threshold (default
``2× cadence`` per the task spec, so a daily job is stale at 48h and a
15-minute job is stale at 30 min). Adding a new scheduled job means
appending an entry to this mapping; the endpoint surfaces the row
automatically.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from zebu.adapters.inbound.api.dependencies import AdminUserDep
from zebu.adapters.outbound.database.job_execution_repository import (
    SQLModelJobExecutionRepository,
)
from zebu.domain.value_objects.job_execution import JobExecution
from zebu.infrastructure.database import SessionDep

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])

# Module-level structlog logger. Picks up the actor identity bound by
# get_current_user automatically — the admin user's clerk_user_id is on
# every log line emitted by this module.
logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Cadence + stale-threshold configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JobHealthThreshold:
    """Cadence + stale threshold for one scheduled job.

    Attributes:
        expected_cadence_seconds: Nominal time between runs. Daily =
            86400s, hourly = 3600s, every-15-min = 900s.
        stale_threshold_seconds: How long ``now - last_run`` may
            exceed before the operator should investigate. Defaults to
            ``2× expected_cadence_seconds`` per the task spec.
    """

    expected_cadence_seconds: int
    stale_threshold_seconds: int


def _threshold(expected_cadence_seconds: int) -> JobHealthThreshold:
    """Build a threshold with the default ``2× cadence`` stale window."""
    return JobHealthThreshold(
        expected_cadence_seconds=expected_cadence_seconds,
        stale_threshold_seconds=expected_cadence_seconds * 2,
    )


# Per-job thresholds. Adding a new scheduled job means appending an
# entry here; the endpoint surfaces the audit row automatically. The
# crons themselves live in :mod:`zebu.infrastructure.scheduler`.
JOB_HEALTH_THRESHOLDS: Mapping[str, JobHealthThreshold] = {
    # Daily price refresh — cron "0 0 * * *" (midnight UTC).
    "refresh_active_stocks": _threshold(86_400),
    # Daily portfolio snapshot — cron "0 0 * * *" (midnight UTC).
    "calculate_daily_snapshots": _threshold(86_400),
    # Daily Mon-Fri live strategy execution — cron "30 0 * * 1-5".
    "execute_active_strategies": _threshold(86_400),
    # Trigger evaluator — the dominant cadence is the market-hours
    # cron "*/15 14-20 * * 1-5" → 900s. The off-hours cron is every 6
    # hours; using the tighter market-hours cadence as the cadence
    # source biases toward "alert sooner" during market hours, which
    # is when drawdown / volatility triggers actually matter.
    "evaluate_triggers": _threshold(900),
}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class JobHealthEntry(BaseModel):
    """Per-job entry in the health response."""

    job_name: str = Field(description="Stable scheduler-handler name.")
    last_run: str | None = Field(
        description=(
            "ISO8601 UTC timestamp of the most-recent run's ``started_at``, "
            "or null when the job has never been seen."
        ),
    )
    last_status: str | None = Field(
        description=(
            "Lifecycle stage of the most-recent run: ``RUNNING`` / "
            "``SUCCEEDED`` / ``FAILED``. Null when the job has never run."
        ),
    )
    duration_seconds: float | None = Field(
        description=(
            "How long the most-recent run took, in seconds. Computed "
            "from ``finished_at - started_at``. Null while the run is "
            "still ``RUNNING`` or never executed."
        ),
    )
    expected_cadence_seconds: int = Field(
        description="Nominal time between runs for this job (seconds).",
    )
    is_stale: bool = Field(
        description=(
            "True when ``now - last_run > stale_threshold_seconds`` or "
            "the job has never run."
        ),
    )
    stale_threshold_seconds: int = Field(
        description=(
            "How long ``now - last_run`` may exceed before the job is "
            "considered stale. Defaults to ``2× expected_cadence``."
        ),
    )
    error_message: str | None = Field(
        default=None,
        description=(
            "Truncated exception message captured by the audit "
            "decorator when ``last_status=FAILED``. Null otherwise."
        ),
    )


class JobsHealthResponse(BaseModel):
    """Response body for ``GET /admin/jobs/health``."""

    jobs: list[JobHealthEntry]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _duration_seconds(execution: JobExecution) -> float | None:
    """Return ``finished_at - started_at`` in seconds, or ``None`` if running."""
    if execution.finished_at is None:
        return None
    delta = execution.finished_at - execution.started_at
    return delta.total_seconds()


def _is_stale(
    execution: JobExecution | None,
    threshold: JobHealthThreshold,
    *,
    now: datetime,
) -> bool:
    """Decide whether a job is stale.

    A job is stale when:

    * No audit row exists (the job has never been seen).
    * The last run started more than ``stale_threshold_seconds`` ago.

    A run still in ``RUNNING`` state isn't itself "stale" until the
    threshold elapses — a long-running daily backfill is normal.
    """
    if execution is None:
        return True
    age_seconds = (now - execution.started_at).total_seconds()
    return age_seconds > threshold.stale_threshold_seconds


def _build_entry(
    job_name: str,
    execution: JobExecution | None,
    threshold: JobHealthThreshold,
    *,
    now: datetime,
) -> JobHealthEntry:
    """Construct the per-job response entry from the audit row."""
    if execution is None:
        return JobHealthEntry(
            job_name=job_name,
            last_run=None,
            last_status=None,
            duration_seconds=None,
            expected_cadence_seconds=threshold.expected_cadence_seconds,
            is_stale=True,
            stale_threshold_seconds=threshold.stale_threshold_seconds,
            error_message=None,
        )
    return JobHealthEntry(
        job_name=job_name,
        last_run=execution.started_at.isoformat(),
        last_status=execution.status.value,
        duration_seconds=_duration_seconds(execution),
        expected_cadence_seconds=threshold.expected_cadence_seconds,
        is_stale=_is_stale(execution, threshold, now=now),
        stale_threshold_seconds=threshold.stale_threshold_seconds,
        error_message=execution.error_message,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=JobsHealthResponse,
)
async def admin_jobs_health(
    admin_user_id: AdminUserDep,
    session: SessionDep,
) -> JobsHealthResponse:
    """Latest audit row per scheduled job, with a computed ``is_stale`` flag.

    Per task #212 Layer 1: operator polls this endpoint to know whether
    each scheduled job (price refresh, snapshot calculation, strategy
    execution, trigger evaluation) is still running on its expected
    cadence. A ``is_stale=true`` entry indicates the cron has lapsed
    and downstream features (backtests, activations) may begin to fail
    on missing data.

    Auth: Clerk admin only (``AdminUserDep`` reads the env-driven
    ``ADMIN_USER_IDS`` allowlist).

    Returns the entry for every job in :data:`JOB_HEALTH_THRESHOLDS`,
    in the same iteration order. A job that has never run yields
    ``last_run=None`` + ``is_stale=true``.
    """
    repo = SQLModelJobExecutionRepository(session)
    now = datetime.now(UTC)

    entries: list[JobHealthEntry] = []
    for job_name, threshold in JOB_HEALTH_THRESHOLDS.items():
        execution = await repo.latest(job_name)
        entries.append(_build_entry(job_name, execution, threshold, now=now))

    logger.info(
        "admin_jobs_health_polled",
        admin_user_id=str(admin_user_id),
        jobs_total=len(entries),
        jobs_stale=sum(1 for e in entries if e.is_stale),
    )
    return JobsHealthResponse(jobs=entries)
