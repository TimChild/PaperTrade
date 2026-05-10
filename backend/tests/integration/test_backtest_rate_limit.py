"""Integration tests for Phase F-6 backtest rate limit on POST /backtests.

Covers:

- API-key requests beyond the per-minute cap return 429 with the
  standard error envelope and a ``Retry-After`` header.
- Clerk Bearer requests bypass the limiter — humans can run as many
  backtests as they want.
- The error envelope carries the bucket state so a caller can self-
  report "5/5 in last 60s; retry in 12s".
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from zebu.adapters.inbound.api import dependencies as deps
from zebu.adapters.inbound.api.dependencies import get_backtest_rate_limiter
from zebu.infrastructure.inbound_rate_limiter import InMemoryInboundRateLimiter


def _create_strategy(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Rate Limit Strategy",
) -> str:
    """Helper — create a buy-and-hold strategy and return its ID."""
    response = client.post(
        "/api/v1/strategies",
        headers=headers,
        json={
            "name": name,
            "strategy_type": "BUY_AND_HOLD",
            "tickers": ["AAPL"],
            "parameters": {"allocation": {"AAPL": 1.0}},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return str(body["id"])


def _backtest_body(strategy_id: str) -> dict[str, str]:
    """Helper — a minimal backtest request body."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=10)
    return {
        "strategy_id": strategy_id,
        "backtest_name": "Rate Limit Test",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "initial_cash": "10000.00",
    }


@pytest.fixture
def low_limit_override(client: TestClient) -> None:
    """Override the singleton with a low-limit limiter to make tests fast.

    The default 5/min would still work but each test would have to
    issue 6 backtests. With a 2/min override the test stays small.
    """
    low = InMemoryInboundRateLimiter(minute_limit=2, day_limit=100)

    def _get_low() -> InMemoryInboundRateLimiter:
        return low

    client.app.dependency_overrides[get_backtest_rate_limiter] = _get_low


class TestApiKeyRequestsAreRateLimited:
    """API-key requests beyond the per-minute cap return 429."""

    def test_third_backtest_with_api_key_returns_429(
        self,
        client: TestClient,
        low_limit_override: None,
    ) -> None:
        """2 succeed (cap=2), 3rd hits 429 with the standard envelope."""
        api_key_headers = {"Authorization": "ApiKey test-token-default"}
        strategy_id = _create_strategy(client, api_key_headers)
        body = _backtest_body(strategy_id)

        # First 2 backtests succeed.
        for i in range(2):
            response = client.post(
                "/api/v1/backtests",
                headers=api_key_headers,
                json={**body, "backtest_name": f"OK #{i}"},
            )
            assert response.status_code == 201, response.text

        # 3rd hits the limit.
        denied = client.post(
            "/api/v1/backtests",
            headers=api_key_headers,
            json={**body, "backtest_name": "DENIED"},
        )
        assert denied.status_code == 429, denied.text
        envelope = denied.json()
        # Standard error envelope.
        assert isinstance(envelope["detail"], str)
        assert "rate limit" in envelope["detail"].lower()
        assert envelope["code"] == "rate_limit_exceeded"
        assert envelope["fields"] is not None
        assert envelope["fields"]["minute_limit"] == "2"
        assert envelope["fields"]["minute_used"] == "2"
        assert envelope["fields"]["day_limit"] == "100"
        # Retry-After header populated and integer-seconds.
        retry_after = denied.headers["Retry-After"]
        assert retry_after.isdigit()
        assert int(retry_after) >= 1

    def test_clerk_bearer_bypasses_limit(
        self,
        client: TestClient,
        low_limit_override: None,
    ) -> None:
        """Bearer-authenticated (human) requests are unmetered."""
        bearer_headers = {"Authorization": "Bearer test-token-default"}
        strategy_id = _create_strategy(client, bearer_headers)
        body = _backtest_body(strategy_id)

        # Run many more than the 2/min API-key cap — none should 429.
        for i in range(5):
            response = client.post(
                "/api/v1/backtests",
                headers=bearer_headers,
                json={**body, "backtest_name": f"BearerOK #{i}"},
            )
            assert response.status_code == 201, response.text


class TestEnvelopeAccuracy:
    """The 429 envelope mirrors the limiter state correctly."""

    def test_envelope_includes_bucket_state_after_denial(
        self,
        client: TestClient,
    ) -> None:
        """Use the default 5/min limit; 6 rapid requests → 6th gets envelope.

        Default limits (5/min, 100/day) are exercised here so a regression
        in the production defaults surfaces in this test.
        """
        # Reset the singleton in case prior tests in the same session
        # touched it.
        deps._inbound_backtest_rate_limiter = None

        api_key_headers = {"Authorization": "ApiKey test-token-default"}
        strategy_id = _create_strategy(client, api_key_headers)
        body = _backtest_body(strategy_id)

        ok_count = 0
        last_denied_envelope: dict[str, object] | None = None
        for i in range(6):
            response = client.post(
                "/api/v1/backtests",
                headers=api_key_headers,
                json={**body, "backtest_name": f"Run #{i}"},
            )
            if response.status_code == 201:
                ok_count += 1
            elif response.status_code == 429:
                last_denied_envelope = response.json()

        assert ok_count == 5  # default minute cap
        assert last_denied_envelope is not None
        assert last_denied_envelope["code"] == "rate_limit_exceeded"
        fields = last_denied_envelope["fields"]
        assert isinstance(fields, dict)
        assert fields["minute_limit"] == "5"
        assert fields["minute_used"] == "5"
        # day_used is at least 5 (we have not crossed the day cap).
        assert int(fields["day_used"]) >= 5
