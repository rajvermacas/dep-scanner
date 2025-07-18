"""Tests for the job status endpoint."""

import pytest
import base64
from unittest.mock import patch
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


def test_job_status_endpoint_returns_job_info(client, auth_headers):
    """Test that the job status endpoint returns job information."""
    # Mock the scanner service to prevent actual Git operations
    with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
        # First create a job
        scan_response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"}, headers=auth_headers)
        job_id = scan_response.json()["job_id"]
        
        # Then check job status
        response = client.get(f"/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        json_response = response.json()
        assert json_response["job_id"] == job_id
        assert "status" in json_response
        assert "created_at" in json_response
        assert "progress" in json_response
        assert json_response["status"] == "pending"
        assert json_response["progress"] == 0


def test_job_status_endpoint_returns_404_for_invalid_job(client, auth_headers):
    """Test that the job status endpoint returns 404 for invalid job ID."""
    response = client.get("/jobs/invalid-job-id", headers=auth_headers)
    assert response.status_code == 404


def test_job_status_endpoint_returns_json_content_type(client, auth_headers):
    """Test that the job status endpoint returns JSON content type."""
    # Mock the scanner service to prevent actual Git operations
    with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
        # First create a job
        scan_response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"}, headers=auth_headers)
        job_id = scan_response.json()["job_id"]
        
        # Then check job status
        response = client.get(f"/jobs/{job_id}", headers=auth_headers)
        assert response.headers["content-type"] == "application/json"