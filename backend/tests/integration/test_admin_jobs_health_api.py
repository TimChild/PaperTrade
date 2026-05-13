"""Integration tests for ``GET /api/v1/admin/jobs/health``.

Phase J (Task #212 Layer 1). Covers:

* Auth gating — 401 unauthenticated, 403 for non-admin Clerk users, 200
  for admin Clerk users.
* Empty DB → every job listed with ``is_stale=true`` and ``last_run=null``.
* Recent successful run → ``is_stale=false``, ``duration_seconds`` set.
* Stale row → ``is_stale=true``.
* Failed run → ``last_status=FAILED`` with the captured error message.

The test client uses the SQLite in-memory DB wired in ``conftest.py``;
we seed audit rows by writing through the SQL repository directly to
bypass the decorator's session-isolated commit path.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.job_execution_repository import (
    SQLModelJobExecutionRepository,
)
from zebu.adapters.outbound.database.models import JobExecutionModel
from zebu.domain.value_objects.job_execution import JobExecution
from zebu.domain.value_objects.job_execution_status import JobExecutionStatus

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture
def admin_headers(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Bearer headers that pass the admin allowlist gate."""
    monkeypatch.setenv("ADMIN_USER_IDS", "test-user-default")
    yield {"Authorization": "Bearer test-token-default"}


