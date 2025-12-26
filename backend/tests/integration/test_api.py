"""Integration tests for the API endpoints."""

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
