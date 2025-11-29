"""
Tests for main FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint returns correct status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "grimoire-engine-backend"


def test_docs_available(client):
    """Test that OpenAPI documentation is available at /docs."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema(client):
    """Test that OpenAPI schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Grimoire Engine API"
    assert schema["info"]["version"] == "0.1.0"
    assert "/health" in schema["paths"]
