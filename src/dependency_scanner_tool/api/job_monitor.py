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

from dependency_scanner_tool.api.constants import (
    JOB_MONITOR_STALE_THRESHOLD,
    JOB_MONITOR_CLEANUP_AGE_HOURS
)

logger = logging.getLogger(__name__)


class JobMonitor:
    """Monitors and aggregates status for subprocess-based scan jobs."""

    # Status directory base
    STATUS_DIR_BASE = Path("tmp/scan_jobs")

    # Stale status threshold in seconds
    STALE_THRESHOLD = JOB_MONITOR_STALE_THRESHOLD

    # Old job cleanup age in hours
    CLEANUP_AGE_HOURS = JOB_MONITOR_CLEANUP_AGE_HOURS

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
        in_progress = [r for r in repos if r.get("status") in ["starting", "downloading", "extracting", "cloning", "scanning", "analyzing"]]
        initializing = [r for r in repos if r.get("status") == "initializing"]

        # Calculate total repositories
        total_repos = master.get("total_repositories", len(repos))

        # Calculate pending (repos that haven't started yet)
        pending_count = max(0, total_repos - len(completed) - len(failed) - len(in_progress) - len(initializing))

        # Determine overall job status
        overall_status = self._determine_overall_status(
            master, completed, failed, in_progress, pending_count, total_repos
        )

        # Calculate elapsed time (use current time as fallback per architecture)
        started_at = master.get("started_at")
        if started_at:
            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        else:
            # Use current time as fallback (as shown in architecture line 241)
            elapsed = 0  # Will be 0 since time.time() - time.time() = 0

        # Get last update time and ensure ISO format
        last_updates = []
        for r in repos:
            update = r.get("last_update")
            if update:
                # Ensure it's in ISO format
                if isinstance(update, (int, float)):
                    # Convert timestamp to ISO format
                    last_updates.append(datetime.fromtimestamp(update, timezone.utc).isoformat())
                else:
                    last_updates.append(update)

        # Get the most recent update
        if last_updates:
            # Sort ISO timestamps and get the latest
            last_update = max(last_updates)
        else:
            last_update = datetime.now(timezone.utc).isoformat()

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

        # Add normalized detailed repository list with progress where available
        if repos:
            repositories: List[Dict[str, Any]] = []
            for repo in repos:
                repo_detail: Dict[str, Any] = {
                    "repo_index": repo.get("repo_index"),
                    "repo_name": repo.get("repo_name"),
                    "status": repo.get("status"),
                    "started_at": repo.get("started_at"),
                }

                # Normalize per-repo last_update to ISO string if present
                per_update = repo.get("last_update")
                if per_update is not None:
                    if isinstance(per_update, (int, float)):
                        repo_detail["last_update"] = datetime.fromtimestamp(per_update, timezone.utc).isoformat()
                    else:
                        repo_detail["last_update"] = per_update

                # Include progress information if available
                if repo.get("total_files") is not None:
                    total_files = repo.get("total_files") or 0
                    current_file = repo.get("current_file", 0)
                    percentage = repo.get("percentage")
                    if percentage is None and total_files > 0:
                        percentage = (current_file / total_files) * 100

                    progress: Dict[str, Any] = {
                        "total_files": total_files,
                        "current_file": current_file,
                        "percentage": percentage or 0,
                    }
                    if repo.get("current_filename"):
                        progress["current_file_name"] = repo.get("current_filename")
                    repo_detail["progress"] = progress
                elif repo.get("download_bytes") is not None:
                    # Download progress
                    download_bytes = repo.get("download_bytes", 0)
                    download_mb = download_bytes / (1024 * 1024)
                    repo_detail["progress"] = {
                        "download_bytes": download_bytes,
                        "download_mb": round(download_mb, 1),
                        "message": repo.get("message", f"Downloading: {download_mb:.1f} MB")
                    }
                elif repo.get("files_extracted") is not None:
                    # Extraction progress
                    files_extracted = repo.get("files_extracted", 0)
                    total_extraction_files = repo.get("total_extraction_files", 0)
                    extraction_percentage = repo.get("extraction_percentage", 0)
                    repo_detail["progress"] = {
                        "files_extracted": files_extracted,
                        "total_extraction_files": total_extraction_files,
                        "percentage": extraction_percentage,
                        "message": repo.get("message", f"Extracting: {files_extracted:,} / {total_extraction_files:,} files")
                    }
                elif repo.get("message"):
                    repo_detail["progress"] = {"message": repo.get("message")}

                repositories.append(repo_detail)

            response["repositories"] = repositories

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
                if repo.get("total_files") is not None:
                    total_files = repo.get("total_files", 0)
                    current_file = repo.get("current_file", 0)
                    # Calculate percentage if not provided (per architecture)
                    percentage = repo.get("percentage")
                    if percentage is None and total_files and total_files > 0:
                        percentage = ((current_file / total_files) * 100)

                    progress = {
                        "total_files": total_files,
                        "current_file": current_file,
                        "percentage": percentage or 0
                    }
                    if repo.get("current_filename"):
                        progress["current_file_name"] = repo.get("current_filename")
                    repo_info["progress"] = progress
                elif repo.get("download_bytes") is not None:
                    # Download progress
                    download_bytes = repo.get("download_bytes", 0)
                    download_mb = download_bytes / (1024 * 1024)
                    repo_info["progress"] = {
                        "download_bytes": download_bytes,
                        "download_mb": round(download_mb, 1),
                        "message": repo.get("message", f"Downloading: {download_mb:.1f} MB")
                    }
                elif repo.get("files_extracted") is not None:
                    # Extraction progress
                    files_extracted = repo.get("files_extracted", 0)
                    total_extraction_files = repo.get("total_extraction_files", 0)
                    extraction_percentage = repo.get("extraction_percentage", 0)
                    repo_info["progress"] = {
                        "files_extracted": files_extracted,
                        "total_extraction_files": total_extraction_files,
                        "percentage": extraction_percentage,
                        "message": repo.get("message", f"Extracting: {files_extracted:,} / {total_extraction_files:,} files")
                    }
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

        # Add pending repositories list (always include per architecture)
        # First check if master has the list
        pending_repos = master.get("pending_repositories", [])
        if pending_repos:
            response["pending_repositories"] = pending_repos[:pending_count]
        elif pending_count > 0:
            # If no list in master but we know there are pending repos,
            # create placeholder list per architecture requirements
            response["pending_repositories"] = [
                f"Repository {i+1} (pending)"
                for i in range(pending_count)
            ]

        return response

    def _determine_overall_status(self, master: Dict, completed: List, failed: List,
                                 in_progress: List, _pending: int, total: int) -> str:
        """Determine overall job status.

        Args:
            master: Master status dictionary
            completed: List of completed repositories
            failed: List of failed repositories
            in_progress: List of in-progress repositories
            _pending: Number of pending repositories (unused, derived from total)
            total: Total number of repositories

        Returns:
            Overall status string
        """
        # Check master status first - master status takes precedence
        master_status = master.get("status")
        normalized_master = master_status.lower() if isinstance(master_status, str) else None
        final_master_states = {"completed", "completed_with_errors", "all_failed", "failed", "timeout", "cancelled"}

        if normalized_master in final_master_states:
            return normalized_master

        # If all repos are done (completed or failed) but master status is not final,
        # return "processing" to indicate we're aggregating results
        # This prevents clients from seeing "completed" before job_manager is updated
        if len(completed) + len(failed) >= total:
            # All subprocess work is done, but scanner_service is still processing
            return "processing"

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
        master_status["job_id"] = job_id  # Always ensure job_id is present
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

            # Update master.json after subprocess completes
            await self._update_repository_completion(job_id, repo_index)

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

            # Update master.json after timeout
            await self._update_repository_completion(job_id, repo_index)

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

    async def _update_repository_completion(self, job_id: str, repo_index: int) -> None:
        """Update master.json when a repository completes or fails.

        Args:
            job_id: Job identifier
            repo_index: Repository index that completed
        """
        try:
            # Read the repo status to determine completion status
            repo_file = self.STATUS_DIR_BASE / job_id / f"repo_{repo_index}.json"
            if not repo_file.exists():
                logger.warning(f"Repo status file not found for job {job_id}, repo {repo_index}")
                return

            with open(repo_file, 'r') as f:
                repo_status = json.load(f)

            repo_name = repo_status.get("repo_name", f"Repository {repo_index}")
            status = repo_status.get("status")

            # Read current master status
            master_file = self.STATUS_DIR_BASE / job_id / "master.json"
            master_data = {}
            if master_file.exists():
                with open(master_file, 'r') as f:
                    master_data = json.load(f)

            # Initialize lists if not present
            pending = master_data.get("pending_repositories", [])
            completed = master_data.get("completed_repositories", [])
            failed = master_data.get("failed_repositories", [])

            # Remove from pending if present
            if repo_name in pending:
                pending.remove(repo_name)

            # Add to appropriate list based on status
            if status == "completed":
                if repo_name not in completed:
                    completed.append(repo_name)
                    logger.info(f"Repository {repo_name} completed for job {job_id}")
            elif status in ["failed", "timeout"]:
                # For failed repos, store as dict with error info
                failed_info = {
                    "repo_name": repo_name,
                    "error": repo_status.get("error_message", "Unknown error"),
                    "status": status
                }
                # Check if already in failed list
                existing_failed = [f for f in failed if isinstance(f, dict) and f.get("repo_name") == repo_name]
                if not existing_failed:
                    failed.append(failed_info)
                    logger.info(f"Repository {repo_name} failed for job {job_id}")

            # Update master status with new lists
            self.update_master_status(
                job_id,
                pending_repositories=pending,
                completed_repositories=completed,
                failed_repositories=failed
            )

            logger.debug(f"Updated master.json for job {job_id}: {len(pending)} pending, {len(completed)} completed, {len(failed)} failed")

        except Exception as e:
            logger.error(f"Failed to update repository completion for job {job_id}, repo {repo_index}: {e}")
            # Don't raise - this is a non-critical update


# Global job monitor instance
job_monitor = JobMonitor()
