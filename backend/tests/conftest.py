"""Pytest configuration and shared fixtures."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from papertrade.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def default_user_id() -> UUID:
    """Default user ID for integration tests."""
    return uuid4()