@pytest.fixture
def non_admin_headers(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Bearer headers that do NOT pass the admin allowlist gate."""
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    yield {"Authorization": "Bearer test-token-default"}


async def _write_row(
    test_engine: AsyncEngine,
    *,
    job_name: str,
    started_at: datetime,
    finished_at: datetime | None,
    status: JobExecutionStatus,
    error_message: str | None = None,
) -> None:
    """Seed one audit row directly via the SQL repo."""
    from uuid import uuid4

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        repo = SQLModelJobExecutionRepository(session)
        # We can't go through record_start / record_finish because they
        # stamp their own timestamps. Use the model layer directly.
        execution = JobExecution(
            id=uuid4(),
            job_name=job_name,
            started_at=started_at,
            status=JobExecutionStatus.RUNNING,
            metadata={},
        )
        model = JobExecutionModel.from_domain(execution)
        session.add(model)
        await session.commit()
        if finished_at is not None:
            terminal = JobExecution(
                id=execution.id,
                job_name=job_name,
                started_at=started_at,
                finished_at=finished_at,
                status=status,
                error_message=error_message,
                metadata={"duration_seconds": "0.1"},
            )
            await repo.record_finish(
                terminal,
                status=status,
                error_message=error_message,
                metadata={"duration_seconds": "0.1"},
            )
            await session.commit()
        # Sanity: the repo helper is exercised by other tests.
        _ = repo


class TestAuthGating:
    """``GET /admin/jobs/health`` auth gating."""

    def test_unauthenticated_rejects(
        self,
        client: "TestClient",
    ) -> None:
        response = client.get("/api/v1/admin/jobs/health")
        assert response.status_code in (401, 403)

    def test_non_admin_user_rejects(
        self,
        client: "TestClient",
        non_admin_headers: dict[str, str],
    ) -> None:
        response = client.get(
            "/api/v1/admin/jobs/health",
            headers=non_admin_headers,
        )
        assert response.status_code == 403

    def test_admin_user_succeeds(
        self,
        client: "TestClient",
        admin_headers: dict[str, str],
    ) -> None:
        response = client.get(
            "/api/v1/admin/jobs/health",
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text


class TestEmptyDatabase:
    """Empty DB → every configured job appears stale with no last_run."""

    def test_lists_every_configured_job(
        self,
        client: "TestClient",
        admin_headers: dict[str, str],
    ) -> None:
        response = client.get(
            "/api/v1/admin/jobs/health",
            headers=admin_headers,
        )
        body = response.json()
        names = [entry["job_name"] for entry in body["jobs"]]
        assert "refresh_active_stocks" in names
        assert "calculate_daily_snapshots" in names
        assert "execute_active_strategies" in names
        assert "evaluate_triggers" in names

    def test_never_run_jobs_marked_stale(
        self,
        client: "TestClient",
        admin_headers: dict[str, str],
    ) -> None:
        response = client.get(
            "/api/v1/admin/jobs/health",
            headers=admin_headers,
        )
        for entry in response.json()["jobs"]:
            assert entry["last_run"] is None
            assert entry["last_status"] is None
            assert entry["duration_seconds"] is None
            assert entry["is_stale"] is True


@pytest.mark.asyncio
class TestWithAuditRows:
    """Endpoint reflects seeded audit rows."""

    async def test_recent_success_not_stale(
        self,
        client: "TestClient",
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        now = datetime.now(UTC)
        await _write_row(
            test_engine,
            job_name="refresh_active_stocks",
            started_at=now - timedelta(minutes=5),
            finished_at=now - timedelta(minutes=5) + timedelta(seconds=1),
            status=JobExecutionStatus.SUCCEEDED,
        )

        response = client.get(
            "/api/v1/admin/jobs/health",
            headers=admin_headers,
        )
        body = response.json()
        entry = _find_entry(body, "refresh_active_stocks")
        assert entry["last_status"] == "SUCCEEDED"
        assert entry["last_run"] is not None
        assert entry["duration_seconds"] is not None
        assert entry["is_stale"] is False

    async def test_old_success_marked_stale(
        self,
        client: "TestClient",
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """A daily job (cadence 86400s, threshold 172800s) marked stale at 3d old."""
        now = datetime.now(UTC)
        old = now - timedelta(days=3)
        await _write_row(
            test_engine,
            job_name="refresh_active_stocks",
            started_at=old,
            finished_at=old + timedelta(seconds=1),
            status=JobExecutionStatus.SUCCEEDED,
        )

        response = client.get(
            "/api/v1/admin/jobs/health",
            headers=admin_headers,
        )
        entry = _find_entry(response.json(), "refresh_active_stocks")
        assert entry["is_stale"] is True

    async def test_failed_row_surfaces_error_message(
        self,
        client: "TestClient",
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        now = datetime.now(UTC)
        await _write_row(
            test_engine,
            job_name="evaluate_triggers",
            started_at=now - timedelta(minutes=1),
            finished_at=now - timedelta(minutes=1) + timedelta(seconds=2),
            status=JobExecutionStatus.FAILED,
            error_message="upstream timeout",
        )

        response = client.get(
            "/api/v1/admin/jobs/health",
            headers=admin_headers,
        )
        entry = _find_entry(response.json(), "evaluate_triggers")
        assert entry["last_status"] == "FAILED"
        assert entry["error_message"] == "upstream timeout"

    async def test_response_schema_matches_spec(
        self,
        client: "TestClient",
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Every entry exposes the keys the task spec promises."""
        now = datetime.now(UTC)
        await _write_row(
            test_engine,
            job_name="refresh_active_stocks",
            started_at=now - timedelta(minutes=1),
            finished_at=now - timedelta(minutes=1) + timedelta(seconds=1),
            status=JobExecutionStatus.SUCCEEDED,
        )

        response = client.get(
            "/api/v1/admin/jobs/health",
            headers=admin_headers,
        )
        body = response.json()
        # Each entry has every key from the §"Layer 1 Endpoint" spec
        expected_keys = {
            "job_name",
            "last_run",
            "last_status",
            "duration_seconds",
            "expected_cadence_seconds",
            "is_stale",
            "stale_threshold_seconds",
            "error_message",
        }
        for entry in body["jobs"]:
            assert set(entry.keys()) == expected_keys


def _find_entry(body: dict[str, object], job_name: str) -> dict[str, object]:
    """Return the entry for ``job_name`` from a parsed JSON body."""
    jobs = body["jobs"]
    assert isinstance(jobs, list)
    for entry in jobs:
        assert isinstance(entry, dict)
        if entry["job_name"] == job_name:
            return entry
    raise AssertionError(f"No entry for {job_name} in response: {body}")
