"""Integration tests for transaction API endpoints.

These tests verify that transaction history tracking works correctly.
"""

from uuid import UUID

from fastapi.testclient import TestClient


def test_get_transactions_returns_initial_deposit(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that transaction history includes the initial deposit."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Transaction Test",
            "initial_deposit": "25000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Get transactions
    tx_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers={"X-User-Id": str(default_user_id)},
    )

    assert tx_response.status_code == 200
    tx_data = tx_response.json()
    transactions = tx_data["transactions"]

    # Should have 1 transaction: DEPOSIT
    assert len(transactions) == 1
    assert transactions[0]["transaction_type"] == "DEPOSIT"
    assert transactions[0]["cash_change"] == "25000.00"


def test_get_transactions_returns_all_trades(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test transaction history includes all deposits and trades."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Transaction Test",
            "initial_deposit": "25000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute trades
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "50", "price": "150.00"},
    )
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "GOOGL", "quantity": "10", "price": "140.00"},
    )

    # Get transactions
    tx_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers={"X-User-Id": str(default_user_id)},
    )

    assert tx_response.status_code == 200
    tx_data = tx_response.json()
    transactions = tx_data["transactions"]

    # Should have 3 transactions: 1 DEPOSIT + 2 BUY
    assert len(transactions) == 3

    # Verify types
    types = [tx["transaction_type"] for tx in transactions]
    assert "DEPOSIT" in types
    assert types.count("BUY") == 2


def test_transactions_include_trade_details(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that trade transactions include ticker, quantity, and price."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Detail Test",
            "initial_deposit": "50000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Execute a trade
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "25", "price": "180.00"},
    )

    # Get transactions
    tx_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers={"X-User-Id": str(default_user_id)},
    )

    transactions = tx_response.json()["transactions"]

    # Find the BUY transaction
    buy_tx = next(tx for tx in transactions if tx["transaction_type"] == "BUY")

    # Verify details
    assert buy_tx["ticker"] == "AAPL"
    assert buy_tx["quantity"] == "25.0000"
    assert buy_tx["price_per_share"] == "180.00"
    # Cash change should be negative (spent money)
    assert buy_tx["cash_change"].startswith("-")


def test_deposit_and_withdrawal_in_transaction_history(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that deposits and withdrawals appear in transaction history."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Cash Flow Test",
            "initial_deposit": "10000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Additional deposit
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/deposit",
        headers={"X-User-Id": str(default_user_id)},
        json={"amount": "5000.00", "currency": "USD"},
    )

    # Withdrawal
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/withdraw",
        headers={"X-User-Id": str(default_user_id)},
        json={"amount": "2000.00", "currency": "USD"},
    )

    # Get transactions
    tx_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers={"X-User-Id": str(default_user_id)},
    )

    transactions = tx_response.json()["transactions"]

    # Should have 3 transactions: initial DEPOSIT + deposit + withdrawal
    assert len(transactions) == 3

    types = [tx["transaction_type"] for tx in transactions]
    assert types.count("DEPOSIT") == 2
    assert types.count("WITHDRAWAL") == 1


def test_sell_transaction_appears_in_history(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that sell transactions appear correctly in history."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Sell Test",
            "initial_deposit": "50000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Buy shares
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "BUY", "ticker": "AAPL", "quantity": "100", "price": "150.00"},
    )

    # Sell shares
    client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers={"X-User-Id": str(default_user_id)},
        json={"action": "SELL", "ticker": "AAPL", "quantity": "30", "price": "160.00"},
    )

    # Get transactions
    tx_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers={"X-User-Id": str(default_user_id)},
    )

    transactions = tx_response.json()["transactions"]

    # Find the SELL transaction
    sell_tx = next(tx for tx in transactions if tx["transaction_type"] == "SELL")

    # Verify details
    assert sell_tx["ticker"] == "AAPL"
    assert sell_tx["quantity"] == "30.0000"
    assert sell_tx["price_per_share"] == "160.00"
    # Cash change should be positive (received money)
    assert not sell_tx["cash_change"].startswith("-")


def test_transaction_pagination(
    client: TestClient,
    default_user_id: UUID,
) -> None:
    """Test that transaction list supports pagination."""
    # Create portfolio
    response = client.post(
        "/api/v1/portfolios",
        headers={"X-User-Id": str(default_user_id)},
        json={
            "name": "Pagination Test",
            "initial_deposit": "100000.00",
            "currency": "USD",
        },
    )
    portfolio_id = response.json()["portfolio_id"]

    # Create multiple transactions (10 trades)
    for i in range(10):
        client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            headers={"X-User-Id": str(default_user_id)},
            json={
                "action": "BUY",
                "ticker": "AAPL",
                "quantity": "1",
                "price": "150.00",
            },
        )

    # Get first page (limit=5)
    page1_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions?limit=5&offset=0",
        headers={"X-User-Id": str(default_user_id)},
    )
    page1_data = page1_response.json()
    assert len(page1_data["transactions"]) == 5
    assert page1_data["total_count"] == 11  # 10 trades + 1 initial deposit
    assert page1_data["limit"] == 5
    assert page1_data["offset"] == 0

    # Get second page
    page2_response = client.get(
        f"/api/v1/portfolios/{portfolio_id}/transactions?limit=5&offset=5",
        headers={"X-User-Id": str(default_user_id)},
    )
    page2_data = page2_response.json()
    assert len(page2_data["transactions"]) == 5
    assert page2_data["offset"] == 5
