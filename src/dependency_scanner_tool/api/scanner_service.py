"""Scanner service for subprocess-based repository scanning.

This service spawns subprocesses to perform CPU-intensive scanning
without blocking the FastAPI worker's event loop.
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from dependency_scanner_tool.api.models import ScanResultResponse, ProjectScanResult
from dependency_scanner_tool.api.job_manager import job_manager, JobStatus
from dependency_scanner_tool.api.job_lifecycle import job_lifecycle_manager
from dependency_scanner_tool.api.validation import validate_git_url, is_gitlab_group_url
from dependency_scanner_tool.api.gitlab_service import GitLabGroupService
from dependency_scanner_tool.api.job_monitor import job_monitor

logger = logging.getLogger(__name__)


class ScannerService:
    """Service for scanning repositories using subprocess execution."""

    # Maximum concurrent subprocesses
    MAX_CONCURRENT_PROCESSES = 5

    # Subprocess timeout in seconds (1 hour)
    SUBPROCESS_TIMEOUT = 3600

    def __init__(self):
        """Initialize scanner service."""
        self.active_processes: Dict[str, List[asyncio.subprocess.Process]] = {}
        logger.info("Scanner service initialized with subprocess execution")

    async def scan_repository(self, job_id: str, git_url: str) -> None:
        """Scan a Git repository or GitLab group using subprocesses.

        Args:
            job_id: Job identifier
            git_url: Git repository or group URL
        """
        try:
            # Register job start
            job_lifecycle_manager.register_job_start(job_id)

            # Validate Git URL
            logger.info(f"Validating Git URL for job {job_id}: {git_url}")
            validated_url = validate_git_url(git_url)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 5)

            # Determine scan type
            if is_gitlab_group_url(validated_url):
                logger.info(f"Job {job_id}: Detected GitLab group URL")
                await self._scan_gitlab_group_subprocess(job_id, validated_url)
            else:
                logger.info(f"Job {job_id}: Detected single repository URL")
                await self._scan_single_repository_subprocess(job_id, validated_url)

        except Exception as e:
            logger.error(f"Scan failed for job {job_id}: {str(e)}")
            job_manager.set_job_error(job_id, str(e))
            # Update master status to reflect failure
            job_monitor.update_master_status(
                job_id,
                status="failed",
                error=str(e),
                completed_at=datetime.now(timezone.utc).isoformat()
            )
        finally:
            # Register job completion
            job_lifecycle_manager.register_job_completion(job_id)
            # Cleanup processes
            await self._cleanup_job_processes(job_id)

    async def _scan_single_repository_subprocess(self, job_id: str, git_url: str) -> None:
        """Scan a single repository using subprocess.

        Args:
            job_id: Job identifier
            git_url: Repository URL
        """
        try:
            # Initialize master status
            job_monitor.update_master_status(
                job_id,
                group_url=git_url,
                total_repositories=1,
                status="initializing",
                started_at=datetime.now(timezone.utc).isoformat()
            )

            # Extract repository name from URL
            repo_name = git_url.split('/')[-1].replace('.git', '') if '/' in git_url else git_url

            # Spawn subprocess for scanning
            process = await self._spawn_scanner_subprocess(
                job_id, 0, repo_name, git_url
            )

            # Track process
            self.active_processes[job_id] = [process]

            # Monitor subprocess (non-blocking)
            monitor_task = asyncio.create_task(
                job_monitor.monitor_subprocess(job_id, process, 0, self.SUBPROCESS_TIMEOUT)
            )

            # Update job progress periodically while monitoring
            async def update_progress():
                while process.returncode is None:
                    await asyncio.sleep(5)  # Check every 5 seconds
                    status = await job_monitor.get_job_status(job_id)
                    if status.get("status") == "completed":
                        job_manager.update_job_status(job_id, JobStatus.RUNNING, 100)
                        break
                    elif status.get("status") == "failed":
                        break
                    else:
                        # Estimate progress based on status
                        progress = 50  # Default mid-progress
                        if status.get("current_repositories"):
                            curr = status["current_repositories"][0]
                            if curr.get("progress", {}).get("percentage"):
                                progress = int(curr["progress"]["percentage"] * 0.8 + 20)
                        job_manager.update_job_status(job_id, JobStatus.RUNNING, progress)

            progress_task = asyncio.create_task(update_progress())

            # Wait for subprocess to complete
            await monitor_task
            progress_task.cancel()

            # Get final status and update job
            final_status = await job_monitor.get_job_status(job_id)

            if final_status.get("status") in ["completed", "completed_with_errors"]:
                # Transform results for API response
                result = self._transform_subprocess_results_single(git_url, final_status)
                job_manager.set_job_result(job_id, result)

                # Update master status
                job_monitor.update_master_status(
                    job_id,
                    status="completed",
                    completed_at=datetime.now(timezone.utc).isoformat()
                )
                logger.info(f"Job {job_id}: Single repository scan completed")
            else:
                error_msg = "Scan subprocess failed"
                if final_status.get("failed_repositories"):
                    error_msg = final_status["failed_repositories"][0].get("error", error_msg)

                job_manager.set_job_error(job_id, error_msg)
                job_monitor.update_master_status(
                    job_id,
                    status="failed",
                    error=error_msg,
                    completed_at=datetime.now(timezone.utc).isoformat()
                )
                logger.error(f"Job {job_id}: Single repository scan failed")

        except Exception as e:
            logger.error(f"Subprocess scan failed for job {job_id}: {e}")
            raise

    async def _scan_gitlab_group_subprocess(self, job_id: str, group_url: str) -> None:
        """Scan a GitLab group using multiple subprocesses.

        Args:
            job_id: Job identifier
            group_url: GitLab group URL
        """
        gitlab_service = GitLabGroupService()

        try:
            # Get project information
            logger.info(f"Job {job_id}: Fetching GitLab group projects")
            project_info = gitlab_service.get_project_info(group_url)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 10)

            if not project_info:
                raise RuntimeError("No projects found in the GitLab group")

            total_projects = len(project_info)
            logger.info(f"Job {job_id}: Found {total_projects} projects to scan")

            # Initialize master status
            pending_repos = [p['name'] for p in project_info]
            job_monitor.update_master_status(
                job_id,
                group_url=group_url,
                total_repositories=total_projects,
                status="initializing",
                started_at=datetime.now(timezone.utc).isoformat(),
                pending_repositories=pending_repos
            )

            # Track processes
            self.active_processes[job_id] = []
            monitor_tasks = []

            # Process repositories with concurrency limit
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_PROCESSES)

            async def scan_project(index: int, project: Dict[str, Any]):
                """Scan a single project with semaphore control."""
                async with semaphore:
                    project_name = project['name']
                    git_url = project['git_url']

                    if not git_url:
                        logger.warning(f"Job {job_id}: Skipping project {project_name} - no git URL")
                        return

                    logger.info(f"Job {job_id}: Starting scan [{index+1}/{total_projects}]: {project_name}")

                    try:
                        # Spawn subprocess
                        process = await self._spawn_scanner_subprocess(
                            job_id, index, project_name, git_url
                        )

                        self.active_processes[job_id].append(process)

                        # Monitor subprocess
                        await job_monitor.monitor_subprocess(
                            job_id, process, index, self.SUBPROCESS_TIMEOUT
                        )

                    except Exception as e:
                        logger.error(f"Job {job_id}: Failed to scan project {project_name}: {e}")
                        # Write failed status for this repository
                        repo_file = Path(f"tmp/scan_jobs/{job_id}/repo_{index}.json")
                        job_monitor._write_failed_status(
                            repo_file, index, f"Failed to start subprocess: {str(e)}", ""
                        )

            # Create tasks for all projects
            scan_tasks = [
                scan_project(i, project)
                for i, project in enumerate(project_info)
            ]

            # Progress monitoring task
            async def monitor_progress():
                """Monitor overall progress and update job status."""
                while True:
                    await asyncio.sleep(5)  # Check every 5 seconds

                    status = await job_monitor.get_job_status(job_id)
                    summary = status.get("summary", {})

                    completed = summary.get("completed", 0)
                    failed = summary.get("failed", 0)
                    done = completed + failed

                    if done >= total_projects:
                        job_manager.update_job_status(job_id, JobStatus.RUNNING, 95)
                        break
                    else:
                        # Calculate progress
                        progress = 10 + int((done / total_projects) * 85)
                        job_manager.update_job_status(job_id, JobStatus.RUNNING, progress)

            progress_task = asyncio.create_task(monitor_progress())

            # Run all scans
            await asyncio.gather(*scan_tasks, return_exceptions=True)

            # Cancel progress monitoring
            progress_task.cancel()

            # Get final aggregated status
            final_status = await job_monitor.get_job_status(job_id)

            # Transform results for API response
            result = self._transform_subprocess_results_group(group_url, final_status, project_info)
            job_manager.set_job_result(job_id, result)

            # Update master status
            summary = final_status.get("summary", {})
            final_job_status = "completed" if summary.get("failed", 0) == 0 else "completed_with_errors"

            job_monitor.update_master_status(
                job_id,
                status=final_job_status,
                completed_at=datetime.now(timezone.utc).isoformat()
            )

            job_manager.update_job_status(job_id, JobStatus.RUNNING, 100)
            logger.info(f"Job {job_id}: Group scan completed - {summary.get('completed', 0)} succeeded, {summary.get('failed', 0)} failed")

        except Exception as e:
            logger.error(f"Group scan failed for job {job_id}: {e}")
            raise

    async def _spawn_scanner_subprocess(self, job_id: str, repo_index: int,
                                       repo_name: str, git_url: str) -> asyncio.subprocess.Process:
        """Spawn a scanner worker subprocess.

        Args:
            job_id: Job identifier
            repo_index: Repository index
            repo_name: Repository name
            git_url: Repository URL

        Returns:
            Subprocess handle
        """
        cmd = [
            sys.executable,
            "-m", "dependency_scanner_tool.api.scanner_worker",
            job_id,
            str(repo_index),
            repo_name,
            git_url
        ]

        logger.info(f"Spawning scanner subprocess: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        logger.info(f"Subprocess spawned with PID {process.pid} for repo {repo_name}")
        return process

    async def _cleanup_job_processes(self, job_id: str) -> None:
        """Clean up any remaining processes for a job.

        Args:
            job_id: Job identifier
        """
        if job_id not in self.active_processes:
            return

        processes = self.active_processes[job_id]
        for process in processes:
            if process.returncode is None:
                logger.warning(f"Terminating still-running process {process.pid}")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    logger.warning(f"Force killing process {process.pid}")
                    process.kill()
                    await process.wait()

        del self.active_processes[job_id]
        logger.info(f"Cleaned up processes for job {job_id}")

    def _transform_subprocess_results_single(self, git_url: str, status: Dict[str, Any]) -> ScanResultResponse:
        """Transform subprocess status to API response for single repository.

        Args:
            git_url: Repository URL
            status: Aggregated status from job monitor

        Returns:
            API response object
        """
        # For single repository, we'll use simplified results
        # In production, you'd read actual scan results from a results file
        dependencies = {}
        infrastructure_usage = {}

        # Check if scan completed successfully
        if status.get("status") in ["completed", "completed_with_errors"]:
            # Here you would read actual results from a results file
            # For now, returning empty results
            pass

        return ScanResultResponse(
            git_url=git_url,
            dependencies=dependencies,
            infrastructure_usage=infrastructure_usage,
            scan_type="repository",
            total_projects=None,
            successful_scans=None,
            failed_scans=None,
            project_results=None,
            failed_projects=None
        )

    def _transform_subprocess_results_group(self, group_url: str, status: Dict[str, Any],
                                           project_info: List[Dict]) -> ScanResultResponse:
        """Transform subprocess status to API response for group scan.

        Args:
            group_url: GitLab group URL
            status: Aggregated status from job monitor
            project_info: Original project information

        Returns:
            API response object
        """
        summary = status.get("summary", {})

        # Build project results
        project_results = []
        completed_repos = status.get("completed_repositories", [])
        failed_repos = status.get("failed_repositories", [])

        for project in project_info:
            project_name = project['name']
            git_url = project['git_url']

            if project_name in completed_repos:
                # Successful scan - in production, read actual results
                project_results.append(ProjectScanResult(
                    project_name=project_name,
                    git_url=git_url,
                    dependencies={},  # Would be populated from results file
                    infrastructure_usage={},
                    status="success",
                    error=None
                ))
            elif any(f.get("repo_name") == project_name for f in failed_repos if isinstance(f, dict)):
                # Failed scan
                error = next((f.get("error") for f in failed_repos
                            if isinstance(f, dict) and f.get("repo_name") == project_name), "Unknown error")
                project_results.append(ProjectScanResult(
                    project_name=project_name,
                    git_url=git_url,
                    dependencies={},
                    infrastructure_usage={},
                    status="failed",
                    error=error
                ))

        # Aggregate dependencies and infrastructure (simplified)
        group_dependencies = {}
        group_infrastructure = {}

        return ScanResultResponse(
            git_url=group_url,
            dependencies=group_dependencies,
            infrastructure_usage=group_infrastructure,
            scan_type="group",
            total_projects=summary.get("total_repositories", 0),
            successful_scans=summary.get("completed", 0),
            failed_scans=summary.get("failed", 0),
            project_results=project_results,
            failed_projects=[
                {
                    'project_name': f.get("repo_name", "unknown"),
                    'git_url': "",
                    'error': f.get("error", "Unknown error")
                } for f in failed_repos if isinstance(f, dict)
            ]
        )

    def is_service_ready(self) -> bool:
        """Check if the scanner service is ready to accept jobs.

        Returns:
            True if service is ready
        """
        return job_lifecycle_manager.can_create_job()


# Global scanner service instance
scanner_service = ScannerService()