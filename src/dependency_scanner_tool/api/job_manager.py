"""Job management for the REST API."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from dependency_scanner_tool.api.models import JobStatus, ScanResultResponse


class Job:
    """Represents a scan job."""
    
    def __init__(self, job_id: str, git_url: str):
        self.job_id = job_id
        self.git_url = git_url
        self.status = JobStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.progress = 0
        self.error_message: Optional[str] = None
        self.result: Optional[ScanResultResponse] = None


class JobManager:
    """Manages scan jobs."""
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
    
    def create_job(self, git_url: str) -> str:
        """Create a new scan job."""
        job_id = str(uuid.uuid4())
        job = Job(job_id, git_url)
        self._jobs[job_id] = job
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def update_job_status(self, job_id: str, status: JobStatus, progress: int = 0):
        """Update job status."""
        job = self._jobs.get(job_id)
        if job:
            job.status = status
            job.progress = progress
            if status == JobStatus.COMPLETED or status == JobStatus.FAILED:
                job.completed_at = datetime.now(timezone.utc)
    
    def set_job_result(self, job_id: str, result: ScanResultResponse):
        """Set job result."""
        job = self._jobs.get(job_id)
        if job:
            job.result = result
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
    
    def set_job_error(self, job_id: str, error_message: str):
        """Set job error."""
        job = self._jobs.get(job_id)
        if job:
            job.error_message = error_message
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False
    
    @property
    def jobs(self) -> Dict[str, Job]:
        """Get all jobs."""
        return self._jobs


# Global job manager instance
job_manager = JobManager()