"""Integration tests for prices API endpoints.

These tests verify that the price endpoints work correctly end-to-end,
including proper error handling and response formatting.
"""

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


def test_check_historical_data_available(
    client: TestClient,
) -> None:
    """Test checking historical data availability when data exists."""
    # AAPL has seeded data in conftest (timestamp = now)
    # Check for data close to now - use a formatted datetime string
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    # Format as ISO 8601 with Z suffix (FastAPI expects this format)
    date_str = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    response = client.get(f"/api/v1/prices/AAPL/check?date={date_str}")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "available" in data
    assert "closest_date" in data

    # Should find data (seeded in conftest with current timestamp)
    assert data["available"] is True
    assert data["closest_date"] is not None


def test_check_historical_data_not_available(
    client: TestClient,
) -> None:
    """Test checking historical data availability when no data exists."""
    # Use a date far in the past where we have no data
    # InMemoryAdapter only has ±1 hour window
    response = client.get("/api/v1/prices/AAPL/check?date=2020-01-01T00:00:00Z")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "available" in data
    assert "closest_date" in data

    # Should not find data (outside ±1 hour window)
    assert data["available"] is False
    assert data["closest_date"] is None


def test_check_historical_data_invalid_ticker(
    client: TestClient,
) -> None:
    """Test checking historical data with unknown ticker returns not available."""
    # Use a valid ticker format but unknown ticker (max 5 chars)
    response = client.get("/api/v1/prices/XXXXX/check?date=2024-01-01T00:00:00Z")

    assert response.status_code == 200
    data = response.json()

    # Should return available=False for unknown ticker
    assert "available" in data
    assert data["available"] is False


def test_fetch_historical_data(
    client: TestClient,
) -> None:
    """Test fetching historical data endpoint."""
    # This will use the InMemoryAdapter in tests, which doesn't actually fetch
    # from Alpha Vantage, but we can verify the endpoint structure
    response = client.post(
        "/api/v1/prices/fetch-historical",
        json={
            "ticker": "AAPL",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "ticker" in data
    assert "fetched" in data
    assert "start" in data
    assert "end" in data

    assert data["ticker"] == "AAPL"
    assert isinstance(data["fetched"], int)
    assert data["fetched"] >= 0


def test_fetch_historical_data_invalid_date_range(
    client: TestClient,
) -> None:
    """Test fetching historical data with invalid date range."""
    response = client.post(
        "/api/v1/prices/fetch-historical",
        json={
            "ticker": "AAPL",
            "start": "2024-12-31T00:00:00Z",
            "end": "2024-01-01T00:00:00Z",
        },
    )

    # Should reject end before start
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_get_batch_prices_all_available(
    client: TestClient,
) -> None:
    """Test batch prices endpoint returns all requested tickers when available."""
    response = client.get("/api/v1/prices/batch?tickers=AAPL,GOOGL,MSFT")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "prices" in data
    assert "requested" in data
    assert "returned" in data

    # All three tickers should be available
    assert data["requested"] == 3
    assert data["returned"] == 3
    assert "AAPL" in data["prices"]
    assert "GOOGL" in data["prices"]
    assert "MSFT" in data["prices"]

    # Verify price values (from conftest seeded data)
    assert data["prices"]["AAPL"]["price"] == "150.00"
    assert data["prices"]["GOOGL"]["price"] == "2800.00"
    assert data["prices"]["MSFT"]["price"] == "380.00"


def test_get_batch_prices_partial_results(
    client: TestClient,
) -> None:
    """Test batch prices endpoint returns only available tickers."""
    # Request AAPL (available) and XXXXX (not available)
    response = client.get("/api/v1/prices/batch?tickers=AAPL,XXXXX")

    assert response.status_code == 200
    data = response.json()

    # Should return only AAPL
    assert data["requested"] == 2
    assert data["returned"] == 1
    assert "AAPL" in data["prices"]
    assert "XXXXX" not in data["prices"]


def test_get_batch_prices_empty_tickers(
    client: TestClient,
) -> None:
    """Test batch prices endpoint returns 400 for empty ticker list."""
    response = client.get("/api/v1/prices/batch?tickers=")

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "At least one ticker symbol is required" in data["detail"]


def test_get_batch_prices_single_ticker(
    client: TestClient,
) -> None:
    """Test batch prices endpoint works with single ticker."""
    response = client.get("/api/v1/prices/batch?tickers=AAPL")

    assert response.status_code == 200
    data = response.json()

    assert data["requested"] == 1
    assert data["returned"] == 1
    assert "AAPL" in data["prices"]
    assert data["prices"]["AAPL"]["price"] == "150.00"


def test_get_batch_prices_whitespace_handling(
    client: TestClient,
) -> None:
    """Test batch prices endpoint handles whitespace in ticker list."""
    # Add extra spaces around tickers
    response = client.get("/api/v1/prices/batch?tickers= AAPL , GOOGL , MSFT ")

    assert response.status_code == 200
    data = response.json()

    # Should still parse correctly
    assert data["requested"] == 3
    assert data["returned"] == 3


def test_get_batch_prices_case_insensitive(
    client: TestClient,
) -> None:
    """Test batch prices endpoint handles lowercase tickers."""
    response = client.get("/api/v1/prices/batch?tickers=aapl,googl")

    assert response.status_code == 200
    data = response.json()

    # Should normalize to uppercase
    assert data["requested"] == 2
    assert data["returned"] == 2
    assert "AAPL" in data["prices"]
    assert "GOOGL" in data["prices"]


def test_get_batch_prices_includes_metadata(
    client: TestClient,
) -> None:
    """Test batch prices endpoint includes all required metadata."""
    response = client.get("/api/v1/prices/batch?tickers=AAPL")

    assert response.status_code == 200
    data = response.json()

    aapl_price = data["prices"]["AAPL"]

    # Check all expected fields
    assert "ticker" in aapl_price
    assert "price" in aapl_price
    assert "currency" in aapl_price
    assert "timestamp" in aapl_price
    assert "source" in aapl_price
    assert "is_stale" in aapl_price

    # Verify values
    assert aapl_price["ticker"] == "AAPL"
    assert aapl_price["currency"] == "USD"
    assert aapl_price["source"] == "database"
