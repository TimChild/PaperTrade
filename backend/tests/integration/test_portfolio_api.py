"""Integration tests for portfolio API endpoints.

These tests verify that the portfolio endpoints work correctly end-to-end,
including database persistence and proper error handling.
"""

from datetime import datetime
from uuid import UUID

from fastapi.testclient import TestClient


def _parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO 8601 datetime string to datetime object.

    Handles both 'Z' suffix and '+00:00' timezone formats.

    Args:
        iso_string: ISO 8601 formatted datetime string

    Returns:
        datetime object in UTC timezone
    """
    return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))


def test_create_portfolio_with_initial_deposit(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test creating a portfolio with initial deposit.

    Creates portfolio and transaction.
    """
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
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
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    portfolios = list_response.json()
    assert len(portfolios) == 1
    assert portfolios[0]["id"] == portfolio_id
    assert portfolios[0]["name"] == "My Portfolio"


def test_get_portfolio_balance_after_creation(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test balance endpoint returns correct amount after portfolio creation.

    This test would have caught Bug #2 from Task 016: balance endpoint crash
    due to field name mismatch (cash_balance vs balance).
    """
    # Create portfolio with $10,000 deposit
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
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
        headers=auth_headers,
    )

    # This would have FAILED before Bug #2 fix!
    assert balance_response.status_code == 200

    balance_data = balance_response.json()
    assert "cash_balance" in balance_data
    assert "holdings_value" in balance_data
    assert "total_value" in balance_data
    assert "currency" in balance_data
    assert "as_of" in balance_data
    assert balance_data["cash_balance"] == "10000.00"
    assert balance_data["holdings_value"] == "0.00"
    assert balance_data["total_value"] == "10000.00"
    assert balance_data["currency"] == "USD"


def test_execute_buy_trade_and_verify_holdings(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test buying stock updates holdings correctly.

    This test would have caught Bug #3 from Task 016: trading functionality broken.
    """
    # Create portfolio with cash
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
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
        headers=auth_headers,
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
        headers=auth_headers,
    )
    assert holdings_response.status_code == 200

    holdings_data = holdings_response.json()
    assert "holdings" in holdings_data
    holdings = holdings_data["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "10.0000"

    # Verify balance decreased and holdings value increased
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers=auth_headers,
    )
    balance_data = balance_response.json()
    # $50,000 - (10 shares * $150) = $48,500 cash
    # Holdings: 10 shares * $150 = $1,500
    # Total: $50,000 (unchanged)
    assert balance_data["cash_balance"] == "48500.00"
    assert balance_data["holdings_value"] == "1500.00"
    assert balance_data["total_value"] == "50000.00"


def test_buy_and_sell_updates_holdings_correctly(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test buy followed by sell updates holdings and balance correctly."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
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
        headers=auth_headers,
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100"},
    )

    # Sell 30 shares of AAPL (price will be fetched automatically)
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={"action": "SELL", "ticker": "AAPL", "quantity": "30"},
    )

    # Verify holdings: 100 - 30 = 70 shares
    holdings_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/holdings",
        headers=auth_headers,
    )
    holdings = holdings_response.json()["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == "70.0000"

    # Verify balance
    # Start: $100,000
    # Buy: -$15,000 (100 * $150)
    # Sell: +$4,500 (30 * $150)
    # Cash: $89,500
    # Holdings: 70 * $150 = $10,500
    # Total: $100,000
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers=auth_headers,
    )
    balance_data = balance_response.json()
    assert balance_data["cash_balance"] == "89500.00"
    assert balance_data["holdings_value"] == "10500.00"
    assert balance_data["total_value"] == "100000.00"


