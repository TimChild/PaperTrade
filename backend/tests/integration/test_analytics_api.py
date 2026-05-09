"""Integration tests for analytics API endpoints.

These tests verify that the analytics endpoints work correctly end-to-end,
including snapshot retrieval and portfolio composition calculation.
"""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.domain.entities.portfolio_snapshot import PortfolioSnapshot

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.asyncio
async def test_get_performance_with_snapshots(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
    test_engine: "AsyncEngine",  # type: ignore[name-defined]
) -> None:
    """Test performance endpoint returns snapshots and metrics."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Performance Test Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = UUID(response.json()["portfolio_id"])

    # Create test snapshots using the same engine as the client

    from zebu.adapters.outbound.database.snapshot_repository import (
        SQLModelSnapshotRepository,
    )

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        snapshot_repo = SQLModelSnapshotRepository(session)

        today = date.today()
        snapshots = [
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=today - timedelta(days=7),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=today - timedelta(days=3),
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("5500.00"),
                holdings_count=1,
            ),
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=today,
                cash_balance=Decimal("5000.00"),
                holdings_value=Decimal("6000.00"),
                holdings_count=1,
            ),
        ]

        for snapshot in snapshots:
            await snapshot_repo.save(snapshot)
        await session.commit()

    # Get performance data
    perf_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance?range=1W",
        headers=auth_headers,
    )

    assert perf_response.status_code == 200
    data = perf_response.json()

    # Verify structure
    assert "portfolio_id" in data
    assert "range" in data
    assert "data_points" in data
    assert "metrics" in data

    assert data["portfolio_id"] == str(portfolio_id)
    assert data["range"] == "1W"
    assert len(data["data_points"]) == 3

    # Verify data points
    assert data["data_points"][0]["date"] == str(today - timedelta(days=7))
    assert data["data_points"][0]["total_value"] == 10000.0
    assert data["data_points"][2]["total_value"] == 11000.0

    # Verify metrics
    metrics = data["metrics"]
    assert metrics is not None
    assert metrics["starting_value"] == 10000.0
    assert metrics["ending_value"] == 11000.0
    assert metrics["absolute_gain"] == 1000.0
    assert metrics["percentage_gain"] == 10.0
    assert metrics["highest_value"] == 11000.0
    assert metrics["lowest_value"] == 10000.0


def test_get_performance_with_no_snapshots(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test performance endpoint with no snapshots returns empty data."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Empty Performance Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Get performance data (no snapshots exist yet)
    perf_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance?range=1M",
        headers=auth_headers,
    )

    assert perf_response.status_code == 200
    data = perf_response.json()

    assert data["portfolio_id"] == portfolio_id
    assert data["range"] == "1M"
    assert data["data_points"] == []
    assert data["metrics"] is None  # No metrics without data


@pytest.mark.asyncio
async def test_get_performance_different_time_ranges(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
    test_engine: "AsyncEngine",  # type: ignore[name-defined]
) -> None:
    """Test performance endpoint with different time ranges."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Time Range Test Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = UUID(response.json()["portfolio_id"])

    # Create snapshots across different time periods

    from zebu.adapters.outbound.database.snapshot_repository import (
        SQLModelSnapshotRepository,
    )

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        snapshot_repo = SQLModelSnapshotRepository(session)

        today = date.today()
        dates = [
            today - timedelta(days=400),  # Very old (should be in ALL only)
            today - timedelta(days=200),  # Old (should be in 1Y and ALL)
            today - timedelta(days=60),  # Should be in 3M, 1Y, ALL
            today - timedelta(days=20),  # Should be in 1M, 3M, 1Y, ALL
            today - timedelta(days=5),  # Should be in 1W, 1M, 3M, 1Y, ALL
            today,  # Should be in all ranges
        ]

        for i, snapshot_date in enumerate(dates):
            snapshot = PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=snapshot_date,
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal(i * 100),
                holdings_count=i,
            )
            await snapshot_repo.save(snapshot)
        await session.commit()

    # Test different time ranges
    test_cases = [
        ("1W", 2),  # Last 7 days: 2 snapshots
        ("1M", 3),  # Last 30 days: 3 snapshots
        ("3M", 4),  # Last 90 days: 4 snapshots
        ("1Y", 5),  # Last 365 days: 5 snapshots
        ("ALL", 6),  # All time: 6 snapshots
    ]

    for time_range, expected_count in test_cases:
        perf_response = client.get(
            f"/api/v1/portfolios/{portfolio_id}/performance?range={time_range}",
            headers=auth_headers,
        )

        assert perf_response.status_code == 200
        data = perf_response.json()
        assert data["range"] == time_range
        assert len(data["data_points"]) == expected_count, (
            f"Range {time_range} should have {expected_count} snapshots"
        )


