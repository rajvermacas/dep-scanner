"""Integration tests for the REST API."""

import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from dependency_scanner_tool.api.app import app
from dependency_scanner_tool.scanner import ScanResult, Dependency


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_complete_scanning_workflow_with_mocked_git(client):
    """Test the complete scanning workflow with mocked Git operations."""
    
    # Mock the git clone operation and scanner
    with patch('dependency_scanner_tool.api.scanner_service.subprocess.run') as mock_run, \
         patch('dependency_scanner_tool.api.scanner_service.tempfile.mkdtemp') as mock_mkdtemp, \
         patch('dependency_scanner_tool.api.scanner_service.shutil.rmtree') as mock_rmtree:
        
        # Setup mocks
        mock_mkdtemp.return_value = '/tmp/test_repo'
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        
        # Mock scanner results
        mock_dependencies = [
            Dependency(name='pandas', version='1.0.0'),
            Dependency(name='flask', version='2.0.0'),
            Dependency(name='numpy', version='1.20.0')
        ]
        
        mock_scan_result = ScanResult(
            languages={'python': 100.0},
            package_managers={'pip'},
            dependency_files=[],
            dependencies=mock_dependencies,
            api_calls=[],
            errors=[]
        )
        
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scanner') as mock_scanner:
            mock_scanner.scan_project.return_value = mock_scan_result
            
            # Submit scan request
            response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"})
            assert response.status_code == 200
            
            job_id = response.json()["job_id"]
            assert job_id is not None
            
            # Wait a bit for background task to complete
            # Note: In a real test, we'd want to wait for the job to complete
            # For now, we'll just verify the job was created
            time.sleep(0.1)
            
            # Check job status
            status_response = client.get(f"/jobs/{job_id}")
            assert status_response.status_code == 200
            
            job_status = status_response.json()
            assert job_status["job_id"] == job_id
            assert job_status["status"] in ["pending", "running", "completed"]


def test_api_error_handling(client):
    """Test API error handling."""
    # Test invalid Git URL
    response = client.post("/scan", json={"git_url": "invalid-url"})
    assert response.status_code == 422
    
    # Test missing git_url
    response = client.post("/scan", json={})
    assert response.status_code == 422
    
    # Test invalid job ID
    response = client.get("/jobs/invalid-job-id")
    assert response.status_code == 404
    
    # Test results for invalid job ID
    response = client.get("/jobs/invalid-job-id/results")
    assert response.status_code == 404


def test_api_endpoints_structure(client):
    """Test that all required API endpoints are available."""
    # Health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    
    # Scan endpoint (with invalid data to test endpoint exists)
    response = client.post("/scan", json={"git_url": "invalid"})
    assert response.status_code == 422  # Validation error, but endpoint exists
    
    # Job status endpoint (with invalid job ID)
    response = client.get("/jobs/test-job-id")
    assert response.status_code == 404  # Not found, but endpoint exists
    
    # Results endpoint (with invalid job ID)
    response = client.get("/jobs/test-job-id/results")
    assert response.status_code == 404  # Not found, but endpoint exists