def test_get_portfolios_returns_only_user_portfolios(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that list portfolios only returns portfolios owned by the current user.

    This would have caught Bug #1 from Task 016: user ID mismatch issues.
    """
    # Import the auth adapter from conftest to add a second user
    from papertrade.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
    from papertrade.adapters.inbound.api.dependencies import get_auth_port
    from papertrade.application.ports.auth_port import AuthenticatedUser
    from papertrade.main import app

    # Get the test auth adapter and add a second user
    # The override is a function, so we need to call it
    auth_factory = app.dependency_overrides[get_auth_port]
    auth_adapter = auth_factory()
    assert isinstance(auth_adapter, InMemoryAuthAdapter)

    user_2 = AuthenticatedUser(id="test-user-2", email="user2@test.com")
    auth_adapter.add_user(user_2, "test-token-user-2")
    user_2_headers = {"Authorization": "Bearer test-token-user-2"}

    # Create portfolio for user 1
    response1 = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "User 1 Portfolio",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    assert response1.status_code == 201

    # Create portfolio for user 2 (different user)
    response2 = client.post(
        "/api/v1/portfolios",
        headers=user_2_headers,
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
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    portfolios = list_response.json()
    assert len(portfolios) == 1
    assert portfolios[0]["name"] == "User 1 Portfolio"
    assert portfolios[0]["user_id"] == str(default_user_id)


def test_deposit_and_withdraw_cash(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test depositing and withdrawing cash updates balance correctly."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
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
        headers=auth_headers,
        json={"amount": "5000.00", "currency": "USD"},
    )
    assert deposit_response.status_code == 201

    # Verify balance increased
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers=auth_headers,
    )
    assert balance_response.json()["cash_balance"] == "15000.00"
    assert balance_response.json()["total_value"] == "15000.00"

    # Withdraw $3,000
    withdraw_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/withdraw",
        headers=auth_headers,
        json={"amount": "3000.00", "currency": "USD"},
    )
    assert withdraw_response.status_code == 201

    # Verify balance decreased
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers=auth_headers,
    )
    assert balance_response.json()["cash_balance"] == "12000.00"
    assert balance_response.json()["total_value"] == "12000.00"


def test_multiple_portfolios_for_same_user(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that a user can create multiple portfolios."""
    # Create first portfolio
    response1 = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
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
        headers=auth_headers,
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
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    portfolios = list_response.json()
    assert len(portfolios) == 2

    portfolio_names = {p["name"] for p in portfolios}
    assert "Growth Portfolio" in portfolio_names
    assert "Income Portfolio" in portfolio_names


def test_execute_trade_with_as_of_uses_historical_price(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that trades with as_of parameter use historical prices for backtesting."""
    from datetime import UTC, datetime

    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Backtest Portfolio",
            "initial_deposit": "100000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute backtest trade with as_of timestamp
    # Use AAPL which is seeded in test fixtures
    # The fixture creates a price with current timestamp, which should be
    # within the ±1 hour window for get_price_at
    backtest_date = datetime.now(UTC)

    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={
            "action": "BUY",
            "ticker": "AAPL",
            "quantity": "10",
            "as_of": backtest_date.isoformat(),
        },
    )

    assert trade_response.status_code == 201
    trade_data = trade_response.json()
    assert "transaction_id" in trade_data

    # Verify the transaction was created with correct timestamp
    transactions_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=auth_headers,
    )
    assert transactions_response.status_code == 200

    transactions = transactions_response.json()["transactions"]
    # Filter out the initial deposit transaction
    buy_transactions = [t for t in transactions if t["transaction_type"] == "BUY"]
    assert len(buy_transactions) == 1

    buy_transaction = buy_transactions[0]
    assert buy_transaction["ticker"] == "AAPL"
    assert buy_transaction["quantity"] == "10.0000"
    # Verify the timestamp matches the backtest date (within a second)
    transaction_timestamp = _parse_iso_datetime(buy_transaction["timestamp"])
    # Allow 1 second tolerance for timestamp comparison
    time_diff = abs((transaction_timestamp - backtest_date).total_seconds())
    assert time_diff < 1.0


def test_execute_trade_without_as_of_uses_current_price(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that trades without as_of parameter use current prices (normal mode)."""
    from datetime import UTC, datetime, timedelta

    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Normal Trading Portfolio",
            "initial_deposit": "50000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute normal trade without as_of
    before_trade = datetime.now(UTC)

    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={
            "action": "BUY",
            "ticker": "AAPL",
            "quantity": "5",
            # No as_of parameter - should use current time
        },
    )

    after_trade = datetime.now(UTC)

    assert trade_response.status_code == 201

    # Verify the transaction timestamp is recent (within last minute)
    transactions_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=auth_headers,
    )

    transactions = transactions_response.json()["transactions"]
    buy_transactions = [t for t in transactions if t["transaction_type"] == "BUY"]
    assert len(buy_transactions) == 1

    buy_transaction = buy_transactions[0]
    transaction_timestamp = _parse_iso_datetime(buy_transaction["timestamp"])

    # Transaction should be within a few seconds of now
    assert before_trade <= transaction_timestamp <= after_trade + timedelta(seconds=5)