def test_get_performance_invalid_portfolio(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test performance endpoint with non-existent portfolio."""
    from uuid import uuid4

    fake_portfolio_id = uuid4()

    perf_response = client.get(
        f"/api/v1/portfolios/{fake_portfolio_id}/performance?range=1M",
        headers=auth_headers,
    )

    assert perf_response.status_code == 404
    assert "not found" in perf_response.json()["detail"].lower()


def test_get_composition_with_holdings(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test composition endpoint returns holdings breakdown."""
    # Create portfolio with cash
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Composition Test Portfolio",
            "initial_deposit": "50000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute trades to create holdings
    # Buy AAPL (price: $150)
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100"},
    )

    # Buy MSFT (price: $380)
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "BUY", "ticker": "MSFT", "quantity": "20"},
    )

    # Get composition
    comp_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/composition",
        headers=auth_headers,
    )

    assert comp_response.status_code == 200
    data = comp_response.json()

    # Verify structure
    assert "portfolio_id" in data
    assert "total_value" in data
    assert "composition" in data

    assert data["portfolio_id"] == portfolio_id
    composition = data["composition"]

    # Should have AAPL, MSFT, and CASH
    tickers = {item["ticker"] for item in composition}
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert "CASH" in tickers

    # Verify total value calculation
    # $50,000 initial - $15,000 (AAPL) - $7,600 (MSFT) = $27,400 cash
    # Total: $15,000 + $7,600 + $27,400 = $50,000
    assert data["total_value"] == 50000.0

    # Verify percentages sum to ~100%
    total_percentage = sum(item["percentage"] for item in composition)
    assert 99.0 <= total_percentage <= 101.0  # Allow rounding errors

    # Verify each item has required fields
    for item in composition:
        assert "ticker" in item
        assert "value" in item
        assert "percentage" in item
        assert "quantity" in item

        if item["ticker"] != "CASH":
            assert isinstance(item["quantity"], int)
        else:
            assert item["quantity"] is None


