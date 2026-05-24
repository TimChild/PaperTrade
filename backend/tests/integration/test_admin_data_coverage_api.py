"""Integration tests for ``/api/v1/admin/data-coverage`` endpoints.

Phase J (Task #212 Layer 4); Task #215 "catch up" UX rework.

Covers:

* Auth gating — 401 unauthenticated, 403 for non-admin, 200 for admin.
* GET ``/admin/data-coverage``: empty DB, with seeded daily bars,
  gap computation against ``[ZEBU_HISTORY_EPOCH, today]``, ordering,
  is_active union, ``backfill_status`` payload + ``target_epoch``
  echo.
* POST ``/admin/data-coverage/backfill``: creates a task for the
  ``[epoch, today]`` range, idempotency on the computed range,
  rejects bodies that include ``start_date`` / ``end_date`` (the
  pre-Task-215 shape) with 422.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import BackfillTaskModel
from zebu.adapters.outbound.models.price_history import PriceHistoryModel
from zebu.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture
def admin_headers(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Bearer headers that pass the admin allowlist gate.

    The in-memory auth adapter resolves any non-empty Bearer token to
    user_id ``test-user-default`` by default — setting that user in
    ``ADMIN_USER_IDS`` flips the request to admin-authenticated.
    """
    monkeypatch.setenv("ADMIN_USER_IDS", "test-user-default")
    yield {"Authorization": "Bearer test-token-default"}


@pytest.fixture
def no_immediate_drain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable the fire-and-forget post-create drain so DB-state
    assertions stay deterministic.

    Without this, the background task ``_run_drain_background`` may
    transition the freshly-created ``BackfillTask`` from PENDING to
    RUNNING / SUCCEEDED / FAILED before the assertion runs against the
    DB, depending on how the asyncio loop interleaves the test's read
    with the scheduled drain. Tests that explicitly exercise the drain
    behaviour should NOT use this fixture.
    """
    from zebu.adapters.inbound.api import admin_data_coverage

    monkeypatch.setattr(
        admin_data_coverage,
        "_schedule_immediate_drain",
        lambda **_: None,
    )


@pytest.fixture
def non_admin_headers(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Bearer headers that do NOT pass the admin allowlist gate."""
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    yield {"Authorization": "Bearer test-token-default"}


@pytest.fixture
def pinned_epoch(monkeypatch: pytest.MonkeyPatch) -> str:
    """Pin ``ZEBU_HISTORY_EPOCH`` to a deterministic date for the test.

    Uses a date well in the past so ``end_date`` (today, computed by
    the handler) is always >= the epoch — no risk of triggering the
    domain's ``end_date >= start_date`` invariant.
    """
    epoch = "2015-01-01"
    monkeypatch.setenv("ZEBU_HISTORY_EPOCH", epoch)
    return epoch


async def _seed_bars(
    engine: AsyncEngine,
    *,
    ticker: str,
    days: list[date],
    created_at: datetime,
    interval: str = "1day",
) -> None:
    """Seed one ``price_history`` row per supplied date.

    Uses a separate session and an explicit commit so the row is
    visible to the FastAPI TestClient's per-request sessions.
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for d in days:
            session.add(
                PriceHistoryModel(
                    ticker=ticker,
                    price_amount=Decimal("100.00"),
                    price_currency="USD",
                    timestamp=datetime(d.year, d.month, d.day),
                    source="test",
                    interval=interval,
                    created_at=created_at.replace(tzinfo=None),
                )
            )
        await session.commit()


async def _seed_watchlist(engine: AsyncEngine, *, ticker: str) -> None:
    """Add an active watchlist row."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(TickerWatchlistModel(ticker=ticker, is_active=True))
        await session.commit()


