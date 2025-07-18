"""Tests for concurrent job management."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import base64

from dependency_scanner_tool.api.app import app
from dependency_scanner_tool.api.job_manager import job_manager
from dependency_scanner_tool.api.job_lifecycle import job_lifecycle_manager


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
def mock_git_service():
    """Mock git service for testing."""
    with patch('dependency_scanner_tool.api.git_service.git_service') as mock_service:
        mock_service.clone_repository.return_value = MagicMock()
        mock_service.validate_repository.return_value = True
        mock_service.cleanup_repository.return_value = None
        yield mock_service


@pytest.fixture
def mock_scanner():
    """Mock scanner for testing."""
    with patch('dependency_scanner_tool.api.scanner_service.scanner_service') as mock_service:
        mock_result = MagicMock()
        mock_result.dependencies = []
        mock_service.scanner.scan_project.return_value = mock_result
        yield mock_service


class TestConcurrentJobManagement:
    """Test concurrent job management functionality."""
    
    def test_can_create_job_within_limit(self, client, auth_headers, mock_git_service, mock_scanner):
        """Test that jobs can be created within the concurrent limit."""
        # Reset job lifecycle manager to known state
        job_lifecycle_manager.running_jobs.clear()
        job_lifecycle_manager.job_start_times.clear()
        job_lifecycle_manager.job_resources.clear()
        
        # Create a job - should succeed
        response = client.post(
            "/scan", 
            json={"git_url": "https://github.com/test/repo.git"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
    
    def test_concurrent_job_limit_enforcement(self, client, auth_headers, mock_git_service, mock_scanner):
        """Test that the concurrent job limit is enforced."""
        # Reset job lifecycle manager to known state
        job_lifecycle_manager.running_jobs.clear()
        job_lifecycle_manager.job_start_times.clear()
        job_lifecycle_manager.job_resources.clear()
        
        # Fill up the concurrent job slots (default is 5)
        for i in range(job_lifecycle_manager.max_concurrent_jobs):
            job_lifecycle_manager.register_job_start(f"test_job_{i}")
        
        # Now try to create another job - should fail
        response = client.post(
            "/scan", 
            json={"git_url": "https://github.com/test/repo.git"},
            headers=auth_headers
        )
        
        assert response.status_code == 429
        assert "Too many concurrent jobs" in response.json()["detail"]
    
    def test_job_completion_frees_up_slot(self, client, auth_headers, mock_git_service, mock_scanner):
        """Test that completing a job frees up a concurrent slot."""
        # Reset job lifecycle manager to known state
        job_lifecycle_manager.running_jobs.clear()
        job_lifecycle_manager.job_start_times.clear()
        job_lifecycle_manager.job_resources.clear()
        
        # Fill up the concurrent job slots
        job_ids = []
        for i in range(job_lifecycle_manager.max_concurrent_jobs):
            job_id = f"test_job_{i}"
            job_lifecycle_manager.register_job_start(job_id)
            job_ids.append(job_id)
        
        # Complete one job
        job_lifecycle_manager.register_job_completion(job_ids[0])
        
        # Now we should be able to create another job
        response = client.post(
            "/scan", 
            json={"git_url": "https://github.com/test/repo.git"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
    
    def test_service_readiness_check(self):
        """Test the service readiness check method."""
        # Reset job lifecycle manager to known state
        job_lifecycle_manager.running_jobs.clear()
        job_lifecycle_manager.job_start_times.clear()
        job_lifecycle_manager.job_resources.clear()
        
        # Service should be ready when under limit
        assert job_lifecycle_manager.can_create_job() is True
        
        # Fill up the concurrent job slots
        for i in range(job_lifecycle_manager.max_concurrent_jobs):
            job_lifecycle_manager.register_job_start(f"test_job_{i}")
        
        # Service should not be ready when at limit
        assert job_lifecycle_manager.can_create_job() is False
    
    def test_running_jobs_tracking(self):
        """Test that running jobs are properly tracked."""
        # Reset job lifecycle manager to known state
        job_lifecycle_manager.running_jobs.clear()
        job_lifecycle_manager.job_start_times.clear()
        job_lifecycle_manager.job_resources.clear()
        
        # Initially no running jobs
        assert len(job_lifecycle_manager.get_running_jobs()) == 0
        
        # Register some jobs
        job_ids = ["job1", "job2", "job3"]
        for job_id in job_ids:
            job_lifecycle_manager.register_job_start(job_id)
        
        # Should track all running jobs
        running_jobs = job_lifecycle_manager.get_running_jobs()
        assert len(running_jobs) == 3
        assert set(running_jobs) == set(job_ids)
        
        # Complete one job
        job_lifecycle_manager.register_job_completion("job1")
        
        # Should have one less running job
        running_jobs = job_lifecycle_manager.get_running_jobs()
        assert len(running_jobs) == 2
        assert "job1" not in running_jobs
    
    def test_concurrent_job_limit_configuration(self):
        """Test that the concurrent job limit can be configured."""
        from dependency_scanner_tool.api.job_lifecycle import JobLifecycleManager
        
        # Create a new job lifecycle manager with different limit
        test_manager = JobLifecycleManager(max_concurrent_jobs=3)
        
        # Test the limit is applied
        assert test_manager.max_concurrent_jobs == 3
        
        # Should be able to create jobs up to the limit
        for i in range(3):
            test_manager.register_job_start(f"test_job_{i}")
        
        # Should be at capacity
        assert test_manager.can_create_job() is False
        
        # Should not be able to create more jobs
        assert len(test_manager.get_running_jobs()) == 3
    
    def test_job_statistics(self):
        """Test job lifecycle statistics."""
        # Reset job lifecycle manager to known state
        job_lifecycle_manager.running_jobs.clear()
        job_lifecycle_manager.job_start_times.clear()
        job_lifecycle_manager.job_resources.clear()
        
        # Create some test jobs in job manager
        for i in range(3):
            job_manager.create_job(f"https://github.com/test/repo{i}.git")
        
        # Register some running jobs
        for i in range(2):
            job_lifecycle_manager.register_job_start(f"running_job_{i}")
        
        # Get stats
        stats = job_lifecycle_manager.get_stats()
        
        # Verify stats
        assert stats["running_jobs"] == 2
        assert stats["max_concurrent_jobs"] == 5
        assert stats["total_jobs"] >= 3  # At least the ones we created
        assert stats["job_timeout"] == 1800
        assert stats["cleanup_interval"] == 300
        assert stats["max_job_age"] == 86400


class TestJobLifecycleManagement:
    """Test job lifecycle management functionality."""
    
    @pytest.mark.asyncio
    async def test_lifecycle_manager_start_stop(self):
        """Test starting and stopping the lifecycle manager."""
        from dependency_scanner_tool.api.job_lifecycle import JobLifecycleManager
        
        # Create a test manager
        test_manager = JobLifecycleManager()
        
        # Should not be running initially
        assert test_manager._running is False
        
        # Start the manager
        await test_manager.start()
        assert test_manager._running is True
        
        # Stop the manager
        await test_manager.stop()
        assert test_manager._running is False
    
    def test_job_timeout_detection(self):
        """Test job timeout detection."""
        from dependency_scanner_tool.api.job_lifecycle import JobLifecycleManager
        import time
        
        # Create a manager with very short timeout
        test_manager = JobLifecycleManager(job_timeout=1)
        
        # Register a job
        test_manager.register_job_start("timeout_job")
        
        # Should not be timed out initially
        assert test_manager.is_job_timed_out("timeout_job") is False
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Should be timed out now
        assert test_manager.is_job_timed_out("timeout_job") is True
    
    def test_job_resource_tracking(self):
        """Test job resource tracking."""
        from pathlib import Path
        
        # Reset job lifecycle manager to known state
        job_lifecycle_manager.running_jobs.clear()
        job_lifecycle_manager.job_start_times.clear()
        job_lifecycle_manager.job_resources.clear()
        
        # Register a job
        job_lifecycle_manager.register_job_start("resource_job")
        
        # Register some resources
        resource1 = Path("/tmp/resource1")
        resource2 = Path("/tmp/resource2")
        job_lifecycle_manager.register_job_resource("resource_job", resource1)
        job_lifecycle_manager.register_job_resource("resource_job", resource2)
        
        # Check resources are tracked
        assert "resource_job" in job_lifecycle_manager.job_resources
        assert len(job_lifecycle_manager.job_resources["resource_job"]) == 2
        assert resource1 in job_lifecycle_manager.job_resources["resource_job"]
        assert resource2 in job_lifecycle_manager.job_resources["resource_job"]
        
        # Complete the job
        job_lifecycle_manager.register_job_completion("resource_job")
        
        # Resources should be cleaned up
        assert "resource_job" not in job_lifecycle_manager.job_resources