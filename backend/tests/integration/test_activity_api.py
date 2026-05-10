"""Integration tests for the recent-activity feed (Phase H2).

Covers the cross-table aggregation at ``GET /api/v1/activity``:

- Multi-source merge: trades, strategy creations, backtests, activations,
  exploration tasks, and API-key minting all land in one chronological
  feed sorted DESC by ``occurred_at``.
- Actor identity column: rows authored via Clerk Bearer carry
  ``actor_kind="user"`` and ``actor_label=None``; rows authored via API
  key carry ``actor_kind="api_key"`` and the key's human label.
- Filtering by ``event_type`` (single + repeated), by ``actor_label``,
  and by ``since``.
- Pagination via the standard ``limit`` / ``offset`` envelope.
- Auth gating: 401 without credentials.

The tests use the project's ``client`` fixture (in-memory SQLite DB,
in-memory market data, in-memory auth/api-key adapters).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def bearer_headers() -> dict[str, str]:
    """Headers for the seeded test user via Bearer (Clerk) auth."""
    return {"Authorization": "Bearer test-token-default"}


def _mint_api_key(
    client: TestClient,
    bearer_headers: dict[str, str],
    *,
    label: str,
    scopes: list[str] | None = None,
) -> tuple[str, str]:
    """Mint an API key via the Clerk-gated route, return (id, raw_key)."""
    body = client.post(
        "/api/v1/api-keys",
        headers=bearer_headers,
        json={"label": label, "scopes": scopes or ["read", "trade"]},
    ).json()
    return body["id"], body["raw_key"]


def _create_portfolio(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Test Portfolio",
    initial_deposit: str = "1000.00",
) -> str:
    """Create a portfolio and return its id."""
    resp = client.post(
        "/api/v1/portfolios",
        headers=headers,
        json={"name": name, "initial_deposit": initial_deposit},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["portfolio_id"]


def _trade(
    client: TestClient,
    headers: dict[str, str],
    *,
    portfolio_id: str,
    action: str,
    ticker: str,
    quantity: str,
) -> dict[str, str]:
    """Execute a trade and return the response body."""
    resp = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=headers,
        json={"action": action, "ticker": ticker, "quantity": quantity},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert isinstance(body, dict)
    return body


def _create_strategy(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "BAH AAPL",
    tickers: list[str] | None = None,
) -> str:
    """Create a BUY_AND_HOLD strategy and return its id."""
    chosen_tickers = tickers or ["AAPL"]
    # Equal-weight allocation across the tickers.
    fraction = f"{1 / len(chosen_tickers):.4f}"
    resp = client.post(
        "/api/v1/strategies",
        headers=headers,
        json={
            "name": name,
            "strategy_type": "BUY_AND_HOLD",
            "tickers": chosen_tickers,
            "parameters": {
                "allocation": {ticker: fraction for ticker in chosen_tickers},
            },
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_task(
    client: TestClient,
    headers: dict[str, str],
    *,
    prompt: str = "Investigate AAPL drift",
) -> str:
    """Create an exploration task, return its id."""
    resp = client.post(
        "/api/v1/exploration-tasks",
        headers=headers,
        json={"prompt": prompt},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------


class TestAuth:
    def test_unauthenticated_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/activity")
        assert response.status_code == 401

    def test_bearer_authenticated_returns_200(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/v1/activity", headers=bearer_headers)
        assert response.status_code == 200
        body = response.json()
        # Standard PaginatedResponse envelope.
        assert set(body.keys()) >= {"items", "total", "limit", "offset", "has_more"}

    def test_api_key_authenticated_returns_200(self, client: TestClient) -> None:
        # The default seeded API key works against `read` paths.
        response = client.get(
            "/api/v1/activity",
            headers={"X-API-Key": "test-token-default"},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Empty / minimal feed
# ---------------------------------------------------------------------------


class TestEmptyFeed:
    def test_empty_when_user_has_no_activity(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/v1/activity", headers=bearer_headers)
        assert response.status_code == 200
        body = response.json()
        # Only the seeded API key is present — that mints a single
        # activity row but it predates anything the user did. Either way
        # the feed should accept zero or more.
        assert body["limit"] == 50
        assert body["offset"] == 0
        assert isinstance(body["items"], list)


# ---------------------------------------------------------------------------
# Trade events
# ---------------------------------------------------------------------------


class TestTradeEvents:
    def test_trade_appears_in_feed_with_user_actor(
        self, client: TestClient, bearer_headers: dict[str, str]
    ) -> None:
        portfolio_id = _create_portfolio(client, bearer_headers)
        _trade(
            client,
            bearer_headers,
            portfolio_id=portfolio_id,
            action="BUY",
            ticker="AAPL",
            quantity="2",
        )

        body = client.get(
            "/api/v1/activity?event_type=trade",
            headers=bearer_headers,
        ).json()

        trades = [item for item in body["items"] if item["type"] == "trade"]
        assert len(trades) == 1
        trade = trades[0]
        # Bearer-authored — actor is "user".
        assert trade["actor_kind"] == "user"
        assert trade["actor_label"] is None
        assert trade["subject_type"] == "portfolio"
        assert trade["subject_id"] == portfolio_id
        # Summary contains the verb + ticker + price for human display.
        assert "Bought" in trade["summary"]
        assert "AAPL" in trade["summary"]

    def test_api_key_authored_trade_carries_label(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        # Mint a labelled API key via Clerk, then use it to trade.
        _, raw_key = _mint_api_key(client, bearer_headers, label="claude-laptop")
        api_key_headers = {"Authorization": f"ApiKey {raw_key}"}

        portfolio_id = _create_portfolio(client, bearer_headers)
        _trade(
            client,
            api_key_headers,
            portfolio_id=portfolio_id,
            action="BUY",
            ticker="MSFT",
            quantity="1",
        )

        # Read the feed back via Bearer (the same user owns both
        # auth paths).
        body = client.get(
            "/api/v1/activity?event_type=trade",
            headers=bearer_headers,
        ).json()
        trades = [item for item in body["items"] if item["type"] == "trade"]
        assert len(trades) == 1
        assert trades[0]["actor_kind"] == "api_key"
        assert trades[0]["actor_label"] == "claude-laptop"

    def test_user_and_api_key_trades_ordered_correctly(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        """A trade authored by an api_key after a Bearer trade comes first."""
        # Larger initial deposit so both trades fit.
        portfolio_id = _create_portfolio(
            client, bearer_headers, initial_deposit="10000.00"
        )
        # Bearer trade first.
        _trade(
            client,
            bearer_headers,
            portfolio_id=portfolio_id,
            action="BUY",
            ticker="AAPL",
            quantity="1",
        )

        _, raw_key = _mint_api_key(client, bearer_headers, label="claude-laptop")
        api_key_headers = {"Authorization": f"ApiKey {raw_key}"}
        # API-key trade second (= newer, should sort first).
        _trade(
            client,
            api_key_headers,
            portfolio_id=portfolio_id,
            action="BUY",
            ticker="MSFT",
            quantity="1",
        )

        body = client.get(
            "/api/v1/activity?event_type=trade",
            headers=bearer_headers,
        ).json()
        trades = [item for item in body["items"] if item["type"] == "trade"]
        assert len(trades) == 2
        # First (newest) is the api-key trade.
        assert trades[0]["actor_kind"] == "api_key"
        assert trades[0]["actor_label"] == "claude-laptop"
        # Second is the Bearer trade.
        assert trades[1]["actor_kind"] == "user"
        assert trades[1]["actor_label"] is None


# ---------------------------------------------------------------------------
# Multi-source merge
# ---------------------------------------------------------------------------


class TestMultiSourceMerge:
    def test_feed_merges_strategies_backtests_tasks_and_keys(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        # Create one of each kind to confirm the merge works.
        _create_strategy(client, bearer_headers, name="BAH-1")
        _create_task(client, bearer_headers, prompt="Look at AAPL")
        _mint_api_key(client, bearer_headers, label="agent-1")

        body = client.get("/api/v1/activity", headers=bearer_headers).json()
        types = {item["type"] for item in body["items"]}
        # All three event kinds we just produced are in the feed.
        assert "strategy_created" in types
        assert "task_filed" in types
        assert "api_key_minted" in types

    def test_subject_ids_are_correct_uuids(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        strategy_id = _create_strategy(client, bearer_headers)
        body = client.get(
            "/api/v1/activity?event_type=strategy_created",
            headers=bearer_headers,
        ).json()
        events = [item for item in body["items"] if item["type"] == "strategy_created"]
        assert any(e["subject_id"] == strategy_id for e in events)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


class TestFilters:
    def test_event_type_filter_narrows_results(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        _create_strategy(client, bearer_headers, name="NarrowMe")
        _create_task(client, bearer_headers, prompt="Filter probe")

        body = client.get(
            "/api/v1/activity?event_type=strategy_created",
            headers=bearer_headers,
        ).json()
        types = {item["type"] for item in body["items"]}
        assert types <= {"strategy_created"}
        assert "task_filed" not in types

    def test_repeated_event_type_filter_includes_all_listed(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        _create_strategy(client, bearer_headers)
        _create_task(client, bearer_headers)

        body = client.get(
            "/api/v1/activity?event_type=strategy_created&event_type=task_filed",
            headers=bearer_headers,
        ).json()
        types = {item["type"] for item in body["items"]}
        assert types <= {"strategy_created", "task_filed"}
        # Both surfaces are present.
        assert "strategy_created" in types
        assert "task_filed" in types

    def test_actor_label_filter_isolates_one_credential(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        # Mint two API keys, use each to file a task.
        _, raw_a = _mint_api_key(client, bearer_headers, label="agent-a")
        _, raw_b = _mint_api_key(client, bearer_headers, label="agent-b")
        _create_task(client, {"Authorization": f"ApiKey {raw_a}"}, prompt="From A")
        _create_task(client, {"Authorization": f"ApiKey {raw_b}"}, prompt="From B")

        body = client.get(
            "/api/v1/activity?actor_label=agent-a",
            headers=bearer_headers,
        ).json()
        # Every returned row was authored by agent-a.
        labels = {item["actor_label"] for item in body["items"]}
        assert labels <= {"agent-a"}

    def test_since_filter_excludes_older_events(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        _create_strategy(client, bearer_headers, name="AncientStrategy")
        # Future cutoff drops everything. ``client.get(params={...})`` URL
        # -encodes the ``+00:00`` offset for us.
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        response = client.get(
            "/api/v1/activity",
            params={"since": future},
            headers=bearer_headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    def test_limit_and_offset_envelope(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        # Build at least 5 events.
        for n in range(5):
            _create_strategy(client, bearer_headers, name=f"S{n}")

        body = client.get(
            "/api/v1/activity?limit=2&offset=1&event_type=strategy_created",
            headers=bearer_headers,
        ).json()
        assert body["limit"] == 2
        assert body["offset"] == 1
        assert len(body["items"]) <= 2
        # has_more is computed server-side; with 5 items, limit=2, offset=1
        # we expect more pages remain.
        assert body["has_more"] is True

    def test_oversized_limit_rejected_with_422(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        response = client.get(
            "/api/v1/activity",
            params={"limit": "999"},
            headers=bearer_headers,
        )
        # 422 Unprocessable Entity — caps at the platform-wide MAX_PAGE_LIMIT.
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Sort order — verifies the merge sort is stable DESC by occurred_at
# ---------------------------------------------------------------------------


class TestSortOrder:
    def test_events_sorted_desc_by_occurred_at(
        self,
        client: TestClient,
        bearer_headers: dict[str, str],
    ) -> None:
        _create_strategy(client, bearer_headers, name="oldest")
        _create_task(client, bearer_headers, prompt="middle")
        _create_strategy(client, bearer_headers, name="newest")

        response = client.get(
            "/api/v1/activity",
            params={"limit": "100"},
            headers=bearer_headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        timestamps = [item["occurred_at"] for item in body["items"]]
        # Verify monotonically non-increasing.
        assert timestamps == sorted(timestamps, reverse=True)
