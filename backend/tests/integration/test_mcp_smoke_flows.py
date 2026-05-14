"""MCP-style end-to-end smoke flows against a real (FK-enforced) DB.

These tests exercise the HTTP surface in the same shape an MCP agent
client does, with SQLite's ``PRAGMA foreign_keys=ON`` so referential
integrity bugs surface here instead of in prod.

**Motivation**: between 2026-05-13 and 2026-05-14 we shipped four
backtest-related fixes (#287 FK ordering, #289 DCA 0-trades, #291 the
two-bug pair around fractional-share math + AV cap-as-not-found), all
caught only by Tim's manual MCP smoke run. None of them tripped CI.
The gap: existing integration tests use in-memory repos OR a FK-
disabled SQLite engine, so the entire class of "this would fail on
real Postgres" stays invisible. These tests close that gap for the
agent-facing flows that have proven to be the highest-risk surface.

Test inventory (each is a happy-path full-stack flow):

1. ``test_backtest_completes_against_real_db`` — POST /backtests on a
   freshly created strategy. Asserts COMPLETED, not 500. Would have
   caught the #287 FK ordering bug (``backtest_runs.portfolio_id ->
   portfolios.id`` violated because the portfolio was saved AFTER the
   run row staged for INSERT).
2. ``test_dca_backtest_produces_trades`` — POST /backtests on a DCA
   strategy over a multi-period window. Asserts COMPLETED + >0 trades.
   Would have caught #289 (``ROUND_DOWN`` of fractional shares to 0)
   AND #291 part 1 (the Money 2dp invariant choke when the
   fractional-share fix shipped without quantising ``cash_change``).
3. ``test_activation_lifecycle`` — create strategy → activate → run
   now → deactivate-with-reason → list. Walks the full state machine
   that #284's deactivation_reason migration touched, asserting the
   reason lands in the right field and ``last_error`` stays clean.
4. ``test_exploration_task_lifecycle`` — create → claim → submit
   findings → fetch. Confirms the MCP write surface persists through
   the FK chain (api_key_id, claimed_by, finding payload).

Read-side tools (``list_supported_tickers``, ``list_portfolios``,
``get_current_price`` etc.) are covered by the existing API tests in
``test_portfolio_api.py`` / ``test_prices_api.py`` — no need to
duplicate here.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_DNS, uuid4, uuid5

import pytest
import pytest_asyncio
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.auth.api_key_adapter import ApiKeyAuthAdapter
from zebu.adapters.auth.api_key_hasher import ApiKeyHasher
from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.adapters.inbound.api.dependencies import (
    get_api_key_auth_adapter,
    get_api_key_repository,
    get_auth_port,
    get_market_data,
)
from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.ports.auth_port import AuthenticatedUser
from zebu.application.ports.in_memory_api_key_repository import (
    InMemoryApiKeyRepository,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.ticker import Ticker
from zebu.infrastructure.database import get_session
from zebu.main import app


_TEST_USER_ID = "test-user-mcp-smoke"
_TEST_TOKEN = "mcp-smoke-token"
_TEST_PEPPER = "test-api-key-pepper-do-not-use-in-production"


def _seed_market_data() -> InMemoryMarketDataAdapter:
    """Build an in-memory adapter pre-seeded with daily bars for AAPL.

    Seeds ~400 daily bars spanning roughly 1.5 years so multi-period
    backtests have data to iterate over. Prices drift modestly upward
    so DCA periods produce non-trivial differences from each other.
    """
    adapter = InMemoryMarketDataAdapter()

    end_date = datetime.now(UTC) - timedelta(days=1)
    base_price = Decimal("150.00")
    drift = Decimal("0.10")  # +$0.10/day average

    bars: list[PricePoint] = []
    for i in range(400):
        ts = end_date - timedelta(days=i)
        # Anchor to 21:00 UTC (canonical market-close per #286).
        ts = ts.replace(hour=21, minute=0, second=0, microsecond=0)
        price = base_price + drift * (400 - i)
        # Quantise to 2dp so prices satisfy Money's invariant.
        price = price.quantize(Decimal("0.01"))
        bars.append(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(price, "USD"),
                timestamp=ts,
                source="database",
                interval="1day",
            )
        )

    adapter.seed_prices(bars)
    return adapter


@pytest_asyncio.fixture
async def mcp_market_data() -> InMemoryMarketDataAdapter:
    """Reusable seeded adapter — separate fixture so individual tests
    can extend it before the client is built if they need to."""
    return _seed_market_data()


@pytest.fixture
def mcp_client(
    test_engine_with_fks: AsyncEngine,
    mcp_market_data: InMemoryMarketDataAdapter,
) -> TestClient:
    """HTTP client backed by a FK-enforcing in-memory SQLite + seeded
    market data + a fresh API-key + auth adapter. Each test gets a
    clean engine and adapters — no shared state across tests.

    Tests authenticate via API key ``Authorization: ApiKey <token>``
    (matches the MCP transport). The token's owner has TRADE + READ
    scopes; ADMIN is intentionally omitted to mirror what an agent's
    key normally carries.
    """
    async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSession(
            test_engine_with_fks, expire_on_commit=False
        ) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_test_market_data(
        session: AsyncSession = Depends(get_test_session),  # type: ignore[assignment]  # noqa: B008
    ) -> InMemoryMarketDataAdapter:
        return mcp_market_data

    auth_adapter = InMemoryAuthAdapter()
    auth_adapter.add_user(
        AuthenticatedUser(id=_TEST_USER_ID, email="agent@zebutrader.com"),
        _TEST_TOKEN,
    )

    def get_test_auth_port() -> InMemoryAuthAdapter:
        return auth_adapter

    hasher = ApiKeyHasher(secret=_TEST_PEPPER)
    api_key_repo = InMemoryApiKeyRepository()
    seed_key = ApiKey(
        id=uuid4(),
        user_id=uuid5(NAMESPACE_DNS, _TEST_USER_ID),
        clerk_user_id=_TEST_USER_ID,
        label="mcp-smoke-key",
        key_hash=hasher.hash(_TEST_TOKEN),
        scopes=frozenset([ApiKeyScope.READ, ApiKeyScope.TRADE]),
        created_at=datetime.now(UTC),
    )
    api_key_repo._by_id[seed_key.id] = seed_key

    # Also seed the SQL ``api_keys`` table — every write surface stamps
    # ``api_key_id`` on its row (strategies, transactions, activations,
    # backtest_runs, exploration_tasks) with FK references to this
    # table. Without the SQL row the FK constraint fails the moment any
    # of those writes flush. The in-memory repo above handles the auth
    # *read* path; this insert handles the persistence *write* path.
    import asyncio

    async def _seed_sql_api_key() -> None:
        async with AsyncSession(
            test_engine_with_fks, expire_on_commit=False
        ) as session:
            session.add(
                ApiKeyModel(
                    id=seed_key.id,
                    user_id=seed_key.user_id,
                    clerk_user_id=seed_key.clerk_user_id,
                    label=seed_key.label,
                    key_hash=seed_key.key_hash,
                    scopes=[s.value for s in seed_key.scopes],
                    created_at=seed_key.created_at,
                )
            )
            await session.commit()

    asyncio.run(_seed_sql_api_key())

    def get_test_api_key_repository() -> InMemoryApiKeyRepository:
        return api_key_repo

    def get_test_api_key_auth_adapter() -> ApiKeyAuthAdapter:
        return ApiKeyAuthAdapter(repository=api_key_repo, hasher=hasher)

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_market_data] = get_test_market_data
    app.dependency_overrides[get_auth_port] = get_test_auth_port
    app.dependency_overrides[get_api_key_repository] = get_test_api_key_repository
    app.dependency_overrides[get_api_key_auth_adapter] = (
        get_test_api_key_auth_adapter
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mcp_headers() -> dict[str, str]:
    """API-key Authorization header — same shape MCP uses."""
    return {"Authorization": f"ApiKey {_TEST_TOKEN}"}


def _create_portfolio(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/portfolios",
        headers=headers,
        json={"name": "MCP Smoke Portfolio", "initial_deposit": "10000.00"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["portfolio_id"])


def _create_buy_and_hold_strategy(
    client: TestClient, headers: dict[str, str], *, name: str = "smoke-bah"
) -> str:
    response = client.post(
        "/api/v1/strategies",
        headers=headers,
        json={
            "name": name,
            "strategy_type": "BUY_AND_HOLD",
            "tickers": ["AAPL"],
            "parameters": {"allocation": {"AAPL": "1.0"}},
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _create_dca_strategy(
    client: TestClient, headers: dict[str, str], *, name: str = "smoke-dca"
) -> str:
    response = client.post(
        "/api/v1/strategies",
        headers=headers,
        json={
            "name": name,
            "strategy_type": "DOLLAR_COST_AVERAGING",
            "tickers": ["AAPL"],
            "parameters": {
                "frequency_days": 30,
                "amount_per_period": "100.00",
                "allocation": {"AAPL": "1.0"},
            },
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBacktestHappyPath:
    """Issue #287 regression coverage."""

    def test_backtest_completes_against_real_db(
        self, mcp_client: TestClient, mcp_headers: dict[str, str]
    ) -> None:
        """``POST /backtests`` returns a COMPLETED run, not a 500.

        Pre-fix: the executor staged a ``BacktestRun`` with
        ``portfolio_id`` referencing a synthetic portfolio that hadn't
        been INSERTed yet. The first ``session.get`` in ``_run_pipeline``
        triggered autoflush of the pending row → FK violation → opaque
        500. This test would have failed before #287 landed.
        """
        strategy_id = _create_buy_and_hold_strategy(mcp_client, mcp_headers)

        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=60)

        response = mcp_client.post(
            "/api/v1/backtests",
            headers=mcp_headers,
            json={
                "strategy_id": strategy_id,
                "backtest_name": "mcp-smoke-bah",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "initial_cash": "10000.00",
            },
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "COMPLETED", (
            f"backtest expected COMPLETED, got {body['status']!r}. "
            f"error_message={body.get('error_message')!r}"
        )
        assert body["total_trades"] is not None
        assert body["total_trades"] >= 1, (
            "buy-and-hold over 60 days must produce at least one trade"
        )


class TestDcaBacktestProducesTrades:
    """Issues #283 + #291 part 1 regression coverage."""

    def test_dca_backtest_produces_trades_with_fractional_shares(
        self, mcp_client: TestClient, mcp_headers: dict[str, str]
    ) -> None:
        """DCA over 6 periods with $100 / $150-ish-priced AAPL fires
        non-zero trades AND doesn't blow up Money's 2dp invariant.

        Pre-#289: the transaction builder floored fractional quantities
        to whole shares, so DCA at $100 / $150 = 0 shares every period
        → 0 trades silently. Pre-#291 part 1: with fractional shares
        landing, ``quantity.shares × price.amount`` produced 6dp values
        that crashed ``Money.__post_init__``. Both regressions would
        have failed this test.
        """
        strategy_id = _create_dca_strategy(mcp_client, mcp_headers)

        # 200 days = ~6 DCA periods at 30-day cadence. Wide enough that
        # off-by-one errors in the calendar trigger don't yield zero.
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=200)

        response = mcp_client.post(
            "/api/v1/backtests",
            headers=mcp_headers,
            json={
                "strategy_id": strategy_id,
                "backtest_name": "mcp-smoke-dca",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "initial_cash": "10000.00",
            },
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "COMPLETED", (
            f"DCA backtest expected COMPLETED, got {body['status']!r}. "
            f"error_message={body.get('error_message')!r}"
        )
        # 200 days / 30-day cadence ≈ 6 trades. Assert ≥3 to tolerate
        # calendar-alignment edge cases without losing the regression
        # signal (the pre-fix value was 0).
        assert body["total_trades"] >= 3, (
            f"DCA over 200 days must fire multiple trades, got "
            f"{body['total_trades']!r}"
        )


class TestActivationLifecycle:
    """Issue #284 regression coverage — deactivation_reason landing in
    its dedicated column, not last_error."""

    def test_full_activation_lifecycle_persists_deactivation_reason(
        self, mcp_client: TestClient, mcp_headers: dict[str, str]
    ) -> None:
        """create strategy → activate → deactivate-with-reason → fetch.

        Asserts ``deactivation_reason`` carries the human note and
        ``last_error`` stays ``None`` for a deliberate pause. The
        pre-#290 behaviour overloaded ``last_error`` with the reason.
        """
        portfolio_id = _create_portfolio(mcp_client, mcp_headers)
        strategy_id = _create_buy_and_hold_strategy(
            mcp_client, mcp_headers, name="lifecycle-bah"
        )

        # Activate.
        response = mcp_client.post(
            f"/api/v1/strategies/{strategy_id}/activate",
            headers=mcp_headers,
            json={
                "portfolio_id": portfolio_id,
                "frequency": "DAILY_MARKET_CLOSE",
            },
        )
        assert response.status_code == 201, response.text
        activation_id = response.json()["id"]
        assert response.json()["status"] == "ACTIVE"

        # Deactivate with a human-readable reason.
        reason = "Pausing for end-of-quarter review"
        response = mcp_client.post(
            f"/api/v1/activations/{activation_id}/deactivate",
            headers=mcp_headers,
            json={"reason": reason},
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["status"] == "PAUSED"
        assert body.get("deactivation_reason") == reason, (
            "Deactivation reason must land in the dedicated column "
            "after #290, not in last_error"
        )
        # ``last_error`` may be absent from the response or explicitly
        # null — either is acceptable; what matters is that it is NOT
        # the reason string.
        assert body.get("last_error") in (None, ""), (
            f"last_error must stay clean for a deliberate pause, "
            f"got {body.get('last_error')!r}"
        )


class TestExplorationTaskLifecycle:
    """Confirms the MCP write surface persists through the FK chain."""

    def test_create_claim_submit_persists_structured_finding(
        self, mcp_client: TestClient, mcp_headers: dict[str, str]
    ) -> None:
        """Walk the task state machine the MCP server exposes.

        Each transition writes to a different column with FK references
        (api_key_id on create, claimed_by on claim, finding payload on
        submit). FK enforcement here catches schema regressions before
        they ship.
        """
        # Create — schema requires ``prompt`` (no title/description fields).
        response = mcp_client.post(
            "/api/v1/exploration-tasks",
            headers=mcp_headers,
            json={
                "prompt": (
                    "Find a quality momentum signal for AAPL — "
                    "evaluate 50/200 SMA crossover on AAPL."
                ),
                "tickers": ["AAPL"],
            },
        )
        assert response.status_code == 201, response.text
        task_id = response.json()["id"]
        assert response.json()["status"] == "OPEN"

        # Claim.
        agent_id = "claude-code-mcp-smoke"
        response = mcp_client.post(
            f"/api/v1/exploration-tasks/{task_id}/claim",
            headers=mcp_headers,
            json={"agent_id": agent_id},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "IN_PROGRESS"
        assert response.json()["claimed_by"] == agent_id

        # Submit findings — ``notes`` is a list per FindingsPayload.
        response = mcp_client.post(
            f"/api/v1/exploration-tasks/{task_id}/findings",
            headers=mcp_headers,
            json={
                "summary": "AAPL 50/200 SMA crossover: weak signal.",
                "confidence": 0.4,
                "notes": [
                    "Backtest produced positive but low-magnitude returns."
                ],
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "DONE"

        # Fetch and confirm persistence end-to-end.
        response = mcp_client.get(
            f"/api/v1/exploration-tasks/{task_id}", headers=mcp_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "DONE"
        assert body["claimed_by"] == agent_id
        assert body.get("findings") is not None
        assert "weak signal" in body["findings"]["summary"]
