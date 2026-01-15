"""Integration tests for error handling and edge cases.

These tests verify that the API properly handles error conditions and
returns appropriate status codes and error messages.
"""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient


def test_get_nonexistent_portfolio_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test accessing non-existent portfolio returns 404."""
    fake_portfolio_id = uuid4()

    response = client.get(
        f"/api/v1/portfolios/{fake_portfolio_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_portfolio_without_user_id_returns_400(
    client: TestClient,
) -> None:
    """Test creating portfolio without Authorization header fails with 401."""
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Test", "initial_deposit": "1000.00", "currency": "USD"},
    )

    # Should fail due to missing authentication header (401 Unauthorized)
    assert response.status_code == 401


def test_create_portfolio_with_invalid_user_id_returns_400(
    client: TestClient,
) -> None:
    """Test creating portfolio with invalid bearer token fails with 401."""
    response = client.post(
        "/api/v1/portfolios",
        headers={"Authorization": "Bearer invalid-token"},
        json={"name": "Test", "initial_deposit": "1000.00", "currency": "USD"},
    )

    # Should fail due to invalid token (401 Unauthorized)
    assert response.status_code == 401


def test_buy_with_insufficient_funds_fails(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test buying stocks with insufficient cash returns structured error."""
    # Create portfolio with only $1000
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Poor Portfolio",
            "initial_deposit": "1000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to buy 100 shares (will cost $15,000 at seeded price of $150)
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100"},
    )

    assert trade_response.status_code == 400

    # Verify structured error response
    error_data = trade_response.json()
    assert "detail" in error_data
    detail = error_data["detail"]

    # Should be a structured error with type and amounts
    assert isinstance(detail, dict)
    assert detail["type"] == "insufficient_funds"
    assert "message" in detail
    assert "available" in detail
    assert "required" in detail
    assert "shortfall" in detail

    # Verify amounts are correct
    assert detail["available"] == 1000.00
    assert detail["required"] == 15000.00
    assert detail["shortfall"] == 14000.00


def test_sell_stock_not_owned_fails(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test selling stock that's not in holdings returns structured error."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Empty Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to sell stock we don't own
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "SELL", "ticker": "AAPL", "quantity": "10"},
    )

    assert trade_response.status_code == 400

    # Verify structured error response
    error_data = trade_response.json()
    detail = error_data["detail"]
    assert isinstance(detail, dict)
    assert detail["type"] == "insufficient_shares"
    assert detail["ticker"] == "AAPL"
    assert detail["available"] == 0.0
    assert detail["required"] == 10.0
    assert detail["shortfall"] == 10.0


def test_sell_more_shares_than_owned_fails(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test selling more shares than owned returns structured error."""
    # Create portfolio and buy 10 shares
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Trading Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Buy 10 shares of AAPL (price will be fetched automatically)
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "BUY", "ticker": "AAPL", "quantity": "10"},
    )

    # Try to sell 20 shares (we only have 10)
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "SELL", "ticker": "AAPL", "quantity": "20"},
    )

    assert trade_response.status_code == 400

    # Verify structured error response
    error_data = trade_response.json()
    detail = error_data["detail"]
    assert isinstance(detail, dict)
    assert detail["type"] == "insufficient_shares"
    assert detail["ticker"] == "AAPL"
    assert detail["available"] == 10.0
    assert detail["required"] == 20.0
    assert detail["shortfall"] == 10.0


def test_withdraw_more_than_balance_fails(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test withdrawing more cash than available returns structured error."""
    # Create portfolio with $1000
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Cash Portfolio",
            "initial_deposit": "1000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to withdraw $2000 (more than available)
    withdraw_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/withdraw",
        headers=auth_headers,
        json={"amount": "2000.00", "currency": "USD"},
    )

    assert withdraw_response.status_code == 400

    # Verify structured error response
    error_data = withdraw_response.json()
    detail = error_data["detail"]
    assert isinstance(detail, dict)
    assert detail["type"] == "insufficient_funds"
    assert detail["available"] == 1000.00
    assert detail["required"] == 2000.00
    assert detail["shortfall"] == 1000.00


def test_access_other_users_portfolio_returns_403(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that users cannot access portfolios they don't own."""
    # Import necessary modules
    from zebu.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
    from zebu.adapters.inbound.api.dependencies import get_auth_port
    from zebu.application.ports.auth_port import AuthenticatedUser
    from zebu.main import app

    # Create portfolio as user 1
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "User 1 Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Add a second user to the auth adapter
    auth_factory = app.dependency_overrides[get_auth_port]
    auth_adapter = auth_factory()
    assert isinstance(auth_adapter, InMemoryAuthAdapter)

    user_2 = AuthenticatedUser(id="test-user-2-alt", email="user2alt@test.com")
    auth_adapter.add_user(user_2, "test-token-user-2-alt")
    user_2_headers = {"Authorization": "Bearer test-token-user-2-alt"}

    # Try to access as user 2
    get_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=user_2_headers,
    )

    # Should be forbidden (user 2 doesn't own this portfolio)
    assert get_response.status_code == 403
    assert "permission" in get_response.json()["detail"].lower()


def test_create_portfolio_with_zero_deposit_fails(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that creating portfolio with zero or negative deposit fails validation."""
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Zero Portfolio",
            "initial_deposit": "0.00",
            "currency": "USD",
        },
    )

    # Should fail validation (initial_deposit must be > 0)
    assert response.status_code == 422  # Validation error


def test_create_portfolio_with_negative_deposit_fails(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that creating portfolio with negative deposit fails validation."""
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Negative Portfolio",
            "initial_deposit": "-1000.00",
            "currency": "USD",
        },
    )

    # Should fail validation (initial_deposit must be > 0)
    assert response.status_code == 422  # Validation error


def test_trade_with_zero_quantity_fails(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that trading zero shares fails validation."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Test Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to buy 0 shares
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "BUY", "ticker": "AAPL", "quantity": "0"},
    )

    # Should fail validation (quantity must be > 0)
    assert trade_response.status_code == 422  # Validation error


def test_trade_with_invalid_ticker_fails(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that trading with an unknown ticker returns structured error."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Test Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to buy stock with unknown ticker (not in seeded test data)
    # Using a valid format ticker (1-5 chars) but not in our seeded data
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "BUY", "ticker": "ZZZZ", "quantity": "10"},
    )

    # Should fail because ticker is not found in market data
    assert trade_response.status_code == 404

    # Verify structured error response
    error_data = trade_response.json()
    detail = error_data["detail"]
    assert isinstance(detail, dict)
    assert detail["type"] == "ticker_not_found"
    assert "message" in detail
    assert "ZZZZ" in detail["message"]
    assert detail["ticker"] == "ZZZZ"