async def _seed_backfill_task(
    engine: AsyncEngine,
    *,
    ticker: str,
    status: BackfillTaskStatus,
    start_date: date,
    end_date: date,
    created_at: datetime,
    finished_at: datetime | None = None,
    error_message: str | None = None,
) -> None:
    """Insert a backfill task row directly."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(
            BackfillTaskModel(
                id=uuid4(),
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                priority="high",
                status=status.value,
                created_at=created_at.replace(tzinfo=None)
                if created_at.tzinfo
                else created_at,
                finished_at=(
                    finished_at.replace(tzinfo=None)
                    if finished_at is not None and finished_at.tzinfo
                    else finished_at
                ),
                error_message=error_message,
            )
        )
        await session.commit()


async def _fetch_backfill_task(
    engine: AsyncEngine, task_id: str
) -> BackfillTaskModel | None:
    """Load a backfill task by id directly from the DB."""
    from uuid import UUID

    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await session.get(BackfillTaskModel, UUID(task_id))


# =============================================================================
# GET /admin/data-coverage — auth gating
# =============================================================================


class TestGetAuthGating:
    """``GET /admin/data-coverage`` rejects non-admin callers."""

    def test_unauthenticated_rejects(
        self, client: TestClient, pinned_epoch: str
    ) -> None:
        response = client.get("/api/v1/admin/data-coverage")
        assert response.status_code in (401, 403)

    def test_non_admin_user_rejects(
        self,
        client: TestClient,
        non_admin_headers: dict[str, str],
        pinned_epoch: str,
    ) -> None:
        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=non_admin_headers,
        )
        assert response.status_code == 403

    def test_admin_user_succeeds(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        pinned_epoch: str,
    ) -> None:
        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text


# =============================================================================
# GET /admin/data-coverage — happy paths
# =============================================================================


class TestGetEmptyDatabase:
    """Empty DB → empty response."""

    def test_returns_empty_tickers(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        pinned_epoch: str,
    ) -> None:
        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body == {"tickers": []}


@pytest.mark.asyncio
class TestGetWithSeededData:
    """End-to-end behaviour with seeded daily bars + watchlist."""

    async def test_watchlist_only_ticker_visible_with_nulls(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        pinned_epoch: str,
    ) -> None:
        """Watchlist ticker with no bars yields null ranges + echoed epoch."""
        await _seed_watchlist(test_engine, ticker="AAPL")

        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["tickers"]) == 1
        row = body["tickers"][0]
        assert row["ticker"] == "AAPL"
        assert row["coverage_start"] is None
        assert row["coverage_end"] is None
        assert row["last_refresh"] is None
        # With no bars the gap is large (full [epoch, today] trading-day span).
        assert row["gap_days_count"] > 0
        assert row["is_active"] is True
        assert row["target_epoch"] == pinned_epoch
        assert row["backfill_status"] is None

    async def test_contiguous_bars_produce_realistic_gap(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        pinned_epoch: str,
    ) -> None:
        """Bars seeded recently leave a head-gap from epoch up to coverage_start."""
        # Cover a handful of recent trading days. The head-gap (epoch ->
        # bar) means gap_days_count is enormous; we just assert that the
        # query handles it without falling over.
        days = [date(2025, 1, d) for d in (6, 7, 8, 9, 10)]
        await _seed_bars(
            test_engine,
            ticker="AAPL",
            days=days,
            created_at=datetime(2025, 1, 10, tzinfo=UTC),
        )

        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        body = response.json()
        row = next(r for r in body["tickers"] if r["ticker"] == "AAPL")
        assert row["coverage_start"] == "2025-01-06"
        assert row["coverage_end"] == "2025-01-10"
        # Big head-gap from 2015-01-01 to 2025-01-05 + the tail gap to today.
        assert row["gap_days_count"] > 1000
        assert row["last_refresh"] is not None
        assert row["target_epoch"] == pinned_epoch

    async def test_intraday_bars_ignored(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        pinned_epoch: str,
    ) -> None:
        """Only ``1day`` interval rows count; intraday is invisible."""
        await _seed_watchlist(test_engine, ticker="MSFT")
        await _seed_bars(
            test_engine,
            ticker="MSFT",
            days=[date(2025, 1, 6)],
            created_at=datetime(2025, 1, 6, tzinfo=UTC),
            interval="1min",
        )

        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        body = response.json()
        row = next(r for r in body["tickers"] if r["ticker"] == "MSFT")
        # Active via watchlist but zero daily bars → null coverage.
        assert row["coverage_start"] is None
        assert row["coverage_end"] is None
        assert row["is_active"] is True

    async def test_response_keys_match_spec(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        pinned_epoch: str,
    ) -> None:
        """Every entry exposes the full key set from Task #215."""
        await _seed_watchlist(test_engine, ticker="AAPL")
        await _seed_bars(
            test_engine,
            ticker="AAPL",
            days=[date(2025, 1, 6)],
            created_at=datetime(2025, 1, 6, tzinfo=UTC),
        )

        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        body = response.json()
        for row in body["tickers"]:
            assert set(row.keys()) == {
                "ticker",
                "coverage_start",
                "coverage_end",
                "last_refresh",
                "gap_days_count",
                "target_epoch",
                "is_active",
                "backfill_status",
            }

    async def test_backfill_status_pending_surfaces(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        pinned_epoch: str,
    ) -> None:
        """A PENDING task on a ticker shows up in the response payload."""
        await _seed_watchlist(test_engine, ticker="AAPL")
        await _seed_backfill_task(
            test_engine,
            ticker="AAPL",
            status=BackfillTaskStatus.PENDING,
            start_date=date(2015, 1, 1),
            end_date=datetime.now(UTC).date(),
            created_at=datetime.now(UTC) - timedelta(minutes=2),
        )

        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        body = response.json()
        row = next(r for r in body["tickers"] if r["ticker"] == "AAPL")
        assert row["backfill_status"] is not None
        assert row["backfill_status"]["status"] == "pending"
        assert row["backfill_status"]["error_message"] is None
        # task_id and enqueued_at are both present strings.
        assert isinstance(row["backfill_status"]["task_id"], str)
        assert isinstance(row["backfill_status"]["enqueued_at"], str)


