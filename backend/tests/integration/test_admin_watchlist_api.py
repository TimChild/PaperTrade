"""Integration tests for ``/api/v1/admin/watchlist`` endpoints.

Task #220 — operator Pin/Unpin surface for ``ticker_watchlist``.

Covers:

* Auth gating — 401 unauthenticated, 403 for non-admin, 2xx for admin.
* POST ``/admin/watchlist``: happy path (new ticker → row inserted),
  idempotency (re-pinning is a no-op), validation (bad ticker → 400,
  rejected fields → 422).
* DELETE ``/admin/watchlist/{ticker}``: happy path (row marked
  inactive), 404 when the ticker isn't in the watchlist.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.models.ticker_watchlist import TickerWatchlistModel

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


async def _fetch_watchlist_row(
    engine: AsyncEngine, ticker: str
) -> TickerWatchlistModel | None:
    """Read a single watchlist row by ticker (any status)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        stmt = select(TickerWatchlistModel).where(TickerWatchlistModel.ticker == ticker)
        result = await session.exec(stmt)
        return result.one_or_none()


async def _seed_watchlist_row(
    engine: AsyncEngine, *, ticker: str, is_active: bool = True
) -> None:
    """Insert a watchlist row directly (bypasses the manager)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(TickerWatchlistModel(ticker=ticker, is_active=is_active))
        await session.commit()


# =============================================================================
# POST /admin/watchlist — auth gating
# =============================================================================


class TestPinAuthGating:
    """``POST /admin/watchlist`` rejects non-admin callers."""

    def test_unauthenticated_rejects(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/admin/watchlist",
            json={"ticker": "AAPL"},
        )
        assert response.status_code in (401, 403)

    def test_non_admin_user_rejects(
        self,
        client: TestClient,
        non_admin_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/api/v1/admin/watchlist",
            headers=non_admin_headers,
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 403


# =============================================================================
# POST /admin/watchlist — happy paths
# =============================================================================


@pytest.mark.asyncio
class TestPinHappyPath:
    """``POST /admin/watchlist`` adds (or re-activates) a watchlist row."""

    async def test_pin_new_ticker_inserts_active_row(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """First pin → 201, row exists with ``is_active=True``."""
        response = client.post(
            "/api/v1/admin/watchlist",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body == {"ticker": "AAPL", "is_watchlisted": True}

        row = await _fetch_watchlist_row(test_engine, ticker="AAPL")
        assert row is not None
        assert row.is_active is True
        # The endpoint uses the server-fixed priority (100) for pinned rows.
        assert row.priority == 100

    async def test_pin_existing_ticker_is_idempotent(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Pinning an already-active ticker is a no-op and returns 201."""
        await _seed_watchlist_row(test_engine, ticker="AAPL", is_active=True)

        response = client.post(
            "/api/v1/admin/watchlist",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 201, response.text
        assert response.json() == {"ticker": "AAPL", "is_watchlisted": True}

        # Still exactly one row in the watchlist for this ticker.
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            stmt = select(TickerWatchlistModel).where(
                TickerWatchlistModel.ticker == "AAPL"
            )
            result = await session.exec(stmt)
            all_rows = result.all()
            assert len(all_rows) == 1
            assert all_rows[0].is_active is True

    async def test_pin_reactivates_previously_unpinned_ticker(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """A previously-unpinned (inactive) row gets flipped back to active."""
        await _seed_watchlist_row(test_engine, ticker="AAPL", is_active=False)

        response = client.post(
            "/api/v1/admin/watchlist",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 201, response.text

        row = await _fetch_watchlist_row(test_engine, ticker="AAPL")
        assert row is not None
        assert row.is_active is True


# =============================================================================
# POST /admin/watchlist — validation
# =============================================================================


@pytest.mark.asyncio
class TestPinValidation:
    """``POST /admin/watchlist`` rejects invalid input."""

    async def test_invalid_ticker_returns_400(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A ticker that violates the Ticker invariants → 400."""
        response = client.post(
            "/api/v1/admin/watchlist",
            headers=admin_headers,
            json={"ticker": "TOOLONGSYMBOL"},
        )
        assert response.status_code == 400

    async def test_extra_priority_field_rejected(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Task #220: the ``priority`` field is server-set; a client
        override is rejected as 422 (Pydantic ``extra=forbid``).

        Lock the contract so we can later turn on a UI-tunable priority
        without silent overrides leaking through in the meantime.
        """
        response = client.post(
            "/api/v1/admin/watchlist",
            headers=admin_headers,
            json={"ticker": "AAPL", "priority": 50},
        )
        assert response.status_code == 422


# =============================================================================
# DELETE /admin/watchlist/{ticker} — auth gating
# =============================================================================


class TestUnpinAuthGating:
    """``DELETE /admin/watchlist/{ticker}`` rejects non-admin callers."""

    def test_unauthenticated_rejects(self, client: TestClient) -> None:
        response = client.delete("/api/v1/admin/watchlist/AAPL")
        assert response.status_code in (401, 403)

    def test_non_admin_user_rejects(
        self,
        client: TestClient,
        non_admin_headers: dict[str, str],
    ) -> None:
        response = client.delete(
            "/api/v1/admin/watchlist/AAPL",
            headers=non_admin_headers,
        )
        assert response.status_code == 403


# =============================================================================
# DELETE /admin/watchlist/{ticker} — happy paths
# =============================================================================


@pytest.mark.asyncio
class TestUnpinHappyPath:
    """``DELETE`` marks the row inactive."""

    async def test_unpin_existing_ticker_marks_inactive(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """Active row → 204, ``is_active`` flipped to False.

        Row is preserved (soft-delete) so historical refresh metadata
        stays attached to the ticker; only ``is_active`` changes.
        """
        await _seed_watchlist_row(test_engine, ticker="AAPL", is_active=True)

        response = client.delete(
            "/api/v1/admin/watchlist/AAPL",
            headers=admin_headers,
        )
        assert response.status_code == 204, response.text

        row = await _fetch_watchlist_row(test_engine, ticker="AAPL")
        assert row is not None  # Soft delete — row still exists.
        assert row.is_active is False


@pytest.mark.asyncio
class TestUnpinNotFound:
    """``DELETE`` on a non-pinned ticker returns 404."""

    async def test_unpin_never_pinned_returns_404(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A ticker that's never been in the watchlist → 404."""
        response = client.delete(
            "/api/v1/admin/watchlist/AAPL",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_unpin_already_inactive_returns_404(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_engine: AsyncEngine,
    ) -> None:
        """A ticker that exists in the table but is already ``is_active=False``
        → 404. The endpoint reports back the actionable signal: nothing
        changed.
        """
        await _seed_watchlist_row(test_engine, ticker="AAPL", is_active=False)

        response = client.delete(
            "/api/v1/admin/watchlist/AAPL",
            headers=admin_headers,
        )
        assert response.status_code == 404


# =============================================================================
# DELETE /admin/watchlist/{ticker} — validation
# =============================================================================


@pytest.mark.asyncio
class TestUnpinValidation:
    """Invalid path params surface as 400."""

    async def test_invalid_ticker_returns_400(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """A ticker that violates Ticker invariants → 400."""
        response = client.delete(
            "/api/v1/admin/watchlist/TOOLONGSYMBOL",
            headers=admin_headers,
        )
        assert response.status_code == 400


# =============================================================================
# Round-trip: GET /admin/data-coverage reflects POST + DELETE results
# =============================================================================


@pytest.mark.asyncio
class TestRoundTripWithDataCoverage:
    """Pinning and unpinning flips ``is_watchlisted`` on the coverage GET."""

    async def test_pin_flips_is_watchlisted_true_on_coverage_get(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """POST /admin/watchlist then GET /admin/data-coverage → True."""
        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2015-01-01")

        pin = client.post(
            "/api/v1/admin/watchlist",
            headers=admin_headers,
            json={"ticker": "AAPL"},
        )
        assert pin.status_code == 201

        coverage = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        assert coverage.status_code == 200
        body = coverage.json()
        row = next(r for r in body["tickers"] if r["ticker"] == "AAPL")
        assert row["is_watchlisted"] is True
        assert row["is_active"] is True

    async def test_unpin_flips_is_watchlisted_false_on_coverage_get(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
        test_engine: AsyncEngine,
    ) -> None:
        """DELETE /admin/watchlist/AAPL → ``is_watchlisted=False`` next GET."""
        monkeypatch.setenv("ZEBU_HISTORY_EPOCH", "2015-01-01")

        await _seed_watchlist_row(test_engine, ticker="AAPL", is_active=True)

        unpin = client.delete(
            "/api/v1/admin/watchlist/AAPL",
            headers=admin_headers,
        )
        assert unpin.status_code == 204

        coverage = client.get(
            "/api/v1/admin/data-coverage",
            headers=admin_headers,
        )
        body = coverage.json()
        # After unpin the ticker may no longer be in the active set at
        # all (no bars, no recent trades, no active watchlist). It might
        # therefore be missing from the response — assert that if it IS
        # there, ``is_watchlisted`` is False.
        matching = [r for r in body["tickers"] if r["ticker"] == "AAPL"]
        for row in matching:
            assert row["is_watchlisted"] is False
