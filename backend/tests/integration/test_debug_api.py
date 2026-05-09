"""Integration tests for the debug endpoint.

The whole `/api/v1/debug/*` router is gated behind the admin allowlist
(see Wave 1-A security fixes — audits/2026-05-09/security.md P1-1).
Unauthenticated requests get 401, authenticated non-admins get 403.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_auth_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[dict[str, str]]:
    """Provide admin Bearer headers, registering the test user as admin."""
    monkeypatch.setenv("ADMIN_USER_IDS", "test-user-default")
    yield {"Authorization": "Bearer test-token-default"}


def test_debug_endpoint_returns_200_for_admin(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that the debug endpoint returns 200 for an admin caller."""
    response = client.get("/api/v1/debug", headers=admin_auth_headers)
    assert response.status_code == 200


def test_debug_endpoint_structure(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that the debug endpoint returns expected structure."""
    response = client.get("/api/v1/debug", headers=admin_auth_headers)
    data = response.json()

    # Check top-level keys
    assert "environment" in data
    assert "database" in data
    assert "redis" in data
    assert "api_keys" in data
    assert "services" in data


def test_debug_environment_info(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that environment info is returned correctly."""
    response = client.get("/api/v1/debug", headers=admin_auth_headers)
    data = response.json()

    env = data["environment"]
    assert "environment" in env
    assert "python_version" in env
    assert "fastapi_version" in env


def test_debug_database_info(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that database info is returned correctly."""
    response = client.get("/api/v1/debug", headers=admin_auth_headers)
    data = response.json()

    db = data["database"]
    assert "connected" in db
    assert "url" in db
    assert db["connected"] is True


def test_debug_api_keys_redacted(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that API keys are properly redacted."""
    # Set a test API key
    os.environ["CLERK_SECRET_KEY"] = "sk_test_1234567890abcdef"
    os.environ["ALPHA_VANTAGE_API_KEY"] = "DEMO1234567890"

    response = client.get("/api/v1/debug", headers=admin_auth_headers)
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


def test_debug_no_secrets_leaked(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that no full secrets are leaked in the response."""
    # Set test secrets
    test_secrets = {
        "CLERK_SECRET_KEY": "sk_test_super_secret_key_12345",
        "ALPHA_VANTAGE_API_KEY": "SECRET_API_KEY_67890",
        "DATABASE_URL": "postgresql://user:secret_password@localhost/db",
    }

    for key, value in test_secrets.items():
        os.environ[key] = value

    response = client.get("/api/v1/debug", headers=admin_auth_headers)
    response_text = str(response.json())

    # Ensure no full secret appears in response
    assert "super_secret_key_12345" not in response_text
    assert "SECRET_API_KEY_67890" not in response_text
    assert "secret_password" not in response_text

    # Cleanup
    for key in test_secrets:
        os.environ.pop(key, None)


def test_debug_missing_api_keys(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test debug endpoint when API keys are not configured."""
    # Clear any existing keys
    os.environ.pop("CLERK_SECRET_KEY", None)
    os.environ.pop("ALPHA_VANTAGE_API_KEY", None)

    response = client.get("/api/v1/debug", headers=admin_auth_headers)
    data = response.json()

    api_keys = data["api_keys"]

    # Keys should show as not present
    clerk = api_keys.get("clerk_secret_key", {})
    assert clerk.get("present") is False

    av = api_keys.get("alpha_vantage_api_key", {})
    assert av.get("present") is False


# =========================================================================
# Auth gate behaviour (Wave 1-A security fixes — sec.P1-1, api.P0-3)
# =========================================================================


def test_debug_router_requires_auth(
    client: TestClient,
) -> None:
    """All /api/v1/debug/* routes reject unauthenticated requests with 401."""
    assert client.get("/api/v1/debug").status_code == 401
    assert client.get("/api/v1/debug/scheduler").status_code == 401
    assert client.get("/api/v1/debug/price-cache/AAPL").status_code == 401


def test_debug_router_rejects_non_admin_with_403(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticated non-admin callers receive 403 from every debug route."""
    # Empty allowlist — default test user is not in it.
    monkeypatch.setenv("ADMIN_USER_IDS", "")

    assert client.get("/api/v1/debug", headers=auth_headers).status_code == 403
    assert (
        client.get("/api/v1/debug/scheduler", headers=auth_headers).status_code == 403
    )
    assert (
        client.get("/api/v1/debug/price-cache/AAPL", headers=auth_headers).status_code
        == 403
    )


def test_debug_scheduler_admin_can_access(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Admin callers can read scheduler status."""
    response = client.get("/api/v1/debug/scheduler", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "running" in data
    assert "jobs" in data
    assert "job_count" in data


def test_debug_price_cache_admin_can_access(
    client: TestClient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Admin callers can read the price-cache debug status."""
    response = client.get(
        "/api/v1/debug/price-cache/AAPL",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "ticker" in data
