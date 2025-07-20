"""REST API client for the Dependency Scanner Tool."""

import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urljoin
import requests
from requests.auth import HTTPBasicAuth

from dependency_scanner_tool.api.models import (
    ScanRequest, ScanResponse, JobStatusResponse, ScanResultResponse,
    JobHistoryResponse, PartialResultsResponse, JobStatus
)

logger = logging.getLogger(__name__)


class DependencyScannerClient:
    """Client for interacting with the Dependency Scanner REST API."""
    
    def __init__(
        self, 
        base_url: str, 
        username: str, 
        password: str,
        timeout: int = 30,
        poll_interval: int = 5
    ):
        """Initialize the client.
        
        Args:
            base_url: Base URL of the API server (e.g., "http://localhost:8000")
            username: API username for authentication
            password: API password for authentication
            timeout: Request timeout in seconds
            poll_interval: Polling interval in seconds for waiting operations
        """
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.session = requests.Session()
        self.session.auth = self.auth
        
        # Verify connection on initialization
        self._verify_connection()
    
    def _verify_connection(self) -> None:
        """Verify connection to the API server."""
        try:
            response = self.health_check()
            logger.info(f"Connected to Dependency Scanner API v{response.get('version', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to connect to API server: {e}")
            raise ConnectionError(f"Cannot connect to API server at {self.base_url}: {e}")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> requests.Response:
        """Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If request fails
        """
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"{method} {url} failed: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status.
        
        Returns:
            Health status information
        """
        response = self._make_request('GET', '/health')
        return response.json()
    
    def submit_scan(self, git_url: str) -> ScanResponse:
        """Submit a repository for scanning.
        
        Args:
            git_url: Git repository URL to scan
            
        Returns:
            Scan response with job ID and status
        """
        request_data = ScanRequest(git_url=git_url)
        response = self._make_request(
            'POST', 
            '/scan',
            json=request_data.model_dump()
        )
        return ScanResponse(**response.json())
    
    def get_job_status(self, job_id: str) -> JobStatusResponse:
        """Get job status by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status information
        """
        response = self._make_request('GET', f'/jobs/{job_id}')
        return JobStatusResponse(**response.json())
    
    def get_job_results(self, job_id: str) -> ScanResultResponse:
        """Get job results by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Scan results
            
        Raises:
            requests.HTTPError: If job is not completed or results not available
        """
        response = self._make_request('GET', f'/jobs/{job_id}/results')
        return ScanResultResponse(**response.json())
    
    def get_partial_results(self, job_id: str) -> PartialResultsResponse:
        """Get partial results for a running job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Partial results information
        """
        response = self._make_request('GET', f'/jobs/{job_id}/partial')
        return PartialResultsResponse(**response.json())
    
    def list_jobs(
        self, 
        page: int = 1, 
        per_page: int = 10, 
        status: Optional[str] = None
    ) -> JobHistoryResponse:
        """List jobs with pagination and optional status filter.
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of jobs per page
            status: Optional status filter
            
        Returns:
            Job history with pagination info
        """
        params = {'page': page, 'per_page': per_page}
        if status:
            params['status'] = status
            
        response = self._make_request('GET', '/jobs', params=params)
        return JobHistoryResponse(**response.json())
    
    def wait_for_completion(
        self, 
        job_id: str, 
        max_wait: int = 600,
        show_progress: bool = True
    ) -> Tuple[JobStatusResponse, Optional[ScanResultResponse]]:
        """Wait for a job to complete and return results.
        
        Args:
            job_id: Job identifier
            max_wait: Maximum wait time in seconds
            show_progress: Whether to print progress updates
            
        Returns:
            Tuple of (final_status, results). Results is None if job failed.
            
        Raises:
            TimeoutError: If job doesn't complete within max_wait seconds
        """
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < max_wait:
            status_response = self.get_job_status(job_id)
            
            if show_progress and status_response.progress != last_progress:
                print(f"Job {job_id}: {status_response.status.value} - {status_response.progress}%")
                last_progress = status_response.progress
            
            if status_response.status == JobStatus.COMPLETED:
                try:
                    results = self.get_job_results(job_id)
                    return status_response, results
                except Exception as e:
                    logger.error(f"Failed to get results for completed job {job_id}: {e}")
                    return status_response, None
            
            elif status_response.status == JobStatus.FAILED:
                logger.error(f"Job {job_id} failed")
                return status_response, None
            
            time.sleep(self.poll_interval)
        
        raise TimeoutError(f"Job {job_id} did not complete within {max_wait} seconds")
    
    def scan_repository_and_wait(
        self, 
        git_url: str, 
        max_wait: int = 600,
        show_progress: bool = True
    ) -> Tuple[str, ScanResultResponse]:
        """Submit a repository scan and wait for completion.
        
        Args:
            git_url: Git repository URL to scan
            max_wait: Maximum wait time in seconds
            show_progress: Whether to print progress updates
            
        Returns:
            Tuple of (job_id, scan_results)
            
        Raises:
            Exception: If scan submission or completion fails
        """
        print(f"Submitting scan for repository: {git_url}")
        scan_response = self.submit_scan(git_url)
        job_id = scan_response.job_id
        
        print(f"Scan submitted successfully. Job ID: {job_id}")
        print(f"Waiting for completion (max {max_wait} seconds)...")
        
        final_status, results = self.wait_for_completion(
            job_id, max_wait, show_progress
        )
        
        if final_status.status == JobStatus.FAILED:
            raise Exception(f"Scan failed for job {job_id}")
        
        if results is None:
            raise Exception(f"No results available for job {job_id}")
        
        print(f"Scan completed successfully!")
        return job_id, results