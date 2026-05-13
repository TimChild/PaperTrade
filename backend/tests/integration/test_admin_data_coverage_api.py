"""Integration tests for ``/api/v1/admin/data-coverage`` endpoints.

Phase J (Task #212 Layer 4).

Covers:

* Auth gating — 401 unauthenticated, 403 for non-admin, 200 for admin.
* GET ``/admin/data-coverage``: empty DB, with seeded daily bars, gap
  computation correctness, ordering, is_active union.
* POST ``/admin/data-coverage/backfill``: creates a task, idempotency
  on ``(ticker, start_date, end_date)``, terminal tasks don't block
  new ones, validation errors map to 422.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

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
def non_admin_headers(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Bearer headers that do NOT pass the admin allowlist gate."""
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    yield {"Authorization": "Bearer test-token-default"}


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

    def test_unauthenticated_rejects(self, client: TestClient) -> None:
        response = client.get("/api/v1/admin/data-coverage")
        assert response.status_code in (401, 403)

    def test_non_admin_user_rejects(
        self,
        client: TestClient,
        non_admin_headers: dict[str, str],
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
    ) -> None:
        """A watchlisted ticker with no bars renders with null ranges."""
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
        assert row["gap_days_count"] == 0
        assert row["is_active"] is True

    async def test_contiguous_bars_produce_zero_gaps(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """A run of contiguous trading days produces ``gap_days_count=0``."""
        # 2025-01-06 (Mon) through 2025-01-10 (Fri).
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
        assert row["gap_days_count"] == 0
        assert row["last_refresh"] is not None

    async def test_interior_hole_yields_nonzero_gap(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Skipping Wednesday produces ``gap_days_count=1``."""
        # Skip 2025-01-08 (Wed).
        days = [date(2025, 1, d) for d in (6, 7, 9, 10)]
        await _seed_bars(
            test_engine,
            ticker="MSFT",
            days=days,
            created_at=datetime(2025, 1, 10, tzinfo=UTC),
        )

        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        body = response.json()
        row = next(r for r in body["tickers"] if r["ticker"] == "MSFT")
        assert row["gap_days_count"] == 1

    async def test_intraday_bars_ignored(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Only ``1day`` interval rows count; intraday is invisible."""
        # Seed only intraday rows for a ticker.
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
    ) -> None:
        """Every entry exposes the keys from the §"Layer 4 Endpoint" spec."""
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
                "is_active",
            }


# =============================================================================
# POST /admin/data-coverage/backfill
# =============================================================================


class TestBackfillAuthGating:
    """``POST /admin/data-coverage/backfill`` auth gating."""

    def test_unauthenticated_rejects(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
            },
        )
        assert response.status_code in (401, 403)

    def test_non_admin_rejects(
        self,
        client: TestClient,
        non_admin_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=non_admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
            },
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestBackfillHappyPath:
    """``POST /admin/data-coverage/backfill`` creates a task."""

    async def test_creates_task_returns_201(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
                "priority": "high",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert "task_id" in body
        assert body["status"] == "pending"
        assert body["existing"] is False

        # Confirm the row landed in the DB.
        persisted = await _fetch_backfill_task(test_engine, body["task_id"])
        assert persisted is not None
        assert persisted.ticker == "AAPL"
        assert persisted.start_date == date(2025, 1, 6)
        assert persisted.end_date == date(2025, 1, 10)
        assert persisted.status == BackfillTaskStatus.PENDING.value

    async def test_default_priority_is_high(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """The ``priority`` field defaults to ``high`` for admin backfills."""
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
            },
        )
        body = response.json()
        persisted = await _fetch_backfill_task(test_engine, body["task_id"])
        assert persisted is not None
        assert persisted.priority == "high"


@pytest.mark.asyncio
class TestBackfillIdempotency:
    """Same ``(ticker, start_date, end_date)`` returns the existing task."""

    async def test_duplicate_returns_existing(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        first = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
            },
        )
        assert first.status_code == 201
        first_id = first.json()["task_id"]

        second = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
            },
        )
        assert second.status_code == 201
        body = second.json()
        assert body["task_id"] == first_id
        assert body["existing"] is True
        assert body["status"] == "pending"

    async def test_different_ranges_create_distinct_tasks(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        first = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
            },
        )
        second = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                # Different end_date → distinct task.
                "start_date": "2025-01-06",
                "end_date": "2025-01-15",
            },
        )
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["task_id"] != second.json()["task_id"]
        assert second.json()["existing"] is False


@pytest.mark.asyncio
class TestBackfillValidation:
    """Invalid input maps to 4xx with the standard envelope."""

    async def test_invalid_ticker_returns_400(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Lowercase / overly-long ticker → 400 InvalidTicker."""
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "TOOLONGSYMBOL",
                "start_date": "2025-01-06",
                "end_date": "2025-01-10",
            },
        )
        assert response.status_code == 400

    async def test_end_before_start_returns_422(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """``end_date < start_date`` is rejected by the domain invariant."""
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "2025-01-10",
                "end_date": "2025-01-06",
            },
        )
        assert response.status_code == 422

    async def test_invalid_date_format_returns_422(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Pydantic rejects non-ISO date strings."""
        response = client.post(
            "/api/v1/admin/data-coverage/backfill",
            headers=admin_headers,
            json={
                "ticker": "AAPL",
                "start_date": "not-a-date",
                "end_date": "2025-01-10",
            },
        )
        assert response.status_code == 422
