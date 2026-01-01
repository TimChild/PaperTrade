"""Integration tests for prices API endpoints.

These tests verify that the price endpoints work correctly end-to-end,
including proper error handling and response formatting.
"""

from uuid import UUID

from fastapi.testclient import TestClient


def test_get_current_price_aapl(
    client: TestClient,
) -> None:
    """Test fetching current price for AAPL."""
    response = client.get("/api/v1/prices/AAPL")

    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "ticker" in data
    assert "price" in data
    assert "currency" in data
    assert "timestamp" in data
    assert "source" in data
    assert "is_stale" in data
    
    # Verify values (seeded in conftest)
    assert data["ticker"] == "AAPL"
    assert data["price"] == "150.00"
    assert data["currency"] == "USD"


def test_get_current_price_invalid_ticker(
    client: TestClient,
) -> None:
    """Test fetching price for non-existent ticker returns 404."""
    # Use a valid ticker format that doesn't exist in our test data
    response = client.get("/api/v1/prices/XXXX")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_get_supported_tickers(
    client: TestClient,
) -> None:
    """Test getting list of supported tickers."""
    response = client.get("/api/v1/prices/")

    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "tickers" in data
    assert "count" in data
    
    # Should include seeded tickers
    assert isinstance(data["tickers"], list)
    assert "AAPL" in data["tickers"]
    assert "GOOGL" in data["tickers"]
    assert "MSFT" in data["tickers"]
    assert data["count"] == len(data["tickers"])


def test_get_price_history_missing_parameters(
    client: TestClient,
) -> None:
    """Test price history endpoint requires start and end parameters."""
    # Missing both start and end
    response = client.get("/api/v1/prices/AAPL/history")
    assert response.status_code == 422  # Validation error

    # Missing end parameter
    response = client.get("/api/v1/prices/AAPL/history?start=2024-01-01T00:00:00Z")
    assert response.status_code == 422


def test_get_price_history_valid_request(
    client: TestClient,
) -> None:
    """Test price history endpoint with valid parameters."""
    response = client.get(
        "/api/v1/prices/AAPL/history"
        "?start=2024-01-01T00:00:00Z"
        "&end=2024-12-31T23:59:59Z"
        "&interval=1day"
    )

    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "ticker" in data
    assert "prices" in data
    assert "start" in data
    assert "end" in data
    assert "interval" in data
    assert "count" in data
    
    # Verify values
    assert data["ticker"] == "AAPL"
    assert data["interval"] == "1day"
    assert isinstance(data["prices"], list)
    assert data["count"] == len(data["prices"])


def test_get_price_history_valid_interval_accepted(
    client: TestClient,
) -> None:
    """Test price history endpoint accepts valid intervals.
    
    Note: InMemoryAdapter doesn't validate intervals, so this just
    ensures the API doesn't reject valid interval values.
    """
    response = client.get(
        "/api/v1/prices/AAPL/history"
        "?start=2024-01-01T00:00:00Z"
        "&end=2024-12-31T23:59:59Z"
        "&interval=1day"
    )

    # Should succeed (may return empty list if no data)
    assert response.status_code == 200


def test_get_price_history_invalid_date_range(
    client: TestClient,
) -> None:
    """Test price history endpoint rejects end before start."""
    # End date before start date
    response = client.get(
        "/api/v1/prices/AAPL/history"
        "?start=2024-12-31T00:00:00Z"
        "&end=2024-01-01T00:00:00Z"
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
