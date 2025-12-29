"""Integration tests for the API endpoints."""

from uuid import UUID

from fastapi.testclient import TestClient


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """Test that the health check endpoint returns a 200 status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_openapi_docs_accessible(client: TestClient) -> None:
    """Test that OpenAPI documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_api_v1_root_endpoint(client: TestClient) -> None:
    """Test that the API v1 root endpoint is accessible."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_get_portfolio_balance(client: TestClient, default_user_id: UUID) -> None:
    """Test GET /api/v1/portfolios/{id}/balance returns balance correctly."""
    # Create portfolio with initial deposit
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "Test Portfolio", "initial_deposit": "10000.00", "currency": "USD"},
    )
    assert response.status_code == 201
    portfolio_id = response.json()["portfolio_id"]

    # Get balance
    response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert response.status_code == 200

    data = response.json()
    assert "amount" in data
    assert "currency" in data
    assert "as_of" in data
    assert data["amount"] == "10000.00"
    assert data["currency"] == "USD"


def test_execute_buy_trade(client: TestClient, default_user_id: UUID) -> None:
    """Test POST /api/v1/portfolios/{id}/trades for BUY action."""
    # Create portfolio with cash
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "Trading Portfolio", "initial_deposit": "50000.00", "currency": "USD"},
    )
    assert response.status_code == 201
    portfolio_id = response.json()["portfolio_id"]

    # Execute buy trade
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "action": "BUY",
            "ticker": "AAPL",
            "quantity": "10",
            "price": "150.00",
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert "transaction_id" in data

    # Verify holdings updated
    holdings_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert holdings_response.status_code == 200
    holdings = holdings_response.json()["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "10.0000"


def test_create_portfolio_and_list(client: TestClient, default_user_id: UUID) -> None:
    """Test portfolio appears in list after creation."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "New Portfolio", "initial_deposit": "5000.00", "currency": "USD"},
    )
    assert response.status_code == 201
    portfolio_id = response.json()["portfolio_id"]

    # List portfolios
    response = client.get(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert response.status_code == 200
    portfolios = response.json()
    assert len(portfolios) == 1
    assert portfolios[0]["id"] == portfolio_id
    assert portfolios[0]["name"] == "New Portfolio"


def test_holdings_after_multiple_trades(client: TestClient, default_user_id: UUID) -> None:
    """Test holdings are calculated correctly after buy and sell."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={"name": "Trading Portfolio", "initial_deposit": "100000.00", "currency": "USD"},
    )
    assert response.status_code == 201
    portfolio_id = response.json()["portfolio_id"]

    # Buy 100 shares of AAPL
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100", "price": "150.00"},
    )
    assert response.status_code == 201

    # Sell 30 shares of AAPL
    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "SELL", "ticker": "AAPL", "quantity": "30", "price": "155.00"},
    )
    assert response.status_code == 201

    # Check holdings
    response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert response.status_code == 200
    holdings = response.json()["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "70.0000"  # 100 - 30
