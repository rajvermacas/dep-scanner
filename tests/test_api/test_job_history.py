"""Tests for job history endpoint."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import base64
from datetime import datetime, timezone, timedelta

from dependency_scanner_tool.api.app import app
from dependency_scanner_tool.api.job_manager import job_manager, Job, JobStatus
from dependency_scanner_tool.api.models import ScanResultResponse


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
def sample_jobs():
    """Create sample jobs for testing."""
    jobs = []
    
    # Create jobs with different statuses and timestamps
    for i in range(15):  # More than one page
        job = Job(f"job_{i}", f"https://github.com/test/repo{i}.git")
        job.created_at = datetime.now(timezone.utc) - timedelta(hours=i)
        
        # Set different statuses
        if i % 4 == 0:
            job.status = JobStatus.COMPLETED
            job.completed_at = job.created_at + timedelta(minutes=30)
            job.progress = 100
            job.result = ScanResultResponse(
                git_url=job.git_url,
                dependencies={"Data Science": True, "Web Frameworks": False}
            )
        elif i % 4 == 1:
            job.status = JobStatus.RUNNING
            job.progress = 50
        elif i % 4 == 2:
            job.status = JobStatus.FAILED
            job.completed_at = job.created_at + timedelta(minutes=15)
            job.error_message = f"Test error for job {i}"
        else:
            job.status = JobStatus.PENDING
            job.progress = 0
        
        jobs.append(job)
    
    return jobs


class TestJobHistoryEndpoint:
    """Test job history endpoint functionality."""
    
    def test_get_jobs_endpoint_exists(self, client, auth_headers):
        """Test that GET /jobs endpoint exists and requires authentication."""
        # Test without authentication
        response = client.get("/jobs")
        assert response.status_code == 401
        
        # Test with authentication
        response = client.get("/jobs", headers=auth_headers)
        # Should return 200 even if no jobs exist
        assert response.status_code == 200
    
    def test_get_jobs_empty_list(self, client, auth_headers):
        """Test GET /jobs returns empty list when no jobs exist."""
        # Clear all jobs
        job_manager._jobs.clear()
        
        response = client.get("/jobs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        
        assert data["jobs"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 0
    
    def test_get_jobs_with_data(self, client, auth_headers, sample_jobs):
        """Test GET /jobs returns job data."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        for job in sample_jobs:
            job_manager._jobs[job.job_id] = job
        
        response = client.get("/jobs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 10  # Default page size
        assert data["total"] == 15
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 2
        
        # Check job data structure
        job_data = data["jobs"][0]
        assert "job_id" in job_data
        assert "git_url" in job_data
        assert "status" in job_data
        assert "created_at" in job_data
        assert "progress" in job_data
    
    def test_get_jobs_pagination(self, client, auth_headers, sample_jobs):
        """Test GET /jobs pagination functionality."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        for job in sample_jobs:
            job_manager._jobs[job.job_id] = job
        
        # Test page 1
        response = client.get("/jobs?page=1&per_page=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["jobs"]) == 5
        assert data["page"] == 1
        assert data["per_page"] == 5
        assert data["total_pages"] == 3
        
        # Test page 2
        response = client.get("/jobs?page=2&per_page=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["jobs"]) == 5
        assert data["page"] == 2
        assert data["per_page"] == 5
        
        # Test last page
        response = client.get("/jobs?page=3&per_page=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["jobs"]) == 5
        assert data["page"] == 3
        assert data["per_page"] == 5
    
    def test_get_jobs_pagination_out_of_range(self, client, auth_headers, sample_jobs):
        """Test GET /jobs pagination with out-of-range page numbers."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        for job in sample_jobs:
            job_manager._jobs[job.job_id] = job
        
        # Test page 0 (should default to 1)
        response = client.get("/jobs?page=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        
        # Test negative page (should default to 1)
        response = client.get("/jobs?page=-1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        
        # Test page beyond total (should return empty)
        response = client.get("/jobs?page=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["page"] == 10
    
    def test_get_jobs_custom_page_size(self, client, auth_headers, sample_jobs):
        """Test GET /jobs with custom page size."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        for job in sample_jobs:
            job_manager._jobs[job.job_id] = job
        
        # Test custom page size
        response = client.get("/jobs?per_page=3", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["jobs"]) == 3
        assert data["per_page"] == 3
        assert data["total_pages"] == 5  # 15 jobs / 3 per page = 5 pages
    
    def test_get_jobs_max_page_size_limit(self, client, auth_headers, sample_jobs):
        """Test GET /jobs respects maximum page size limit."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        for job in sample_jobs:
            job_manager._jobs[job.job_id] = job
        
        # Test with very large page size (should be capped)
        response = client.get("/jobs?per_page=1000", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Should be capped at max limit (e.g., 100)
        assert data["per_page"] <= 100
    
    def test_get_jobs_sorting_by_created_at(self, client, auth_headers, sample_jobs):
        """Test GET /jobs returns jobs sorted by creation time (newest first)."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        for job in sample_jobs:
            job_manager._jobs[job.job_id] = job
        
        response = client.get("/jobs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        jobs = data["jobs"]
        
        # Check that jobs are sorted by created_at in descending order (newest first)
        for i in range(len(jobs) - 1):
            current_time = datetime.fromisoformat(jobs[i]["created_at"].replace("Z", "+00:00"))
            next_time = datetime.fromisoformat(jobs[i + 1]["created_at"].replace("Z", "+00:00"))
            assert current_time >= next_time
    
    def test_get_jobs_status_filter(self, client, auth_headers, sample_jobs):
        """Test GET /jobs with status filter."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        for job in sample_jobs:
            job_manager._jobs[job.job_id] = job
        
        # Test filter by COMPLETED status
        response = client.get("/jobs?status=completed", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        jobs = data["jobs"]
        
        # All returned jobs should be completed
        for job in jobs:
            assert job["status"] == "completed"
        
        # Test filter by RUNNING status
        response = client.get("/jobs?status=running", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        jobs = data["jobs"]
        
        # All returned jobs should be running
        for job in jobs:
            assert job["status"] == "running"
    
    def test_get_jobs_invalid_status_filter(self, client, auth_headers):
        """Test GET /jobs with invalid status filter."""
        response = client.get("/jobs?status=invalid_status", headers=auth_headers)
        assert response.status_code == 400
        assert "Invalid status filter" in response.json()["detail"]
    
    def test_get_jobs_response_format(self, client, auth_headers, sample_jobs):
        """Test GET /jobs response format matches expected schema."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        for job in sample_jobs[:3]:  # Use fewer jobs for easier testing
            job_manager._jobs[job.job_id] = job
        
        response = client.get("/jobs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level structure
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        
        # Check job structure
        for job in data["jobs"]:
            assert "job_id" in job
            assert "git_url" in job
            assert "status" in job
            assert "created_at" in job
            assert "progress" in job
            
            # Optional fields
            if job["status"] in ["completed", "failed"]:
                assert "completed_at" in job
            
            if job["status"] == "failed":
                assert "error_message" in job
    
    def test_get_jobs_includes_job_details(self, client, auth_headers, sample_jobs):
        """Test GET /jobs includes necessary job details."""
        # Clear existing jobs and add sample jobs
        job_manager._jobs.clear()
        completed_job = sample_jobs[0]  # First job is completed
        failed_job = sample_jobs[2]      # Third job is failed
        job_manager._jobs[completed_job.job_id] = completed_job
        job_manager._jobs[failed_job.job_id] = failed_job
        
        response = client.get("/jobs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        jobs = data["jobs"]
        
        # Find completed job
        completed_job_data = next((job for job in jobs if job["status"] == "completed"), None)
        assert completed_job_data is not None
        assert completed_job_data["progress"] == 100
        assert "completed_at" in completed_job_data
        
        # Find failed job
        failed_job_data = next((job for job in jobs if job["status"] == "failed"), None)
        assert failed_job_data is not None
        assert "error_message" in failed_job_data
        assert "completed_at" in failed_job_data