# =============================================================================
# POST /admin/data-coverage/backfill
# =============================================================================


class TestBackfillAuthGating:
    """``POST /admin/data-coverage/backfill`` auth gating."""

    def test_unauthenticated_rejects(
        self, client: TestClient, pinned_epoch: str
    ) -> None:
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            json={"ticker": "AAPL"},
        )
        assert response.status_code in (401, 403)

    def test_non_admin_rejects(
        self,
        client: TestClient,
        non_admin_headers: dict[str, str],
        pinned_epoch: str,
    ) -> None:
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=non_admin_headers,
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestBackfillHappyPath:
    """POST creates a task over the canonical ``[epoch, today]`` range."""

    async def test_creates_task_over_epoch_today_range(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        pinned_epoch: str,
        no_immediate_drain: None,
    ) -> None:
        """The handler computes ``[epoch, today]`` from env + clock."""
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert "task_id" in body
        assert body["status"] == "pending"
        assert body["existing"] is False
        assert body["start_date"] == pinned_epoch
        # end_date is today UTC; compare on string form.
        assert body["end_date"] == datetime.now(UTC).date().isoformat()

        # Confirm the row landed in the DB with the expected range.
        persisted = await _fetch_backfill_task(test_engine, body["task_id"])
        assert persisted is not None
        assert persisted.ticker == "AAPL"
        assert persisted.start_date == date.fromisoformat(pinned_epoch)
        assert persisted.end_date == datetime.now(UTC).date()
        assert persisted.status == BackfillTaskStatus.PENDING.value
        # Default priority is HIGH for operator-driven catch-ups.
        assert persisted.priority == "high"


