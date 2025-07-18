"""Job lifecycle management with cleanup and resource limits."""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from pathlib import Path

from dependency_scanner_tool.api.job_manager import job_manager, JobStatus
from dependency_scanner_tool.api.git_service import git_service


logger = logging.getLogger(__name__)


class JobLifecycleManager:
    """Manages job lifecycle with resource limits and cleanup."""
    
    def __init__(
        self,
        max_concurrent_jobs: int = 5,
        job_timeout: int = 1800,  # 30 minutes
        cleanup_interval: int = 300,  # 5 minutes
        max_job_age: int = 86400,  # 24 hours
    ):
        """
        Initialize job lifecycle manager.
        
        Args:
            max_concurrent_jobs: Maximum number of concurrent jobs
            job_timeout: Maximum job execution time in seconds
            cleanup_interval: Interval between cleanup runs in seconds
            max_job_age: Maximum age of completed jobs in seconds
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.job_timeout = job_timeout
        self.cleanup_interval = cleanup_interval
        self.max_job_age = max_job_age
        self.running_jobs: Set[str] = set()
        self.job_start_times: Dict[str, float] = {}
        self.job_resources: Dict[str, List[Path]] = {}  # Track temp directories
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the job lifecycle manager."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Job lifecycle manager started")
    
    async def stop(self) -> None:
        """Stop the job lifecycle manager."""
        if not self._running:
            return
        
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clean up any remaining jobs
        await self._cleanup_all_jobs()
        logger.info("Job lifecycle manager stopped")
    
    def can_create_job(self) -> bool:
        """Check if a new job can be created."""
        return len(self.running_jobs) < self.max_concurrent_jobs
    
    def register_job_start(self, job_id: str) -> None:
        """Register that a job has started."""
        if job_id not in self.running_jobs:
            self.running_jobs.add(job_id)
            self.job_start_times[job_id] = time.time()
            self.job_resources[job_id] = []
            logger.info(f"Job {job_id} registered as started")
    
    def register_job_resource(self, job_id: str, resource_path: Path) -> None:
        """Register a resource (temp directory) for a job."""
        if job_id in self.job_resources:
            self.job_resources[job_id].append(resource_path)
            logger.debug(f"Resource {resource_path} registered for job {job_id}")
    
    def register_job_completion(self, job_id: str) -> None:
        """Register that a job has completed."""
        if job_id in self.running_jobs:
            self.running_jobs.remove(job_id)
            self.job_start_times.pop(job_id, None)
            logger.info(f"Job {job_id} registered as completed")
        
        # Clean up resources immediately
        self._cleanup_job_resources(job_id)
    
    def _cleanup_job_resources(self, job_id: str) -> None:
        """Clean up resources for a specific job."""
        if job_id in self.job_resources:
            resources = self.job_resources.pop(job_id)
            for resource_path in resources:
                try:
                    git_service.cleanup_repository(resource_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup resource {resource_path}: {e}")
    
    def get_running_jobs(self) -> List[str]:
        """Get list of currently running job IDs."""
        return list(self.running_jobs)
    
    def get_job_runtime(self, job_id: str) -> Optional[float]:
        """Get the runtime of a job in seconds."""
        if job_id in self.job_start_times:
            return time.time() - self.job_start_times[job_id]
        return None
    
    def is_job_timed_out(self, job_id: str) -> bool:
        """Check if a job has timed out."""
        runtime = self.get_job_runtime(job_id)
        return runtime is not None and runtime > self.job_timeout
    
    async def _cleanup_loop(self) -> None:
        """Background loop for periodic cleanup."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if self._running:
                    await self._cleanup_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_jobs(self) -> None:
        """Perform periodic job cleanup."""
        # Clean up timed out jobs
        timed_out_jobs = []
        for job_id in list(self.running_jobs):
            if self.is_job_timed_out(job_id):
                timed_out_jobs.append(job_id)
        
        for job_id in timed_out_jobs:
            logger.warning(f"Job {job_id} timed out, marking as failed")
            job_manager.set_job_error(job_id, f"Job timed out after {self.job_timeout} seconds")
            self.register_job_completion(job_id)
        
        # Clean up old completed jobs
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.max_job_age)
        old_jobs = []
        
        for job_id in job_manager.jobs:
            job = job_manager.get_job(job_id)
            if job and job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                if job.completed_at and job.completed_at < cutoff_time:
                    old_jobs.append(job_id)
        
        for job_id in old_jobs:
            logger.info(f"Removing old job {job_id}")
            job_manager.remove_job(job_id)
            self._cleanup_job_resources(job_id)
        
        logger.debug(f"Cleanup complete. Running jobs: {len(self.running_jobs)}, Total jobs: {len(job_manager.jobs)}")
    
    async def _cleanup_all_jobs(self) -> None:
        """Clean up all jobs and resources."""
        # Mark all running jobs as failed
        for job_id in list(self.running_jobs):
            job_manager.set_job_error(job_id, "Service shutdown")
            self.register_job_completion(job_id)
        
        # Clean up any remaining resources
        for job_id in list(self.job_resources.keys()):
            self._cleanup_job_resources(job_id)
        
        logger.info("All jobs cleaned up")
    
    def get_stats(self) -> Dict:
        """Get current job lifecycle statistics."""
        return {
            "running_jobs": len(self.running_jobs),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "total_jobs": len(job_manager.jobs),
            "job_timeout": self.job_timeout,
            "cleanup_interval": self.cleanup_interval,
            "max_job_age": self.max_job_age,
        }


# Global job lifecycle manager instance
job_lifecycle_manager = JobLifecycleManager()