def test_trade_with_future_as_of_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that trades with future as_of timestamps are rejected."""
    from datetime import UTC, datetime, timedelta

    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Future Test Portfolio",
            "initial_deposit": "50000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Try to execute trade with future timestamp
    future_date = datetime.now(UTC) + timedelta(days=7)

    trade_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={
            "action": "BUY",
            "ticker": "AAPL",
            "quantity": "10",
            "as_of": future_date.isoformat(),
        },
    )

    # Should be rejected with validation error
    assert trade_response.status_code == 422  # Unprocessable Entity (validation error)
    error_data = trade_response.json()
    assert "detail" in error_data


def test_delete_portfolio_success(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test successful deletion of a portfolio."""
    # Create a portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Portfolio to Delete",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    assert response.status_code == 201
    portfolio_id = response.json()["portfolio_id"]

    # Verify portfolio exists
    get_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200

    # Delete the portfolio
    delete_response = client.delete(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    # Verify portfolio is gone
    get_after_delete = client.get(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=auth_headers,
    )
    assert get_after_delete.status_code == 404


def test_delete_portfolio_removes_transactions(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that deleting a portfolio also deletes its transactions."""
    # Create a portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Portfolio with Transactions",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Add a deposit transaction
    deposit_response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/deposit",
        headers=auth_headers,
        json={"amount": "5000.00", "currency": "USD"},
    )
    assert deposit_response.status_code == 201

    # Verify transactions exist
    transactions_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=auth_headers,
    )
    assert transactions_response.status_code == 200
    transactions = transactions_response.json()["transactions"]
    assert len(transactions) >= 2  # Initial deposit + manual deposit

    # Delete the portfolio
    delete_response = client.delete(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    # Verify transactions endpoint returns 404 (portfolio doesn't exist)
    transactions_after = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=auth_headers,
    )
    assert transactions_after.status_code == 404


def test_delete_nonexistent_portfolio_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Test that deleting a non-existent portfolio returns 404."""
    from uuid import uuid4

    nonexistent_id = uuid4()

    delete_response = client.delete(
        f"/api/v1/portfolios/{nonexistent_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 404


def test_delete_other_users_portfolio_returns_403(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that users cannot delete portfolios owned by other users."""
    from papertrade.adapters.auth.in_memory_adapter import InMemoryAuthAdapter
    from papertrade.adapters.inbound.api.dependencies import get_auth_port
    from papertrade.application.ports.auth_port import AuthenticatedUser

    # Get the app's auth adapter and register a second user
    app = client.app
    auth_factory = app.dependency_overrides[get_auth_port]
    auth_adapter = auth_factory()
    assert isinstance(auth_adapter, InMemoryAuthAdapter)

    user_2 = AuthenticatedUser(id="test-user-2", email="user2@test.com")
    auth_adapter.add_user(user_2, "test-token-user-2")
    user_2_headers = {"Authorization": "Bearer test-token-user-2"}

    # User 1 creates a portfolio
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

    # User 2 tries to delete User 1's portfolio
    delete_response = client.delete(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=user_2_headers,
    )
    assert delete_response.status_code == 403

    # Verify portfolio still exists for User 1
    get_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200


def test_delete_portfolio_does_not_affect_other_portfolios(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that deleting one portfolio doesn't affect other portfolios."""
    # Create two portfolios
    response1 = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Portfolio 1",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio1_id = response1.json()["portfolio_id"]

    response2 = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Portfolio 2",
            "initial_deposit": "20000.00",
            "currency": "USD",
        },
    )
    portfolio2_id = response2.json()["portfolio_id"]

    # Delete first portfolio
    delete_response = client.delete(
        f"/api/v1/portfolios/{portfolio1_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    # Verify first portfolio is gone
    get_response1 = client.get(
        f"/api/v1/portfolios/{portfolio1_id}",
        headers=auth_headers,
    )
    assert get_response1.status_code == 404

    # Verify second portfolio still exists
    get_response2 = client.get(
        f"/api/v1/portfolios/{portfolio2_id}",
        headers=auth_headers,
    )
    assert get_response2.status_code == 200
    assert get_response2.json()["name"] == "Portfolio 2"


def test_delete_portfolio_removes_from_list(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that deleted portfolio is removed from the portfolio list."""
    # Create a portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Portfolio to Remove",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Verify it appears in the list
    list_before = client.get(
        "/api/v1/portfolios",
        headers=auth_headers,
    )
    assert list_before.status_code == 200
    assert len(list_before.json()) == 1

    # Delete the portfolio
    delete_response = client.delete(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    # Verify it's removed from the list
    list_after = client.get(
        "/api/v1/portfolios",
        headers=auth_headers,
    )
    assert list_after.status_code == 200
    assert len(list_after.json()) == 0


def test_total_value_includes_both_cash_and_holdings(
    client: TestClient,
    auth_headers: dict[str, str],
    default_user_id: UUID,
) -> None:
    """Test that total_value correctly sums cash_balance and holdings_value.
    
    This test specifically addresses Task 077: Fix Total Value Calculation.
    Ensures that total_value is not just cash_balance, but includes holdings market value.
    """
    # Create portfolio with $5,000
    response = client.post(
        "/api/v1/portfolios",
        headers=auth_headers,
        json={
            "name": "Total Value Test",
            "initial_deposit": "5000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]
    
    # Initial balance: all cash, no holdings
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers=auth_headers,
    )
    balance = balance_response.json()
    assert balance["cash_balance"] == "5000.00"
    assert balance["holdings_value"] == "0.00"
    assert balance["total_value"] == "5000.00"
    
    # Buy 1 AAPL @ $150
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={
            "action": "BUY",
            "ticker": "AAPL",
            "quantity": "1",
        },
    )
    
    # After purchase: cash reduced, holdings increased, total unchanged
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers=auth_headers,
    )
    balance = balance_response.json()
    
    # Cash should be: $5000 - (1 * $150) = $4,850
    assert balance["cash_balance"] == "4850.00"
    
    # Holdings should be: 1 * $150 = $150
    assert balance["holdings_value"] == "150.00"
    
    # Total should STILL be $5,000 (cash + holdings)
    # This was the bug - total_value was showing only cash_balance
    assert balance["total_value"] == "5000.00"
    
    # Buy 2 MSFT @ $380
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=auth_headers,
        json={
            "action": "BUY",
            "ticker": "MSFT",
            "quantity": "2",
        },
    )
    
    # After second purchase
    balance_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/balance",
        headers=auth_headers,
    )
    balance = balance_response.json()
    
    # Cash: $5000 - $150 - $760 = $4,090
    assert balance["cash_balance"] == "4090.00"
    
    # Holdings: (1 * $150) + (2 * $380) = $910
    assert balance["holdings_value"] == "910.00"
    
    # Total: $4,090 + $910 = $5,000
    assert balance["total_value"] == "5000.00"
    
    # Verify all three values are distinct and correct
    assert balance["cash_balance"] != balance["holdings_value"]
    assert balance["cash_balance"] != balance["total_value"]
    assert balance["holdings_value"] != balance["total_value"]
    delete_response = client.delete(
        f"/api/v1/portfolios/{portfolio_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    # Verify it's removed from the list
    list_after = client.get(
        "/api/v1/portfolios",
        headers=auth_headers,
    )
    assert list_after.status_code == 200
    assert len(list_after.json()) == 0
