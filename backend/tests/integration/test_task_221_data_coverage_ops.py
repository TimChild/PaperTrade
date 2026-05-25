"""Integration tests for Task #221 data-coverage admin ops.

Covers:

1. ``POST /admin/watchlist`` — 422 when ticker validator returns False;
   500 when validator raises MarketDataUnavailableError; 201 success
   when validator returns True.
2. ``DELETE /admin/data-coverage/tickers/{ticker}`` — cascade delete:
   watchlist rows gone, price_history rows gone, non-terminal backfill
   tasks marked FAILED. 204 on success. 404 when nothing to delete.
3. ``GET /admin/data-coverage`` — ``gap_ranges`` field is present and
   correctly populated.
4. ``ZEBU_HISTORY_MAX_LOOKBACK_DAYS`` env knob — effective epoch is
   clamped correctly.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.models import BackfillTaskModel
from zebu.adapters.outbound.models.price_history import PriceHistoryModel
from zebu.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel
from zebu.application.exceptions import MarketDataUnavailableError
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.ticker import Ticker
from zebu.main import app

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_headers(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Bearer headers that pass the admin allowlist gate."""
    monkeypatch.setenv("ADMIN_USER_IDS", "test-user-default")
    yield {"Authorization": "Bearer test-token-default"}


@pytest.fixture
def no_immediate_drain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable post-create drain so DB assertions stay deterministic."""
    from zebu.adapters.inbound.api import admin_data_coverage

    monkeypatch.setattr(
        admin_data_coverage,
        "_schedule_immediate_drain",
        lambda **_: None,
    )


# ---------------------------------------------------------------------------
# Stub validators
# ---------------------------------------------------------------------------


class _RejectingValidator:
    """Always returns False — simulates an unrecognised ticker."""

    async def is_recognised(self, ticker: Ticker) -> bool:  # noqa: ARG002
        return False


class _ErroringValidator:
    """Always raises MarketDataUnavailableError — simulates provider down."""

    async def is_recognised(self, ticker: Ticker) -> bool:
        raise MarketDataUnavailableError(
            f"Alpha Vantage is unavailable for {ticker.symbol}"
        )


class _AcceptingValidator:
    """Always returns True — simulates a known ticker."""

    async def is_recognised(self, ticker: Ticker) -> bool:  # noqa: ARG002
        return True


# ---------------------------------------------------------------------------
# Seed helpers (async — run inside async test methods)
# ---------------------------------------------------------------------------


async def _seed_watchlist(
    engine: AsyncEngine, *, ticker: str, is_active: bool = True
) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(TickerWatchlistModel(ticker=ticker, is_active=is_active))
        await session.commit()


async def _seed_bars(
    engine: AsyncEngine,
    *,
    ticker: str,
    days: list[date],
) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for d in days:
            session.add(
                PriceHistoryModel(
                    ticker=ticker,
                    price_amount=Decimal("100.00"),
                    price_currency="USD",
                    timestamp=datetime(d.year, d.month, d.day),
                    source="test",
                    interval="1day",
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
        await session.commit()


async def _seed_backfill_task(
    engine: AsyncEngine,
    *,
    ticker: str,
    status: BackfillTaskStatus,
) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(
            BackfillTaskModel(
                id=uuid4(),
                ticker=ticker,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                priority="high",
                status=status.value,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await session.commit()


async def _fetch_watchlist_rows(
    engine: AsyncEngine, ticker: str
) -> list[TickerWatchlistModel]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await session.exec(
            select(TickerWatchlistModel).where(TickerWatchlistModel.ticker == ticker)
        )
        return list(result.all())


async def _fetch_price_rows(
    engine: AsyncEngine, ticker: str
) -> list[PriceHistoryModel]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await session.exec(
            select(PriceHistoryModel).where(PriceHistoryModel.ticker == ticker)
        )
        return list(result.all())


async def _fetch_backfill_tasks(
    engine: AsyncEngine, ticker: str
) -> list[BackfillTaskModel]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await session.exec(
            select(BackfillTaskModel).where(BackfillTaskModel.ticker == ticker)
        )
        return list(result.all())


# =============================================================================
# POST /admin/watchlist — ticker validation (Task #221 Step 2+3)
# =============================================================================


class TestPinTickerValidation:
    """``POST /admin/watchlist`` validates tickers against the market-data provider."""

    def test_unrecognised_ticker_returns_422(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Validator returns False → 422 Unprocessable Entity."""
        from zebu.adapters.inbound.api.dependencies import get_ticker_validator

        app.dependency_overrides[get_ticker_validator] = lambda: _RejectingValidator()
        try:
            response = client.post(
                "/api/v1/admin/watchlist",
                json={"ticker": "BOGUS"},
                headers=admin_headers,
            )
        finally:
            # Restore global test override so other tests still use AlwaysRecognised.
            from zebu.adapters.inbound.api.dependencies import (
                _AlwaysRecognisedValidator,
            )

            app.dependency_overrides[get_ticker_validator] = (
                lambda: _AlwaysRecognisedValidator()
            )

        assert response.status_code == 422
        assert "not recognised" in response.json()["detail"].lower()

    def test_provider_unavailable_returns_500(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Validator raises MarketDataUnavailableError → 500."""
        from zebu.adapters.inbound.api.dependencies import get_ticker_validator

        app.dependency_overrides[get_ticker_validator] = lambda: _ErroringValidator()
        try:
            response = client.post(
                "/api/v1/admin/watchlist",
                json={"ticker": "AAPL"},
                headers=admin_headers,
            )
        finally:
            from zebu.adapters.inbound.api.dependencies import (
                _AlwaysRecognisedValidator,
            )

            app.dependency_overrides[get_ticker_validator] = (
                lambda: _AlwaysRecognisedValidator()
            )

        assert response.status_code == 500

    def test_recognised_ticker_is_pinned_successfully(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Validator returns True → ticker is pinned, 201."""
        # The global test fixture already sets get_ticker_validator to
        # _AlwaysRecognisedValidator, so no extra override is needed.
        response = client.post(
            "/api/v1/admin/watchlist",
            json={"ticker": "AAPL"},
            headers=admin_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["ticker"] == "AAPL"
        assert body["is_watchlisted"] is True


# =============================================================================
# DELETE /admin/data-coverage/tickers/{ticker} (Task #221 Step 4)
# =============================================================================


@pytest.mark.asyncio
class TestHardDeleteTicker:
    """``DELETE /admin/data-coverage/tickers/{ticker}`` cascades correctly."""

    async def test_deletes_watchlist_and_price_history(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Hard delete removes both watchlist row and price_history rows."""
        await _seed_watchlist(test_engine, ticker="TSLA")
        await _seed_bars(test_engine, ticker="TSLA", days=[date(2025, 1, 2)])

        response = client.delete(
            "/api/v1/admin/data-coverage/tickers/TSLA",
            headers=admin_headers,
        )
        assert response.status_code == 204

        wl = await _fetch_watchlist_rows(test_engine, "TSLA")
        ph = await _fetch_price_rows(test_engine, "TSLA")
        assert wl == []
        assert ph == []

    async def test_non_terminal_backfill_tasks_marked_failed(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Non-terminal backfill tasks are marked FAILED with admin reason."""
        await _seed_watchlist(test_engine, ticker="MSFT")
        await _seed_backfill_task(
            test_engine, ticker="MSFT", status=BackfillTaskStatus.PENDING
        )

        response = client.delete(
            "/api/v1/admin/data-coverage/tickers/MSFT",
            headers=admin_headers,
        )
        assert response.status_code == 204

        tasks = await _fetch_backfill_tasks(test_engine, "MSFT")
        assert len(tasks) == 1
        task = tasks[0]
        assert task.status == BackfillTaskStatus.FAILED.value
        assert task.error_message is not None
        assert "deleted" in task.error_message.lower()

    async def test_returns_404_when_ticker_has_no_data(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Delete on ticker with nothing to delete → 404."""
        response = client.delete(
            "/api/v1/admin/data-coverage/tickers/FAKE",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_second_delete_returns_404(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Idempotency: second DELETE on already-removed ticker returns 404."""
        await _seed_watchlist(test_engine, ticker="GOOG")

        r1 = client.delete(
            "/api/v1/admin/data-coverage/tickers/GOOG",
            headers=admin_headers,
        )
        assert r1.status_code == 204

        r2 = client.delete(
            "/api/v1/admin/data-coverage/tickers/GOOG",
            headers=admin_headers,
        )
        assert r2.status_code == 404

    def test_requires_admin_auth(self, client: TestClient) -> None:
        """Unauthenticated request is rejected."""
        response = client.delete("/api/v1/admin/data-coverage/tickers/AAPL")
        assert response.status_code in (401, 403)

    async def test_hard_delete_removes_inactive_watchlist_rows_too(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Even is_active=False watchlist rows are removed (hard delete, not soft)."""
        await _seed_watchlist(test_engine, ticker="IBM", is_active=False)

        response = client.delete(
            "/api/v1/admin/data-coverage/tickers/IBM",
            headers=admin_headers,
        )
        assert response.status_code == 204

        wl = await _fetch_watchlist_rows(test_engine, "IBM")
        assert wl == []


# =============================================================================
# GET /admin/data-coverage — gap_ranges field (Task #221 Step 1)
# =============================================================================


@pytest.mark.asyncio
class TestGapRangesInCoverageResponse:
    """``gap_ranges`` is present and correctly populated in the GET response."""

    async def test_gap_ranges_present_in_response(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``gap_ranges`` key exists on each ticker entry."""
        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2025-01-02")
        await _seed_watchlist(test_engine, ticker="AAPL")

        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["tickers"]) >= 1
        entry = next(t for t in body["tickers"] if t["ticker"] == "AAPL")
        assert "gap_ranges" in entry
        assert isinstance(entry["gap_ranges"], list)
        # With no bars, gap_ranges must be non-empty (the whole window is a gap).
        assert len(entry["gap_ranges"]) >= 1

    async def test_gap_ranges_has_start_end_keys(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Each gap_ranges entry has ``start`` and ``end`` keys."""
        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2025-01-02")
        await _seed_watchlist(test_engine, ticker="NVDA")

        response = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        nvda = next((t for t in body["tickers"] if t["ticker"] == "NVDA"), None)
        assert nvda is not None
        assert len(nvda["gap_ranges"]) > 0
        for gr in nvda["gap_ranges"]:
            assert "start" in gr
            assert "end" in gr
            # Values should be parseable ISO dates.
            date.fromisoformat(gr["start"])
            date.fromisoformat(gr["end"])


# =============================================================================
# ZEBU_HISTORY_MAX_LOOKBACK_DAYS env knob (Task #221 Step 5)
# =============================================================================


class TestEffectiveHistoryEpoch:
    """``get_effective_history_epoch`` clamps correctly."""

    def test_no_clamp_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without ``ZEBU_HISTORY_MAX_LOOKBACK_DAYS``, raw epoch is returned."""
        from zebu.adapters.inbound.api.dependencies import get_effective_history_epoch

        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2015-01-01")
        monkeypatch.delenv("ZEBU_HISTORY_MAX_LOOKBACK_DAYS", raising=False)

        result = get_effective_history_epoch()
        assert result == date(2015, 1, 1)

    def test_clamp_applies_when_epoch_is_older_than_lookback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``today - 100`` is newer than epoch 2015-01-01 → clamp wins."""
        from zebu.adapters.inbound.api.dependencies import get_effective_history_epoch

        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2015-01-01")
        monkeypatch.setenv("ZEBU_HISTORY_MAX_LOOKBACK_DAYS", "100")

        result = get_effective_history_epoch()
        expected_min = date.today() - timedelta(days=100)
        assert result == expected_min

    def test_epoch_wins_when_newer_than_lookback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``ZEBU_HISTORY_EPOCH`` is more recent than ``today - N``, epoch wins."""
        from zebu.adapters.inbound.api.dependencies import get_effective_history_epoch

        # Set epoch to a future date — tests the max() branch.
        far_future = (date.today() + timedelta(days=3650)).isoformat()
        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", far_future)
        monkeypatch.setenv("ZEBU_HISTORY_MAX_LOOKBACK_DAYS", "100")

        result = get_effective_history_epoch()
        assert result == date.fromisoformat(far_future)

    def test_zero_lookback_disables_clamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``ZEBU_HISTORY_MAX_LOOKBACK_DAYS=0`` is treated as no-clamp."""
        from zebu.adapters.inbound.api.dependencies import get_effective_history_epoch

        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2015-01-01")
        monkeypatch.setenv("ZEBU_HISTORY_MAX_LOOKBACK_DAYS", "0")

        result = get_effective_history_epoch()
        assert result == date(2015, 1, 1)

    def test_negative_lookback_disables_clamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative ``ZEBU_HISTORY_MAX_LOOKBACK_DAYS`` is treated as no-clamp."""
        from zebu.adapters.inbound.api.dependencies import get_effective_history_epoch

        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2015-01-01")
        monkeypatch.setenv("ZEBU_HISTORY_MAX_LOOKBACK_DAYS", "-5")

        result = get_effective_history_epoch()
        assert result == date(2015, 1, 1)

    def test_invalid_lookback_raises_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-integer ``ZEBU_HISTORY_MAX_LOOKBACK_DAYS`` raises RuntimeError."""
        from zebu.adapters.inbound.api.dependencies import get_effective_history_epoch

        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2015-01-01")
        monkeypatch.setenv("ZEBU_HISTORY_MAX_LOOKBACK_DAYS", "not-a-number")

        with pytest.raises(RuntimeError, match="ZEBU_HISTORY_MAX_LOOKBACK_DAYS"):
            get_effective_history_epoch()
