"""Tests for the health check endpoint."""

import pytest
import base64
from fastapi.testclient import TestClient
from dependency_scanner_tool.api.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create valid authentication headers."""
    credentials = base64.b64encode(b"admin:secret123").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


def test_health_endpoint_returns_200(client, auth_headers):
    """Test that the health endpoint returns HTTP 200."""
    response = client.get("/health", headers=auth_headers)
    assert response.status_code == 200


def test_health_endpoint_returns_expected_format(client, auth_headers):
    """Test that the health endpoint returns the expected JSON format."""
    response = client.get("/health", headers=auth_headers)
    json_response = response.json()
    
    # Check required fields
    assert "status" in json_response
    assert "timestamp" in json_response
    assert "version" in json_response
    assert "user" in json_response
    
    # Check values
    assert json_response["status"] == "healthy"
    assert json_response["version"] == "1.0.0"
    assert json_response["user"] == "admin"


def test_health_endpoint_responds_quickly(client, auth_headers):
    """Test that the health endpoint responds within 1 second."""
    import time
    
    start_time = time.time()
    response = client.get("/health", headers=auth_headers)
    end_time = time.time()
    
    assert response.status_code == 200
    assert (end_time - start_time) < 1.0  # Should respond within 1 second


def test_health_endpoint_requires_authentication(client):
    """Test that the health endpoint requires authentication."""
    response = client.get("/health")
    assert response.status_code == 401