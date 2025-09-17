"""Job monitoring system for subprocess-based scanning.

This module provides filesystem-based monitoring of scan jobs,
aggregating status from multiple subprocess workers.
"""

import json
import time
import shutil
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JobMonitor:
    """Monitors and aggregates status for subprocess-based scan jobs."""

    # Status directory base
    STATUS_DIR_BASE = Path("tmp/scan_jobs")

    # Stale status threshold in seconds (2 minutes)
    STALE_THRESHOLD = 120

    # Old job cleanup age in hours
    CLEANUP_AGE_HOURS = 24

    def __init__(self):
        """Initialize job monitor."""
        self.STATUS_DIR_BASE.mkdir(parents=True, exist_ok=True)
        logger.info(f"Job monitor initialized with base dir: {self.STATUS_DIR_BASE}")

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get aggregated status for a job.

        Args:
            job_id: Job identifier

        Returns:
            Aggregated job status dictionary
        """
        job_dir = self.STATUS_DIR_BASE / job_id

        if not job_dir.exists():
            logger.warning(f"Job directory not found: {job_dir}")
            return {
                "job_id": job_id,
                "status": "not_found",
                "error": "Job not found"
            }

        try:
            # Read master status file if it exists
            master_file = job_dir / "master.json"
            master_status = {}
            if master_file.exists():
                with open(master_file, 'r') as f:
                    master_status = json.load(f)

            # Read all repository status files
            repo_statuses = []
            for repo_file in sorted(job_dir.glob("repo_*.json")):
                try:
                    with open(repo_file, 'r') as f:
                        repo_status = json.load(f)
                        repo_statuses.append(repo_status)
                except Exception as e:
                    logger.error(f"Failed to read status file {repo_file}: {e}")

            # Aggregate status information
            return self._aggregate_status(job_id, master_status, repo_statuses)

        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return {
                "job_id": job_id,
                "status": "error",
                "error": f"Failed to read status: {str(e)}"
            }

    def _aggregate_status(self, job_id: str, master: Dict, repos: List[Dict]) -> Dict[str, Any]:
        """Aggregate status from master and repository files.

        Args:
            job_id: Job identifier
            master: Master status dictionary
            repos: List of repository status dictionaries

        Returns:
            Aggregated status dictionary
        """
        # Categorize repositories by status
        completed = [r for r in repos if r.get("status") == "completed"]
        failed = [r for r in repos if r.get("status") == "failed"]
        in_progress = [r for r in repos if r.get("status") in ["starting", "cloning", "scanning", "analyzing"]]
        initializing = [r for r in repos if r.get("status") == "initializing"]

        # Calculate total repositories
        total_repos = master.get("total_repositories", len(repos))

        # Calculate pending (repos that haven't started yet)
        pending_count = max(0, total_repos - len(completed) - len(failed) - len(in_progress) - len(initializing))

        # Determine overall job status
        overall_status = self._determine_overall_status(
            master, completed, failed, in_progress, pending_count, total_repos
        )

        # Calculate elapsed time
        started_at = master.get("started_at")
        if started_at:
            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        else:
            elapsed = 0

        # Get last update time
        last_updates = [r.get("last_update") for r in repos if r.get("last_update")]
        last_update = max(last_updates) if last_updates else None

        # Build response
        response = {
            "job_id": job_id,
            "status": overall_status,
            "group_url": master.get("group_url"),
            "summary": {
                "total_repositories": total_repos,
                "completed": len(completed),
                "in_progress": len(in_progress),
                "pending": pending_count,
                "failed": len(failed)
            },
            "elapsed_time_seconds": elapsed,
            "last_update": last_update
        }

        # Add current repositories with progress details
        if in_progress:
            response["current_repositories"] = []
            for repo in in_progress:
                repo_info = {
                    "repo_name": repo.get("repo_name"),
                    "status": repo.get("status"),
                    "started_at": repo.get("started_at")
                }

                # Add progress information if available
                if repo.get("total_files"):
                    progress = {
                        "total_files": repo.get("total_files"),
                        "current_file": repo.get("current_file", 0),
                        "percentage": repo.get("percentage", 0)
                    }
                    if repo.get("current_filename"):
                        progress["current_file_name"] = repo.get("current_filename")
                    repo_info["progress"] = progress
                elif repo.get("message"):
                    repo_info["progress"] = {"message": repo.get("message")}

                response["current_repositories"].append(repo_info)

        # Add completed/failed repository lists
        if completed:
            response["completed_repositories"] = [
                r.get("repo_name") for r in completed
            ]

        if failed:
            response["failed_repositories"] = []
            for repo in failed:
                fail_info = {
                    "repo_name": repo.get("repo_name"),
                    "error": repo.get("error_message", "Unknown error")
                }
                if repo.get("errors") and len(repo["errors"]) > 0:
                    fail_info["error"] = repo["errors"][0].get("message", fail_info["error"])
                response["failed_repositories"].append(fail_info)

        # Add pending repositories if available from master
        pending_repos = master.get("pending_repositories", [])
        if pending_repos:
            response["pending_repositories"] = pending_repos[:pending_count]

        return response

    def _determine_overall_status(self, master: Dict, completed: List, failed: List,
                                 in_progress: List, pending: int, total: int) -> str:
        """Determine overall job status.

        Args:
            master: Master status dictionary
            completed: List of completed repositories
            failed: List of failed repositories
            in_progress: List of in-progress repositories
            pending: Number of pending repositories
            total: Total number of repositories

        Returns:
            Overall status string
        """
        # Check master status first
        master_status = master.get("status")
        if master_status in ["failed", "timeout", "cancelled"]:
            return master_status

        # If all repos are done (completed or failed)
        if len(completed) + len(failed) >= total:
            if len(failed) == 0:
                return "completed"
            elif len(failed) == total:
                return "all_failed"
            else:
                return "completed_with_errors"

        # If work is in progress
        if in_progress:
            return "in_progress"

        # If we have some results but waiting for more
        if completed or failed:
            return "in_progress"

        # Just starting
        return "initializing"

    def update_master_status(self, job_id: str, **kwargs) -> None:
        """Update master status file for a job.

        Args:
            job_id: Job identifier
            **kwargs: Status fields to update
        """
        job_dir = self.STATUS_DIR_BASE / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        master_file = job_dir / "master.json"

        # Read existing or create new
        master_status = {}
        if master_file.exists():
            try:
                with open(master_file, 'r') as f:
                    master_status = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read master status: {e}")

        # Update fields
        master_status.update(kwargs)
        master_status["last_aggregation"] = datetime.now(timezone.utc).isoformat()

        # Write atomically
        try:
            temp_file = master_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(master_status, f, indent=2, default=str)
            temp_file.replace(master_file)
            logger.debug(f"Updated master status for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to write master status: {e}")
            raise RuntimeError(f"Master status write failed: {e}")

    def is_status_stale(self, status: Dict[str, Any]) -> bool:
        """Check if a status hasn't been updated recently.

        Args:
            status: Status dictionary with last_update field

        Returns:
            True if status is stale
        """
        last_update_str = status.get("last_update")
        if not last_update_str:
            return True

        try:
            last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - last_update).total_seconds()
            return age > self.STALE_THRESHOLD
        except Exception as e:
            logger.warning(f"Failed to parse last_update: {e}")
            return True

    async def monitor_subprocess(self, job_id: str, process: asyncio.subprocess.Process,
                                repo_index: int, timeout: Optional[int] = 3600) -> None:
        """Monitor a subprocess and update status on completion.

        Args:
            job_id: Job identifier
            process: Subprocess to monitor
            repo_index: Repository index
            timeout: Maximum time to wait in seconds
        """
        try:
            # Wait for process with timeout
            if timeout:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            else:
                await process.wait()

            returncode = process.returncode
            logger.info(f"Subprocess for job {job_id}, repo {repo_index} exited with code {returncode}")

            # Check if process failed
            if returncode != 0:
                # Read stderr if available
                stderr_data = None
                if process.stderr:
                    stderr_data = await process.stderr.read()
                    stderr_text = stderr_data.decode() if stderr_data else ""
                else:
                    stderr_text = ""

                # Update repo status file to ensure it shows failed
                repo_file = self.STATUS_DIR_BASE / job_id / f"repo_{repo_index}.json"
                if not repo_file.exists() or self._should_update_failed_status(repo_file):
                    self._write_failed_status(
                        repo_file,
                        repo_index,
                        f"Process exited with code {returncode}",
                        stderr_text
                    )

        except asyncio.TimeoutError:
            logger.error(f"Subprocess timeout for job {job_id}, repo {repo_index}")
            # Kill the process
            process.kill()
            await process.wait()

            # Write timeout status
            repo_file = self.STATUS_DIR_BASE / job_id / f"repo_{repo_index}.json"
            self._write_failed_status(
                repo_file,
                repo_index,
                f"Process killed after {timeout} seconds timeout",
                ""
            )

        except Exception as e:
            logger.error(f"Error monitoring subprocess for job {job_id}, repo {repo_index}: {e}")

    def _should_update_failed_status(self, repo_file: Path) -> bool:
        """Check if a failed status file needs updating.

        Args:
            repo_file: Path to repository status file

        Returns:
            True if file should be updated
        """
        try:
            with open(repo_file, 'r') as f:
                status = json.load(f)
                # Don't overwrite if already has detailed error
                return status.get("status") not in ["failed", "timeout"]
        except:
            return True

    def _write_failed_status(self, repo_file: Path, repo_index: int,
                           error_message: str, stderr: str) -> None:
        """Write a failed status file for a repository.

        Args:
            repo_file: Path to status file
            repo_index: Repository index
            error_message: Error message
            stderr: Standard error output
        """
        status = {
            "repo_index": repo_index,
            "status": "failed",
            "error_message": error_message,
            "stderr": stderr,
            "last_update": datetime.now(timezone.utc).isoformat(),
            "errors": [{
                "message": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }

        try:
            repo_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = repo_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(status, f, indent=2)
            temp_file.replace(repo_file)
        except Exception as e:
            logger.error(f"Failed to write failed status: {e}")

    async def cleanup_old_jobs(self, age_hours: Optional[int] = None) -> int:
        """Remove old job directories.

        Args:
            age_hours: Age in hours after which to remove jobs

        Returns:
            Number of jobs cleaned up
        """
        if age_hours is None:
            age_hours = self.CLEANUP_AGE_HOURS

        cutoff_time = time.time() - (age_hours * 3600)
        cleaned = 0

        try:
            for job_dir in self.STATUS_DIR_BASE.iterdir():
                if not job_dir.is_dir():
                    continue

                # Check master file for completion time
                master_file = job_dir / "master.json"
                should_cleanup = False

                if master_file.exists():
                    try:
                        with open(master_file, 'r') as f:
                            master = json.load(f)
                            completed_at = master.get("completed_at")
                            if completed_at:
                                completed_time = datetime.fromisoformat(
                                    completed_at.replace('Z', '+00:00')
                                ).timestamp()
                                should_cleanup = completed_time < cutoff_time
                    except Exception as e:
                        logger.warning(f"Failed to read master file for cleanup check: {e}")
                else:
                    # No master file, check directory modification time
                    dir_mtime = job_dir.stat().st_mtime
                    should_cleanup = dir_mtime < cutoff_time

                if should_cleanup:
                    try:
                        shutil.rmtree(job_dir)
                        logger.info(f"Cleaned up old job directory: {job_dir}")
                        cleaned += 1
                    except Exception as e:
                        logger.error(f"Failed to cleanup job directory {job_dir}: {e}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old job directories")

        return cleaned


# Global job monitor instance
job_monitor = JobMonitor()