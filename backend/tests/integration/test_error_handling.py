"""Integration tests for error handling and edge cases.

These tests verify that the API properly handles error conditions and
returns appropriate status codes and error messages.
"""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient


def test_get_nonexistent_portfolio_returns_404(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test accessing non-existent portfolio returns 404."""
    fake_portfolio_id = uuid4()

    response = client.get(
        f"/api/v1/portfolios/{fake_portfolio_id}",
        headers={"X-User-Id": str(default_user_id)},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_portfolio_without_user_id_returns_400(
    client: TestClient,
) -> None:
    """Test creating portfolio without X-User-Id header fails."""
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Test", "initial_deposit": "1000.00", "currency": "USD"},
    )

    # Should fail due to missing authentication header
    assert response.status_code == 400
    assert "X-User-Id" in response.json()["detail"]


def test_create_portfolio_with_invalid_user_id_returns_400(
    client: TestClient,
) -> None:
    """Test creating portfolio with invalid UUID in header fails."""
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": "not-a-valid-uuid"},
        json={"name": "Test", "initial_deposit": "1000.00", "currency": "USD"},
    )

    assert response.status_code == 400
    assert "Invalid X-User-Id" in response.json()["detail"]


def test_buy_with_insufficient_funds_fails(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test buying stocks with insufficient cash returns error."""
    # Create portfolio with only $1000
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
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
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100"},
    )

    assert trade_response.status_code == 400
    # Error message should mention insufficient funds
    error_text = str(trade_response.json()).lower()
    assert "insufficient" in error_text


def test_sell_stock_not_owned_fails(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test selling stock that's not in holdings returns error."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
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
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "SELL", "ticker": "AAPL", "quantity": "10"},
    )

    assert trade_response.status_code == 400
    # Error message should mention not found or insufficient
    error_text = str(trade_response.json()).lower()
    assert "not found" in error_text or "insufficient" in error_text


def test_sell_more_shares_than_owned_fails(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test selling more shares than owned returns error."""
    # Create portfolio and buy 10 shares
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
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
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "10"},
    )

    # Try to sell 20 shares (we only have 10)
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "SELL", "ticker": "AAPL", "quantity": "20"},
    )

    assert trade_response.status_code == 400
    error_text = str(trade_response.json()).lower()
    assert "insufficient" in error_text


def test_withdraw_more_than_balance_fails(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test withdrawing more cash than available returns error."""
    # Create portfolio with $1000
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
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
        headers={"X-User-Id": str(default_user_id)},
        json={"amount": "2000.00", "currency": "USD"},
    )

    assert withdraw_response.status_code == 400
    error_text = str(withdraw_response.json()).lower()
    assert "insufficient" in error_text


def test_access_other_users_portfolio_returns_403(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that users cannot access portfolios they don't own."""
    # Create portfolio as user 1
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "User 1 Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to access as user 2
    other_user_id = uuid4()
    get_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}",
        headers={"X-User-Id": str(other_user_id)},
    )

    # Should be forbidden (user 2 doesn't own this portfolio)
    assert get_response.status_code == 403
    assert "permission" in get_response.json()["detail"].lower()


def test_create_portfolio_with_zero_deposit_fails(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that creating portfolio with zero or negative deposit fails validation."""
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
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
    default_user_id: UUID,
) -> None:
    """Test that creating portfolio with negative deposit fails validation."""
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
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
    default_user_id: UUID,
) -> None:
    """Test that trading zero shares fails validation."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
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
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "0"},
    )

    # Should fail validation (quantity must be > 0)
    assert trade_response.status_code == 422  # Validation error


def test_trade_with_invalid_ticker_fails(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that trading with an unknown ticker fails appropriately."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
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
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "ZZZZ", "quantity": "10"},
    )

    # Should fail because ticker is not found in market data
    assert trade_response.status_code == 404
    assert "not found" in trade_response.json()["detail"].lower()
