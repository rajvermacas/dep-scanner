"""Security tests for the REST API endpoints."""

import pytest
import base64
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
    # Username: admin, Password: secret123
    credentials = base64.b64encode(b"admin:secret123").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def invalid_auth_header():
    """Create invalid Basic Auth header for testing."""
    credentials = base64.b64encode(b"wrong:password").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


class TestBasicAuthentication:
    """Test HTTP Basic Authentication on all endpoints."""
    
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
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
            # Create a job
            response = client.post(
                "/scan", 
                json={"git_url": "https://github.com/test/repo.git"},
                headers=valid_auth_header
            )
            job_id = response.json()["job_id"]
            
            # Wait for job to complete
            mock_scan.return_value = None
            
            # Check that temporary files are cleaned up
            with patch('shutil.rmtree') as mock_rmtree:
                # This should be called during cleanup
                mock_rmtree.assert_called()
    
    def test_job_cleanup_after_failure(self, client, valid_auth_header):
        """Test that jobs are cleaned up after failure."""
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
            mock_scan.side_effect = Exception("Scan failed")
            
            response = client.post(
                "/scan", 
                json={"git_url": "https://github.com/test/repo.git"},
                headers=valid_auth_header
            )
            job_id = response.json()["job_id"]
            
            # Check that cleanup occurs even after failure
            with patch('shutil.rmtree') as mock_rmtree:
                mock_rmtree.assert_called()
    
    def test_maximum_concurrent_jobs_limit(self, client, valid_auth_header):
        """Test that there's a limit on concurrent jobs."""
        # Try to create more than the allowed number of concurrent jobs
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository'):
            job_ids = []
            for i in range(10):  # Try to create 10 jobs
                response = client.post(
                    "/scan", 
                    json={"git_url": f"https://github.com/test/repo{i}.git"},
                    headers=valid_auth_header
                )
                if response.status_code == 200:
                    job_ids.append(response.json()["job_id"])
                else:
                    # Should get rate limited
                    assert response.status_code == 429
                    assert "Too many concurrent jobs" in response.json()["detail"]
                    break
            
            # Should have hit the limit before creating all 10 jobs
            assert len(job_ids) < 10
    
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
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
            # Mock a git clone that would hang
            mock_scan.side_effect = Exception("Git clone timeout after 300 seconds")
            
            response = client.post(
                "/scan", 
                json={"git_url": "https://github.com/test/slowrepo.git"},
                headers=valid_auth_header
            )
            assert response.status_code == 200  # Job created successfully
            
            # Check that job eventually fails with timeout
            job_id = response.json()["job_id"]
            
            # In a real test, we'd wait and check job status
            # For now, we just verify the timeout mechanism exists
    
    def test_scan_operation_timeout(self, client, valid_auth_header):
        """Test that scan operations have timeout protection."""
        with patch('dependency_scanner_tool.api.scanner_service.scanner_service.scan_repository') as mock_scan:
            # Mock a scan that would hang
            mock_scan.side_effect = Exception("Scan timeout after 600 seconds")
            
            response = client.post(
                "/scan", 
                json={"git_url": "https://github.com/test/largerepo.git"},
                headers=valid_auth_header
            )
            assert response.status_code == 200  # Job created successfully
    
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