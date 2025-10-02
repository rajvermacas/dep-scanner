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
from dependency_scanner_tool.api.constants import (
    CLIENT_DEFAULT_MAX_WAIT,
    CLIENT_RESULT_RETRY_COUNT,
    CLIENT_RESULT_RETRY_DELAY
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
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get detailed job status using the subprocess monitoring endpoint.

        Args:
            job_id: Job identifier

        Returns:
            Detailed job status information from /scan/{job_id}
        """
        response = self._make_request('GET', f'/scan/{job_id}')
        return response.json()
    
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
        max_wait: int = CLIENT_DEFAULT_MAX_WAIT,
        show_progress: bool = True
    ) -> Tuple[Dict[str, Any], Optional[ScanResultResponse]]:
        """Wait for a job to complete and return results.

        Args:
            job_id: Job identifier
            max_wait: Maximum wait time in seconds
            show_progress: Whether to print progress updates

        Returns:
            Tuple of (detailed_status, results). Results is None if job failed.

        Raises:
            TimeoutError: If job doesn't complete within max_wait seconds
        """
        start_time = time.time()
        last_progress = {}

        while time.time() - start_time < max_wait:
            # Get detailed progress from subprocess monitoring
            detailed_progress = self.get_job_status(job_id)

            if show_progress:
                self._display_detailed_progress(detailed_progress, last_progress)
                last_progress = detailed_progress.copy()

            # Check if job is complete based on detailed status
            status = detailed_progress.get("status", "unknown")

            if status in ["completed", "completed_with_errors", "all_failed"]:
                # Results might lag by a moment; retry briefly if unavailable
                retries = CLIENT_RESULT_RETRY_COUNT
                while retries > 0:
                    try:
                        results = self.get_job_results(job_id)
                        return detailed_progress, results
                    except requests.HTTPError as e:
                        # If job not yet marked completed on server side, wait and retry
                        code = getattr(e.response, 'status_code', None)
                        if code in (400, 404):
                            time.sleep(CLIENT_RESULT_RETRY_DELAY)
                            retries -= 1
                            continue
                        raise
                    except Exception as e:
                        logger.error(f"Failed to get results for completed job {job_id}: {e}")
                        break
                # If we exit the retry loop without results, return status without results
                logger.error(f"Failed to get results for completed job {job_id} after retries")
                return detailed_progress, None

            elif status in ["failed", "not_found", "error"]:
                error_msg = detailed_progress.get("error", "Job failed")
                logger.error(f"Job {job_id} failed: {error_msg}")
                return detailed_progress, None

            time.sleep(self.poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {max_wait} seconds")

    def _display_detailed_progress(self, current: Dict[str, Any], last: Dict[str, Any]) -> None:
        """Display detailed progress information."""
        # Only show updates if something changed
        if current == last:
            return

        job_id = current.get("job_id", "unknown")
        status = current.get("status", "unknown")

        # Show basic status
        elapsed = current.get("elapsed_time_seconds", 0)
        elapsed_str = f"{elapsed:.1f}s" if elapsed else "unknown"
        print(f"Job {job_id}: {status} (elapsed: {elapsed_str})")

        # Show repository summary if available
        summary = current.get("summary")
        if summary:
            total = summary.get("total_repositories", 0)
            completed = summary.get("completed", 0)
            in_progress = summary.get("in_progress", 0)
            pending = summary.get("pending", 0)
            failed = summary.get("failed", 0)

            if total > 0:
                progress_pct = (completed / total) * 100
                print(f"  Repositories: {completed}/{total} completed ({progress_pct:.1f}%)")
                if in_progress > 0:
                    print(f"  In progress: {in_progress}")
                if pending > 0:
                    print(f"  Pending: {pending}")
                if failed > 0:
                    print(f"  Failed: {failed}")

        # Show current repository being processed
        # Check both field names for backward compatibility
        current_repos = current.get("current_repositories", [])
        if not current_repos:
            # Fallback to old field name for compatibility
            current_repos = current.get("in_progress_repositories", [])

        if current_repos:
            for repo_info in current_repos:
                if isinstance(repo_info, dict):
                    repo_name = repo_info.get("repo_name", "unknown")
                    # Check for progress details in nested structure
                    progress = repo_info.get("progress", {})
                    if progress:
                        current_file_name = progress.get("current_file_name")
                        percentage = progress.get("percentage")
                        current_idx = progress.get("current_file")
                        total_files = progress.get("total_files")

                        detail_parts = []
                        if current_idx is not None and total_files is not None:
                            detail_parts.append(f"{current_idx}/{total_files}")
                        if percentage is not None:
                            detail_parts.append(f"{percentage:.1f}%")

                        detail = " ".join(detail_parts) if detail_parts else None

                        if current_file_name:
                            if detail:
                                print(f"  Processing: {repo_name} - {current_file_name} ({detail})")
                            else:
                                print(f"  Processing: {repo_name} - {current_file_name}")
                        elif "message" in progress:
                            if detail:
                                print(f"  Processing: {repo_name} - {progress['message']} ({detail})")
                            else:
                                print(f"  Processing: {repo_name} - {progress['message']}")
                        else:
                            if detail:
                                print(f"  Processing: {repo_name} ({detail})")
                            else:
                                print(f"  Processing: {repo_name}")
                    else:
                        # Fallback to old structure
                        current_file = repo_info.get("current_file", "")
                        if current_file:
                            print(f"  Processing: {repo_name} - {current_file}")
                        else:
                            print(f"  Processing: {repo_name}")
                else:
                    print(f"  Processing: {repo_info}")

        # Show recently completed repositories
        completed_repos = current.get("completed_repositories", [])
        last_completed = last.get("completed_repositories", [])
        newly_completed = [repo for repo in completed_repos if repo not in last_completed]
        if newly_completed:
            for repo in newly_completed:
                print(f"  ✓ Completed: {repo}")

        # Show failed repositories
        failed_repos = current.get("failed_repositories", [])
        last_failed = last.get("failed_repositories", [])
        newly_failed = [repo for repo in failed_repos if repo not in last_failed]
        if newly_failed:
            for repo_info in newly_failed:
                if isinstance(repo_info, dict):
                    repo_name = repo_info.get("repo_name", "unknown")
                    error = repo_info.get("error", "Unknown error")
                    print(f"  ✗ Failed: {repo_name} - {error}")
                else:
                    print(f"  ✗ Failed: {repo_info}")
    
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
        
        # final_status is now a dict from detailed progress
        if final_status.get("status") in ["failed", "all_failed", "error"]:
            error_msg = final_status.get("error", "Scan failed")
            raise Exception(f"Scan failed for job {job_id}: {error_msg}")
        
        if results is None:
            raise Exception(f"No results available for job {job_id}")
        
        print(f"Scan completed successfully!")
        return job_id, results
