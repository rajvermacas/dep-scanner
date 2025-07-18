"""Tests for the scan endpoint."""

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
    credentials = base64.b64encode(b"test_user_secure:test_password_secure_123!").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


def test_scan_endpoint_returns_job_id(client, auth_headers):
    """Test that the scan endpoint returns a job ID."""
    response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"}, headers=auth_headers)
    assert response.status_code == 200
    
    json_response = response.json()
    assert "job_id" in json_response
    assert "status" in json_response
    assert "created_at" in json_response
    assert json_response["status"] == "pending"


def test_scan_endpoint_validates_git_url(client, auth_headers):
    """Test that the scan endpoint validates Git URL format."""
    response = client.post("/scan", json={"git_url": "invalid-url"}, headers=auth_headers)
    assert response.status_code == 422  # Pydantic validation error for invalid URL format


def test_scan_endpoint_requires_git_url(client, auth_headers):
    """Test that the scan endpoint requires git_url field."""
    response = client.post("/scan", json={}, headers=auth_headers)
    assert response.status_code == 422  # Validation error


def test_scan_endpoint_returns_json_content_type(client, auth_headers):
    """Test that the scan endpoint returns JSON content type."""
    response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"}, headers=auth_headers)
    assert response.headers["content-type"] == "application/json"