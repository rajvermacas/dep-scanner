"""Tests for the scan endpoint."""

import pytest
from fastapi.testclient import TestClient
from dependency_scanner_tool.api.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_scan_endpoint_returns_job_id(client):
    """Test that the scan endpoint returns a job ID."""
    response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"})
    assert response.status_code == 200
    
    json_response = response.json()
    assert "job_id" in json_response
    assert "status" in json_response
    assert "created_at" in json_response
    assert json_response["status"] == "pending"


def test_scan_endpoint_validates_git_url(client):
    """Test that the scan endpoint validates Git URL format."""
    response = client.post("/scan", json={"git_url": "invalid-url"})
    assert response.status_code == 422  # Validation error


def test_scan_endpoint_requires_git_url(client):
    """Test that the scan endpoint requires git_url field."""
    response = client.post("/scan", json={})
    assert response.status_code == 422  # Validation error


def test_scan_endpoint_returns_json_content_type(client):
    """Test that the scan endpoint returns JSON content type."""
    response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"})
    assert response.headers["content-type"] == "application/json"