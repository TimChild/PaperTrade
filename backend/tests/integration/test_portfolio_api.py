"""Integration tests for portfolio API endpoints.

These tests verify that the portfolio endpoints work correctly end-to-end,
including database persistence and proper error handling.
"""

from uuid import UUID

from fastapi.testclient import TestClient


def test_create_portfolio_with_initial_deposit(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test creating a portfolio with initial deposit.

    Creates portfolio and transaction.
    """
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "My Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "portfolio_id" in data
    assert "transaction_id" in data

    portfolio_id = data["portfolio_id"]

    # Verify portfolio was created
    list_response = client.get(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert list_response.status_code == 200
    portfolios = list_response.json()
    assert len(portfolios) == 1
    assert portfolios[0]["id"] == portfolio_id
    assert portfolios[0]["name"] == "My Portfolio"


def test_get_portfolio_balance_after_creation(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test balance endpoint returns correct amount after portfolio creation.

    This test would have caught Bug #2 from Task 016: balance endpoint crash
    due to field name mismatch (cash_balance vs balance).
    """
    # Create portfolio with $10,000 deposit
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Balance Test Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Get balance
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )

    # This would have FAILED before Bug #2 fix!
    assert balance_response.status_code == 200

    balance_data = balance_response.json()
    assert "amount" in balance_data
    assert "currency" in balance_data
    assert "as_of" in balance_data
    assert balance_data["amount"] == "10000.00"
    assert balance_data["currency"] == "USD"


def test_execute_buy_trade_and_verify_holdings(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test buying stock updates holdings correctly.

    This test would have caught Bug #3 from Task 016: trading functionality broken.
    """
    # Create portfolio with cash
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Trading Portfolio",
            "initial_deposit": "50000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute buy trade (price will be fetched automatically)
    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "action": "BUY",
            "ticker": "AAPL",
            "quantity": "10",
        },
    )

    # This would have FAILED before Bug #3 fix!
    assert trade_response.status_code == 201
    trade_data = trade_response.json()
    assert "transaction_id" in trade_data

    # Verify holdings
    holdings_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert holdings_response.status_code == 200

    holdings_data = holdings_response.json()
    assert "holdings" in holdings_data
    holdings = holdings_data["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "10.0000"

    # Verify balance decreased
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )
    balance_data = balance_response.json()
    # $50,000 - (10 shares * $150) = $48,500
    assert balance_data["amount"] == "48500.00"


def test_buy_and_sell_updates_holdings_correctly(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test buy followed by sell updates holdings and balance correctly."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Trading Portfolio",
            "initial_deposit": "100000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Buy 100 shares of AAPL (price will be fetched automatically)
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100"},
    )

    # Sell 30 shares of AAPL (price will be fetched automatically)
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "SELL", "ticker": "AAPL", "quantity": "30"},
    )

    # Verify holdings: 100 - 30 = 70 shares
    holdings_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers={"X-User-Id": str(default_user_id)},
    )
    holdings = holdings_response.json()["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "70.0000"

    # Verify balance
    # Start: $100,000
    # Buy: -$15,000 (100 * $150)
    # Sell: +$4,500 (30 * $150)
    # End: $89,500
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )
    balance_data = balance_response.json()
    assert balance_data["amount"] == "89500.00"


def test_get_portfolios_returns_only_user_portfolios(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that list portfolios only returns portfolios owned by the current user.

    This would have caught Bug #1 from Task 016: user ID mismatch issues.
    """
    from uuid import uuid4

    # Create portfolio for user 1
    response1 = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "User 1 Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    assert response1.status_code == 201

    # Create portfolio for user 2 (different user)
    user_2_id = uuid4()
    response2 = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(user_2_id)},
        json={
            "name": "User 2 Portfolio",
            "initial_deposit": "20000.00",
            "currency": "USD",
        },
    )
    assert response2.status_code == 201

    # User 1 should only see their portfolio
    list_response = client.get(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert list_response.status_code == 200
    portfolios = list_response.json()
    assert len(portfolios) == 1
    assert portfolios[0]["name"] == "User 1 Portfolio"
    assert portfolios[0]["user_id"] == str(default_user_id)


def test_deposit_and_withdraw_cash(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test depositing and withdrawing cash updates balance correctly."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Cash Test Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Deposit $5,000
    deposit_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/deposit",
        headers={"X-User-Id": str(default_user_id)},
        json={"amount": "5000.00", "currency": "USD"},
    )
    assert deposit_response.status_code == 201

    # Verify balance increased
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert balance_response.json()["amount"] == "15000.00"

    # Withdraw $3,000
    withdraw_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/withdraw",
        headers={"X-User-Id": str(default_user_id)},
        json={"amount": "3000.00", "currency": "USD"},
    )
    assert withdraw_response.status_code == 201

    # Verify balance decreased
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert balance_response.json()["amount"] == "12000.00"


def test_multiple_portfolios_for_same_user(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that a user can create multiple portfolios."""
    # Create first portfolio
    response1 = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Growth Portfolio",
            "initial_deposit": "50000.00",
            "currency": "USD",
        },
    )
    assert response1.status_code == 201

    # Create second portfolio
    response2 = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Income Portfolio",
            "initial_deposit": "30000.00",
            "currency": "USD",
        },
    )
    assert response2.status_code == 201

    # Verify both portfolios exist
    list_response = client.get(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
    )
    assert list_response.status_code == 200
    portfolios = list_response.json()
    assert len(portfolios) == 2

    portfolio_names = {p["name"] for p in portfolios}
    assert "Growth Portfolio" in portfolio_names
    assert "Income Portfolio" in portfolio_names
