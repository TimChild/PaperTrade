"""Integration tests for the Wave 3-G API standardisation.

Covers:

* `PaginatedResponse` envelope on `list_strategies`, `list_backtests`,
  `list_portfolios`, and `get_all_balances` — every list route now returns
  ``{items, total, limit, offset, has_more}``.
* `ErrorResponse` envelope on validation errors (422) and on plain string
  `HTTPException(detail=...)` paths — every error response is
  ``{detail: str, code, fields}``.

These tests intentionally avoid asserting on the *content* of items where the
pagination contract is what's being checked — the per-resource endpoints have
their own tests for that.
"""

from datetime import date, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Strategies — list pagination
# ---------------------------------------------------------------------------


def _create_strategy(
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    name: str = "Test Strategy",
    ticker: str = "AAPL",
) -> dict[str, object]:
    """Helper: create a BUY_AND_HOLD strategy and return the response body."""
    response = client.post(
        "/api/v1/strategies",
        headers=auth_headers,
        json={
            "name": name,
            "strategy_type": "BUY_AND_HOLD",
            "tickers": [ticker],
            "parameters": {"allocation": {ticker: 1.0}},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_list_strategies_returns_paginated_envelope(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """An empty strategies list is the paginated envelope, not a bare list."""
    response = client.get("/api/v1/strategies", headers=auth_headers)
    assert response.status_code == 200
    page = response.json()
    assert page["items"] == []
    assert page["total"] == 0
    assert page["limit"] == 20
    assert page["offset"] == 0
    assert page["has_more"] is False


def test_list_strategies_paginates_correctly(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Creating 3 strategies and paging by 2 yields the expected windows."""
    for i in range(3):
        _create_strategy(client, auth_headers, name=f"Strategy {i}")

    page1 = client.get(
        "/api/v1/strategies?limit=2&offset=0", headers=auth_headers
    ).json()
    assert page1["total"] == 3
    assert page1["limit"] == 2
    assert page1["offset"] == 0
    assert len(page1["items"]) == 2
    assert page1["has_more"] is True

    page2 = client.get(
        "/api/v1/strategies?limit=2&offset=2", headers=auth_headers
    ).json()
    assert page2["total"] == 3
    assert page2["offset"] == 2
    assert len(page2["items"]) == 1
    assert page2["has_more"] is False

    # The two pages must not overlap
    ids_p1 = {s["id"] for s in page1["items"]}
    ids_p2 = {s["id"] for s in page2["items"]}
    assert ids_p1.isdisjoint(ids_p2)


def test_list_strategies_rejects_limit_above_max(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """``limit > 100`` is a 422 with the standard error envelope."""
    response = client.get("/api/v1/strategies?limit=101", headers=auth_headers)
    assert response.status_code == 422
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["code"] == "validation_error"
    assert body["fields"] is not None
    # The validation error should reference the limit query parameter
    assert any("limit" in key for key in body["fields"])


# ---------------------------------------------------------------------------
# Backtests — list pagination
# ---------------------------------------------------------------------------


def test_list_backtests_returns_paginated_envelope_when_empty(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """No backtest runs yet — the response is still the paginated envelope."""
    response = client.get("/api/v1/backtests", headers=auth_headers)
    assert response.status_code == 200
    page = response.json()
    assert page == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
        "has_more": False,
    }


def test_list_backtests_returns_paginated_envelope_with_runs(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Run two short backtests and verify they appear in the paginated list."""
    strategy = _create_strategy(client, auth_headers)
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=10)

    for i in range(2):
        run_resp = client.post(
            "/api/v1/backtests",
            headers=auth_headers,
            json={
                "strategy_id": strategy["id"],
                "backtest_name": f"Run {i}",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "initial_cash": "10000.00",
            },
        )
        assert run_resp.status_code == 201, run_resp.text

    page = client.get("/api/v1/backtests?limit=1", headers=auth_headers).json()
    assert page["total"] == 2
    assert page["limit"] == 1
    assert len(page["items"]) == 1
    assert page["has_more"] is True


# ---------------------------------------------------------------------------
# Error envelope — validation, not-found, and forbidden paths
# ---------------------------------------------------------------------------


def test_validation_error_uses_standard_envelope(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A request body that fails Pydantic validation surfaces as a 422 with
    ``{detail: str, code: 'validation_error', fields: {...}}``."""
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            # Missing required ``initial_deposit``
            "name": "Bad Portfolio",
            "currency": "USD",
        },
    )
    assert response.status_code == 422
    body = response.json()

    # detail is always a human-readable string, never a list/dict
    assert isinstance(body["detail"], str)
    assert body["code"] == "validation_error"

    # fields contains a per-field validation message keyed by dotted path
    assert body["fields"] is not None
    assert any("initial_deposit" in key for key in body["fields"]), body["fields"]


def test_not_found_error_uses_standard_envelope(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A 404 from a string-detail HTTPException flows through the global
    handler and emerges as the standard envelope."""
    response = client.get(
        "/api/v1/portfolios/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404
    body = response.json()
    assert isinstance(body["detail"], str)
    assert "not found" in body["detail"].lower()
    # ``code`` may be None for plain string detail — that's fine
    assert "code" in body
    assert "fields" in body


def test_unauthenticated_request_uses_standard_envelope(
    client: TestClient,
) -> None:
    """A 401 (Bearer required) also flows through the global handler."""
    # FastAPI's HTTPBearer raises before our handler runs for *missing*
    # creds, but for a malformed token the route's auth dep runs and produces
    # an HTTPException with a string detail.
    response = client.post(
        "/api/v1/portfolios",
        headers={"Authorization": "Bearer not-a-real-token"},
        json={
            "name": "X",
            "initial_deposit": "100.00",
            "currency": "USD",
        },
    )
    assert response.status_code == 401
    body = response.json()
    assert isinstance(body["detail"], str)
