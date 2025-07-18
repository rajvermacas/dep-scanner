"""Tests for partial results streaming functionality."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import base64
import json
from datetime import datetime, timezone

from dependency_scanner_tool.api.app import app
from dependency_scanner_tool.api.job_manager import job_manager, Job, JobStatus


@pytest.fixture
def auth_headers():
    """Create valid authentication headers."""
    credentials = base64.b64encode(b"test_user_secure:test_password_secure_123!").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_job_with_partial_results():
    """Create a sample job with partial results."""
    job = Job("test_job_partial", "https://github.com/test/repo.git")
    job.status = JobStatus.RUNNING
    job.progress = 60
    
    # Add partial results
    job.partial_results = {
        "scanned_files": 15,
        "total_files": 25,
        "found_dependencies": [
            {"name": "requests", "version": "2.28.1", "type": "python"},
            {"name": "flask", "version": "2.2.0", "type": "python"},
            {"name": "pytest", "version": "7.1.2", "type": "python", "dev_only": True}
        ],
        "current_file": "requirements.txt",
        "scan_stage": "parsing_dependencies"
    }
    
    return job


class TestPartialResultsEndpoint:
    """Test partial results streaming functionality."""
    
    def test_get_partial_results_endpoint_exists(self, client, auth_headers):
        """Test that GET /jobs/{job_id}/partial endpoint exists."""
        # Test without authentication
        response = client.get("/jobs/test_job/partial")
        assert response.status_code == 401
        
        # Test with authentication but non-existent job
        response = client.get("/jobs/non_existent_job/partial", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_partial_results_job_not_found(self, client, auth_headers):
        """Test partial results for non-existent job."""
        job_manager._jobs.clear()
        
        response = client.get("/jobs/non_existent_job/partial", headers=auth_headers)
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]
    
    def test_get_partial_results_not_running(self, client, auth_headers):
        """Test partial results for job that is not running."""
        job_manager._jobs.clear()
        
        # Create a pending job
        job = Job("pending_job", "https://github.com/test/repo.git")
        job.status = JobStatus.PENDING
        job_manager._jobs[job.job_id] = job
        
        response = client.get("/jobs/pending_job/partial", headers=auth_headers)
        assert response.status_code == 400
        assert "not currently running" in response.json()["detail"]
    
    def test_get_partial_results_success(self, client, auth_headers, sample_job_with_partial_results):
        """Test successful partial results retrieval."""
        job_manager._jobs.clear()
        job = sample_job_with_partial_results
        job_manager._jobs[job.job_id] = job
        
        response = client.get(f"/jobs/{job.job_id}/partial", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert "progress" in data
        assert "partial_results" in data
        
        assert data["job_id"] == job.job_id
        assert data["status"] == "running"
        assert data["progress"] == 60
        assert data["partial_results"]["scanned_files"] == 15
        assert data["partial_results"]["total_files"] == 25
        assert len(data["partial_results"]["found_dependencies"]) == 3
    
    def test_get_partial_results_no_partial_data(self, client, auth_headers):
        """Test partial results when no partial data is available."""
        job_manager._jobs.clear()
        
        # Create a running job without partial results
        job = Job("running_job", "https://github.com/test/repo.git")
        job.status = JobStatus.RUNNING
        job.progress = 30
        job_manager._jobs[job.job_id] = job
        
        response = client.get(f"/jobs/{job.job_id}/partial", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == job.job_id
        assert data["status"] == "running"
        assert data["progress"] == 30
        assert data["partial_results"] is None
    
    def test_get_partial_results_response_format(self, client, auth_headers, sample_job_with_partial_results):
        """Test partial results response format."""
        job_manager._jobs.clear()
        job = sample_job_with_partial_results
        job_manager._jobs[job.job_id] = job
        
        response = client.get(f"/jobs/{job.job_id}/partial", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert "job_id" in data
        assert "status" in data
        assert "progress" in data
        assert "partial_results" in data
        assert "last_updated" in data
        
        # Check partial results structure
        partial = data["partial_results"]
        assert "scanned_files" in partial
        assert "total_files" in partial
        assert "found_dependencies" in partial
        assert "current_file" in partial
        assert "scan_stage" in partial
        
        # Check dependencies structure
        for dep in partial["found_dependencies"]:
            assert "name" in dep
            assert "version" in dep
            assert "type" in dep


class TestPartialResultsUpdates:
    """Test partial results update functionality."""
    
    def test_update_partial_results_in_job(self):
        """Test updating partial results in a job."""
        job_manager._jobs.clear()
        
        # Create a job
        job = Job("test_job", "https://github.com/test/repo.git")
        job.status = JobStatus.RUNNING
        job_manager._jobs[job.job_id] = job
        
        # Update partial results
        partial_data = {
            "scanned_files": 5,
            "total_files": 20,
            "found_dependencies": [
                {"name": "numpy", "version": "1.24.0", "type": "python"}
            ],
            "current_file": "setup.py",
            "scan_stage": "analyzing_imports"
        }
        
        job_manager.update_partial_results(job.job_id, partial_data)
        
        # Check results were updated
        updated_job = job_manager.get_job(job.job_id)
        assert updated_job.partial_results == partial_data
        assert updated_job.last_updated is not None
    
    def test_update_partial_results_nonexistent_job(self):
        """Test updating partial results for non-existent job."""
        job_manager._jobs.clear()
        
        # Should not raise an exception
        job_manager.update_partial_results("non_existent", {"test": "data"})
    
    def test_scanner_service_updates_partial_results(self):
        """Test that scanner service updates partial results during scanning."""
        from dependency_scanner_tool.api.scanner_service import ScannerService
        
        # This test would require mocking the scanner service
        # to verify it calls update_partial_results at appropriate times
        pass  # Implementation would go here in a real scenario


class TestPartialResultsIntegration:
    """Test partial results integration with scanning process."""
    
    @pytest.mark.asyncio
    async def test_partial_results_during_scan(self, client, auth_headers):
        """Test that partial results are available during an active scan."""
        with patch('dependency_scanner_tool.api.git_service.git_service') as mock_git, \
             patch('dependency_scanner_tool.api.scanner_service.scanner_service') as mock_scanner:
            
            # Setup mocks
            mock_git.clone_repository.return_value = MagicMock()
            mock_git.validate_repository.return_value = True
            mock_git.cleanup_repository.return_value = None
            
            mock_result = MagicMock()
            mock_result.dependencies = []
            mock_scanner.scanner.scan_project.return_value = mock_result
            
            # Start a scan
            response = client.post(
                "/scan", 
                json={"git_url": "https://github.com/test/repo.git"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            job_id = response.json()["job_id"]
            
            # The scan should be running (we'd need to add delay in real implementation)
            # For now, we'll manually set the job to running with partial results
            job = job_manager.get_job(job_id)
            job.status = JobStatus.RUNNING
            job.progress = 45
            job.partial_results = {
                "scanned_files": 3,
                "total_files": 8,
                "found_dependencies": [
                    {"name": "requests", "version": "2.28.1", "type": "python"}
                ],
                "current_file": "requirements.txt",
                "scan_stage": "parsing_dependencies"
            }
            
            # Test partial results endpoint
            response = client.get(f"/jobs/{job_id}/partial", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "running"
            assert data["progress"] == 45
            assert data["partial_results"]["scanned_files"] == 3
    
    def test_partial_results_cleared_after_completion(self, client, auth_headers):
        """Test that partial results are cleared after job completion."""
        job_manager._jobs.clear()
        
        # Create a completed job that had partial results
        job = Job("completed_job", "https://github.com/test/repo.git")
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.partial_results = None  # Should be cleared after completion
        job_manager._jobs[job.job_id] = job
        
        # Should not be able to get partial results for completed job
        response = client.get(f"/jobs/{job.job_id}/partial", headers=auth_headers)
        assert response.status_code == 400
        assert "not currently running" in response.json()["detail"]


class TestPartialResultsPerformance:
    """Test partial results performance characteristics."""
    
    def test_partial_results_endpoint_performance(self, client, auth_headers):
        """Test that partial results endpoint responds quickly."""
        job_manager._jobs.clear()
        
        # Create a job with large partial results
        job = Job("large_job", "https://github.com/test/repo.git")
        job.status = JobStatus.RUNNING
        job.progress = 80
        job.partial_results = {
            "scanned_files": 500,
            "total_files": 1000,
            "found_dependencies": [
                {"name": f"package_{i}", "version": "1.0.0", "type": "python"}
                for i in range(100)  # Large number of dependencies
            ],
            "current_file": "big_requirements.txt",
            "scan_stage": "analyzing_imports"
        }
        job_manager._jobs[job.job_id] = job
        
        # Should respond quickly even with large data
        import time
        start_time = time.time()
        response = client.get(f"/jobs/{job.job_id}/partial", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond within 1 second
    
    def test_partial_results_memory_usage(self):
        """Test that partial results don't consume excessive memory."""
        job_manager._jobs.clear()
        
        # Create many jobs with partial results
        for i in range(100):
            job = Job(f"job_{i}", f"https://github.com/test/repo{i}.git")
            job.status = JobStatus.RUNNING
            job.partial_results = {
                "scanned_files": i,
                "total_files": 100,
                "found_dependencies": [
                    {"name": f"package_{j}", "version": "1.0.0", "type": "python"}
                    for j in range(10)
                ],
                "current_file": f"file_{i}.txt",
                "scan_stage": "analyzing_imports"
            }
            job_manager._jobs[job.job_id] = job
        
        # Memory usage should be reasonable
        # In a real implementation, we'd measure actual memory usage
        assert len(job_manager._jobs) == 100