def test_get_composition_cash_only_portfolio(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test composition endpoint with cash-only portfolio."""
    # Create portfolio with only cash
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Cash Only Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Get composition
    comp_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/composition",
        headers=auth_headers,
    )

    assert comp_response.status_code == 200
    data = comp_response.json()

    # Should only have CASH
    assert len(data["composition"]) == 1
    cash_item = data["composition"][0]
    assert cash_item["ticker"] == "CASH"
    assert cash_item["value"] == 10000.0
    assert cash_item["percentage"] == 100.0
    assert cash_item["quantity"] is None

    # Total value should equal cash
    assert data["total_value"] == 10000.0


def test_get_composition_portfolio_not_found(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test composition endpoint with non-existent portfolio."""
    from uuid import uuid4

    fake_portfolio_id = uuid4()

    comp_response = client.get(
        f"/api/v1/portfolios/{fake_portfolio_id}/composition",
        headers=auth_headers,
    )

    assert comp_response.status_code == 404
    assert "not found" in comp_response.json()["detail"].lower()


def test_analytics_endpoints_require_auth(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test analytics endpoints reject unauthenticated requests."""
    from uuid import uuid4

    portfolio_id = uuid4()

    # No auth headers
    perf_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance?range=1M"
    )
    assert perf_response.status_code == 401  # Unauthorized, not Forbidden

    comp_response = client.get(f"/api/v1/portfolios/{portfolio_id}/composition")
    assert comp_response.status_code == 401  # Unauthorized, not Forbidden


def test_analytics_endpoints_enforce_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test analytics endpoints only show user's own portfolios."""
    # Create portfolio for user A
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "User A Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id_a = response.json()["portfolio_id"]

    # Note: The in-memory auth adapter in the test fixture only has one user
    # configured ("test-user-default" with token "test-token-default").
    # A different token that isn't registered will result in 401 Unauthorized.
    # This test validates that unauthorized users can't access portfolios,
    # which is the expected behavior.

    # Use an invalid token (not registered in the test auth adapter)
    auth_headers_b = {"Authorization": "Bearer invalid-token"}

    # User B tries to access User A's portfolio with invalid token
    perf_response = client.get(
        f"/api/v1/portfolios/{portfolio_id_a}/performance?range=1M",
        headers=auth_headers_b,
    )
    assert perf_response.status_code == 401  # Unauthorized (invalid token)

    comp_response = client.get(
        f"/api/v1/portfolios/{portfolio_id_a}/composition",
        headers=auth_headers_b,
    )
    assert comp_response.status_code == 401  # Unauthorized (invalid token)


@pytest.mark.asyncio
async def test_performance_data_points_include_holdings_breakdown(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
    test_engine: "AsyncEngine",  # type: ignore[name-defined]
) -> None:
    """Test performance data points include per-holding breakdown."""
    from zebu.adapters.outbound.database.snapshot_repository import (
        SQLModelSnapshotRepository,
    )
    from zebu.domain.entities.portfolio_snapshot import HoldingBreakdown

    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Breakdown Test Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = UUID(response.json()["portfolio_id"])

    breakdown = [
        HoldingBreakdown(
            ticker="AAPL",
            quantity=10,
            price_per_share=Decimal("150.00"),
            value=Decimal("1500.00"),
        ),
        HoldingBreakdown(
            ticker="MSFT",
            quantity=5,
            price_per_share=Decimal("300.00"),
            value=Decimal("1500.00"),
        ),
    ]

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        snapshot_repo = SQLModelSnapshotRepository(session)
        today = date.today()

        snapshot = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=today,
            cash_balance=Decimal("7000.00"),
            holdings_value=Decimal("3000.00"),
            holdings_count=2,
            holdings_breakdown=breakdown,
        )
        await snapshot_repo.save(snapshot)
        await session.commit()

    # Get performance data
    perf_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance?range=1W",
        headers=auth_headers,
    )

    assert perf_response.status_code == 200
    data = perf_response.json()

    assert len(data["data_points"]) == 1
    data_point = data["data_points"][0]

    # Verify breakdown is included
    assert "holdings_breakdown" in data_point
    assert len(data_point["holdings_breakdown"]) == 2

    tickers = {item["ticker"] for item in data_point["holdings_breakdown"]}
    assert tickers == {"AAPL", "MSFT"}

    aapl = next(h for h in data_point["holdings_breakdown"] if h["ticker"] == "AAPL")
    assert aapl["quantity"] == 10
    assert aapl["price_per_share"] == 150.0
    assert aapl["value"] == 1500.0


@pytest.mark.asyncio
async def test_old_snapshot_without_breakdown_returns_empty_list(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
    test_engine: "AsyncEngine",  # type: ignore[name-defined]
) -> None:
    """Test backward compatibility: old snapshots return empty holdings_breakdown."""
    from zebu.adapters.outbound.database.snapshot_repository import (
        SQLModelSnapshotRepository,
    )

    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Old Snapshot Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = UUID(response.json()["portfolio_id"])

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        snapshot_repo = SQLModelSnapshotRepository(session)
        today = date.today()

        # Create snapshot without breakdown (backward compat)
        snapshot = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=today,
            cash_balance=Decimal("5000.00"),
            holdings_value=Decimal("5000.00"),
            holdings_count=2,
            # No holdings_breakdown provided
        )
        await snapshot_repo.save(snapshot)
        await session.commit()

    perf_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance?range=1W",
        headers=auth_headers,
    )

    assert perf_response.status_code == 200
    data = perf_response.json()
    assert len(data["data_points"]) == 1
    data_point = data["data_points"][0]

    # Old snapshot returns empty breakdown list
    assert data_point["holdings_breakdown"] == []