@pytest.mark.asyncio
class TestBackfillIdempotency:
    """Idempotent on ``(ticker, epoch, today)``."""

    async def test_second_call_dedupes(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        pinned_epoch: str,
        no_immediate_drain: None,
    ) -> None:
        first = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert first.status_code == 201
        first_id = first.json()["task_id"]

        second = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert second.status_code == 201
        body = second.json()
        assert body["task_id"] == first_id
        assert body["existing"] is True
        assert body["status"] == "pending"


@pytest.mark.asyncio
class TestBackfillValidation:
    """Invalid input maps to 4xx with the standard envelope."""

    async def test_invalid_ticker_returns_400(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        pinned_epoch: str,
    ) -> None:
        """Lowercase / overly-long ticker → 400 InvalidTicker."""
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "TOOLONGSYMBOL"},
        )
        assert response.status_code == 400

    async def test_rejects_legacy_body_with_start_date(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        pinned_epoch: str,
    ) -> None:
        """Task #215: bodies with ``start_date`` / ``end_date`` are rejected."""
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
            },
        )
        assert response.status_code == 422

    async def test_rejects_legacy_body_with_priority(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        pinned_epoch: str,
    ) -> None:
        """Task #215: priority is server-set; rejecting client overrides too."""
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "AAPL", "priority": "low"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestHistoryEpochEnv:
    """``ZEBU_HISTORY_EPOCH`` env override is honoured."""

    async def test_custom_epoch_drives_backfill_range(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
        no_immediate_drain: None,
    ) -> None:
        """Setting the env to a non-default value flows through to the task row."""
        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2020-06-15")
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["start_date"] == "2020-06-15"

        persisted = await _fetch_backfill_task(test_engine, body["task_id"])
        assert persisted is not None
        assert persisted.start_date == date(2020, 6, 15)


@pytest.mark.asyncio
class TestBackfillImmediateDrain:
    """The operator endpoint schedules a fire-and-forget background
    drain so the freshly-queued task doesn't have to wait for the
    next scheduler firing (midnight UTC, daily).
    """

    async def test_drain_is_scheduled_on_create(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        pinned_epoch: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``_schedule_immediate_drain`` is called once per task creation."""
        from zebu.adapters.inbound.api import admin_data_coverage

        captured: list[dict[str, object]] = []

        def _capture(**kwargs: object) -> None:
            captured.append(kwargs)

        monkeypatch.setattr(
            admin_data_coverage,
            "_schedule_immediate_drain",
            _capture,
        )

        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 201, response.text
        assert len(captured) == 1
        call = captured[0]
        assert str(call["ticker"]) == "AAPL"
        assert call["task_id"] == UUID(response.json()["task_id"])

    async def test_drain_not_scheduled_when_deduping_existing_task(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        pinned_epoch: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Idempotency dedupe returns the existing task without
        re-scheduling a drain — the scheduler already has the task in
        its pickup queue from the first POST.
        """
        from zebu.adapters.inbound.api import admin_data_coverage

        first = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert first.status_code == 201

        captured: list[dict[str, object]] = []

        def _capture(**kwargs: object) -> None:
            captured.append(kwargs)

        monkeypatch.setattr(
            admin_data_coverage,
            "_schedule_immediate_drain",
            _capture,
        )

        second = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert second.status_code == 201
        assert second.json()["existing"] is True
        assert captured == []  # no second drain scheduled

    async def test_invalid_epoch_raises_runtime_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Garbage in ``ZEBU_HISTORY_EPOCH`` is rejected at config-read time.

        FastAPI's exception handler chain translates the ``RuntimeError``
        into a 500 response in real deployments — the TestClient
        propagates the original exception rather than masking it as 500,
        so we assert against the dependency function directly. This
        keeps the misconfiguration loud (no silent fallback) and the
        test fast.
        """
        from zebu.adapters.inbound.api.dependencies import get_history_epoch

        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "not-a-date")
        try:
            get_history_epoch()
        except RuntimeError as exc:
            assert "ZEBU_HISTORY_EPOCH" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError for invalid epoch")
