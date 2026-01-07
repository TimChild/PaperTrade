"""Integration tests for the debug endpoint."""

import os

from fastapi.testclient import TestClient


def test_debug_endpoint_returns_200(client: TestClient) -> None:
    """Test that the debug endpoint returns a 200 status."""
    response = client.get("/api/v1/debug")
    assert response.status_code == 200


def test_debug_endpoint_structure(client: TestClient) -> None:
    """Test that the debug endpoint returns expected structure."""
    response = client.get("/api/v1/debug")
    data = response.json()

    # Check top-level keys
    assert "environment" in data
    assert "database" in data
    assert "redis" in data
    assert "api_keys" in data
    assert "services" in data


def test_debug_environment_info(client: TestClient) -> None:
    """Test that environment info is returned correctly."""
    response = client.get("/api/v1/debug")
    data = response.json()

    env = data["environment"]
    assert "environment" in env
    assert "python_version" in env
    assert "fastapi_version" in env


def test_debug_database_info(client: TestClient) -> None:
    """Test that database info is returned correctly."""
    response = client.get("/api/v1/debug")
    data = response.json()

    db = data["database"]
    assert "connected" in db
    assert "url" in db
    assert db["connected"] is True


def test_debug_api_keys_redacted(client: TestClient) -> None:
    """Test that API keys are properly redacted."""
    # Set a test API key
    os.environ["CLERK_SECRET_KEY"] = "sk_test_1234567890abcdef"
    os.environ["ALPHA_VANTAGE_API_KEY"] = "DEMO1234567890"

    response = client.get("/api/v1/debug")
    data = response.json()

    api_keys = data["api_keys"]

    # Check Clerk key is redacted
    clerk = api_keys.get("clerk_secret_key", {})
    if clerk.get("present"):
        assert "prefix" in clerk
        assert "length" in clerk
        # Ensure full key is NOT in response
        assert "sk_test_1234567890abcdef" not in str(data)

    # Check Alpha Vantage key is redacted
    av = api_keys.get("alpha_vantage_api_key", {})
    if av.get("present"):
        assert "prefix" in av
        assert "length" in av
        # Ensure full key is NOT in response
        assert "DEMO1234567890" not in str(data)


def test_debug_no_secrets_leaked(client: TestClient) -> None:
    """Test that no full secrets are leaked in the response."""
    # Set test secrets
    test_secrets = {
        "CLERK_SECRET_KEY": "sk_test_super_secret_key_12345",
        "ALPHA_VANTAGE_API_KEY": "SECRET_API_KEY_67890",
        "DATABASE_URL": "postgresql://user:secret_password@localhost/db",
    }

    for key, value in test_secrets.items():
        os.environ[key] = value

    response = client.get("/api/v1/debug")
    response_text = str(response.json())

    # Ensure no full secret appears in response
    assert "super_secret_key_12345" not in response_text
    assert "SECRET_API_KEY_67890" not in response_text
    assert "secret_password" not in response_text

    # Cleanup
    for key in test_secrets:
        os.environ.pop(key, None)


def test_debug_missing_api_keys(client: TestClient) -> None:
    """Test debug endpoint when API keys are not configured."""
    # Clear any existing keys
    os.environ.pop("CLERK_SECRET_KEY", None)
    os.environ.pop("ALPHA_VANTAGE_API_KEY", None)

    response = client.get("/api/v1/debug")
    data = response.json()

    api_keys = data["api_keys"]

    # Keys should show as not present
    clerk = api_keys.get("clerk_secret_key", {})
    assert clerk.get("present") is False

    av = api_keys.get("alpha_vantage_api_key", {})
    assert av.get("present") is False