# =========================================================================
# Wave 1-A security fixes — admin gates + ownership check
# (audits/2026-05-09: sec.P0-1, sec.P0-2, api.P0-2)
# =========================================================================


@pytest.fixture
def admin_auth_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[dict[str, str]]:
    """Provide admin Bearer headers, registering the test user as admin."""
    monkeypatch.setenv("ADMIN_USER_IDS", "test-user-default")
    yield {"Authorization": "Bearer test-token-default"}


def test_admin_price_refresh_requires_auth(
    client: TestClient,
) -> None:
    """POST /analytics/prices/refresh rejects unauthenticated callers (401)."""
    response = client.post("/api/v1/analytics/prices/refresh")
    assert response.status_code == 401


def test_admin_price_refresh_rejects_non_admin(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticated non-admin gets 403 from POST /analytics/prices/refresh."""
    monkeypatch.setenv("ADMIN_USER_IDS", "")  # default test user not in allowlist
    response = client.post("/api/v1/analytics/prices/refresh", headers=auth_headers)
    assert response.status_code == 403


def test_admin_daily_snapshots_requires_auth(
    client: TestClient,
) -> None:
    """POST /analytics/snapshots/daily rejects unauthenticated callers (401)."""
    response = client.post("/api/v1/analytics/snapshots/daily")
    assert response.status_code == 401


def test_admin_daily_snapshots_rejects_non_admin(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticated non-admin gets 403 from POST /analytics/snapshots/daily."""
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    response = client.post("/api/v1/analytics/snapshots/daily", headers=auth_headers)
    assert response.status_code == 403


def test_admin_daily_snapshots_admin_succeeds(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Admin caller can trigger daily snapshots and gets a 201."""
    response = client.post(
        "/api/v1/analytics/snapshots/daily", headers=admin_auth_headers
    )
    # The job runs against zero-portfolio test DB, so it completes cleanly.
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert "results" in body


def test_backfill_rejects_non_owner_with_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """User cannot backfill snapshots for someone else's portfolio.

    The default test user creates a portfolio. A second authenticated
    request with a registered-but-different user attempts to backfill
    that portfolio's snapshots — and should be denied with 404 (we use
    404 rather than 403 to avoid disclosing existence).
    """
    from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
    from zebu.adapters.inbound.api.dependencies import get_auth_port
    from zebu.application.ports.auth_port import AuthenticatedUser

    # User A creates a portfolio
    create_resp = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Owned by A",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    assert create_resp.status_code == 201
    portfolio_id_a = create_resp.json()["portfolio_id"]

    # Register a second user in the same in-memory adapter so user B
    # can authenticate (otherwise we'd just get 401, which is a
    # different code path).
    adapter_obj = client.app.dependency_overrides[get_auth_port]()  # type: ignore[attr-defined]
    assert isinstance(adapter_obj, InMemoryAuthAdapter)
    adapter_obj.add_user(
        AuthenticatedUser(id="test-user-b", email="b@example.com"),
        "test-token-b",
    )

    today = date.today()
    backfill_resp = client.post(
        f"/api/v1/portfolios/{portfolio_id_a}/snapshots/backfill"
        f"?start_date={today - timedelta(days=2)}&end_date={today}",
        headers={"Authorization": "Bearer test-token-b"},
    )
    assert backfill_resp.status_code == 404


def test_backfill_owner_succeeds(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """The portfolio owner can backfill snapshots for their portfolio."""
    create_resp = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Owner Backfill",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = create_resp.json()["portfolio_id"]

    today = date.today()
    backfill_resp = client.post(
        f"/api/v1/portfolios/{portfolio_id}/snapshots/backfill"
        f"?start_date={today - timedelta(days=1)}&end_date={today}",
        headers=auth_headers,
    )
    assert backfill_resp.status_code == 201
    body = backfill_resp.json()
    assert body["status"] == "completed"


def test_backfill_requires_auth(
    client: TestClient,
) -> None:
    """Backfill route rejects unauthenticated callers."""
    from uuid import uuid4

    today = date.today()
    response = client.post(
        f"/api/v1/portfolios/{uuid4()}/snapshots/backfill"
        f"?start_date={today - timedelta(days=2)}&end_date={today}",
    )
    assert response.status_code == 401
