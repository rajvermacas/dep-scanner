"""Tests for the results endpoint."""

import pytest
from fastapi.testclient import TestClient
from dependency_scanner_tool.api.app import app
from dependency_scanner_tool.api.job_manager import job_manager
from dependency_scanner_tool.api.models import ScanResultResponse, JobStatus


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_results_endpoint_returns_results_for_completed_job(client):
    """Test that the results endpoint returns results for completed jobs."""
    # First create a job
    scan_response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"})
    job_id = scan_response.json()["job_id"]
    
    # Mock completion with results
    test_result = ScanResultResponse(
        git_url="https://github.com/test/repo.git",
        dependencies={"Data Science": False, "Web Frameworks": True}
    )
    job_manager.set_job_result(job_id, test_result)
    
    # Get results
    response = client.get(f"/jobs/{job_id}/results")
    assert response.status_code == 200
    
    json_response = response.json()
    assert json_response["git_url"] == "https://github.com/test/repo.git"
    assert "dependencies" in json_response
    assert json_response["dependencies"]["Data Science"] is False
    assert json_response["dependencies"]["Web Frameworks"] is True


def test_results_endpoint_returns_404_for_invalid_job(client):
    """Test that the results endpoint returns 404 for invalid job ID."""
    response = client.get("/jobs/invalid-job-id/results")
    assert response.status_code == 404


def test_results_endpoint_returns_400_for_pending_job(client):
    """Test that the results endpoint returns 400 for pending jobs."""
    # First create a job
    scan_response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"})
    job_id = scan_response.json()["job_id"]
    
    # Try to get results while still pending
    response = client.get(f"/jobs/{job_id}/results")
    assert response.status_code == 400


def test_results_endpoint_returns_json_content_type(client):
    """Test that the results endpoint returns JSON content type."""
    # First create a job
    scan_response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"})
    job_id = scan_response.json()["job_id"]
    
    # Mock completion with results
    test_result = ScanResultResponse(
        git_url="https://github.com/test/repo.git",
        dependencies={"Data Science": False, "Web Frameworks": True}
    )
    job_manager.set_job_result(job_id, test_result)
    
    # Get results
    response = client.get(f"/jobs/{job_id}/results")
    assert response.headers["content-type"] == "application/json"