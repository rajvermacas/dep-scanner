#!/usr/bin/env python3
"""Scanner worker subprocess for CPU-bound repository scanning.

This module runs as a separate subprocess to perform repository scanning
without blocking the FastAPI worker's event loop. It writes status updates
to filesystem-based JSON files for monitoring.
"""

import os
import sys
import json
import time
import logging
import argparse
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dependency_scanner_tool.scanner import DependencyScanner
from dependency_scanner_tool.api.git_service import repository_service
from dependency_scanner_tool.api.validation import validate_git_url
from dependency_scanner_tool.file_utils import get_config_path
from dependency_scanner_tool.api.constants import (
    WORKER_STATUS_UPDATE_INTERVAL,
    WORKER_PROGRESS_UPDATE_INTERVAL
)


# Logging configuration
LOG_DIR_ENV_VAR = "SCAN_JOB_LOG_DIR"
DEFAULT_LOG_DIR_BASE = Path("tmp/scan_logs")


def setup_worker_logging(job_id: str) -> Path:
    """Configure logging to capture output in a job-specific file."""
    base_dir_raw = os.getenv(LOG_DIR_ENV_VAR)
    base_dir = Path(base_dir_raw) if base_dir_raw else DEFAULT_LOG_DIR_BASE
    job_dir = base_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    log_path = job_dir / f"{os.getpid()}.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding='utf-8')
        ],
        force=True,
    )

    return log_path


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)


class ScannerWorker:
    """Worker class for scanning repositories in a subprocess."""

    # Status update interval in seconds
    UPDATE_INTERVAL = WORKER_STATUS_UPDATE_INTERVAL

    # Minimum interval between progress writes in seconds
    PROGRESS_UPDATE_INTERVAL = WORKER_PROGRESS_UPDATE_INTERVAL

    # Status file directory base
    STATUS_DIR_BASE = Path("tmp/scan_jobs")

    def __init__(self, job_id: str, repo_index: int, repo_name: str):
        """Initialize scanner worker.

        Args:
            job_id: Unique job identifier
            repo_index: Index of this repository in the scan job
            repo_name: Name or URL of the repository
        """
        self.job_id = job_id
        self.repo_index = repo_index
        self.repo_name = repo_name
        self.scanner = DependencyScanner()

        # Status tracking
        self.status: Dict[str, Any] = {
            "repo_index": repo_index,
            "repo_name": repo_name,
            "status": "initializing",
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "errors": []
        }
        self.last_update_time = 0

        # Setup status file path
        self.job_dir = self.STATUS_DIR_BASE / job_id
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.status_file = self.job_dir / f"repo_{repo_index}.json"

        logger.info(f"Worker initialized for job {job_id}, repo {repo_index}: {repo_name}")

    def update_status(self, force: bool = False, **kwargs) -> None:
        """Update status and write to file if needed.

        Args:
            force: Force immediate write regardless of interval
            **kwargs: Status fields to update
        """
        # Update in-memory status
        self.status.update(kwargs)
        self.status["last_update"] = datetime.now(timezone.utc).isoformat()

        # Check if we should write to file
        current_time = time.time()
        time_since_update = current_time - self.last_update_time

        # Determine if progress-specific fields changed and sufficient time elapsed
        progress_fields = {"current_file", "current_filename", "percentage"}
        progress_update = (
            any(field in kwargs for field in progress_fields)
            and time_since_update >= self.PROGRESS_UPDATE_INTERVAL
        )

        # Write on: force, interval elapsed, key state changes, or timed progress update
        should_write = (
            force or
            time_since_update >= self.UPDATE_INTERVAL or
            kwargs.get("status") in ["completed", "failed", "starting", "downloading", "cloning", "scanning"] or
            progress_update
        )

        if should_write:
            self._write_status_file()
            self.last_update_time = current_time
            logger.debug(f"Status updated for repo {self.repo_index}: {kwargs.get('status', self.status['status'])}")

    def _write_status_file(self) -> None:
        """Atomically write status to file."""
        try:
            # Write to temporary file first
            temp_file = self.status_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.status, f, indent=2, default=str)

            # Atomic rename (on most filesystems)
            temp_file.replace(self.status_file)

        except Exception as e:
            logger.error(f"Failed to write status file: {e}")
            # Fail fast - if we can't write status, something is wrong
            raise RuntimeError(f"Status file write failed: {e}")

    def fail_with_error(self, error_message: str, exception: Optional[Exception] = None) -> None:
        """Mark scan as failed and exit.

        Args:
            error_message: Human-readable error message
            exception: Optional exception object for details
        """
        error_details = {
            "message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if exception:
            error_details["exception"] = str(exception)
            error_details["traceback"] = traceback.format_exc()

        self.status["errors"].append(error_details)
        self.update_status(
            status="failed",
            error_message=error_message,
            force=True
        )

        logger.error(f"Scan failed for repo {self.repo_index}: {error_message}")
        if exception:
            logger.error(f"Exception details: {exception}")

        # Exit with error code
        sys.exit(1)

    def scan_repository(self, git_url: str) -> None:
        """Scan a single repository.

        Args:
            git_url: URL of the repository to scan
        """
        repo_path = None

        try:
            # Update status: starting
            self.update_status(
                status="starting",
                git_url=git_url,
                force=True
            )

            # Validate URL
            logger.info(f"Validating Git URL: {git_url}")
            validated_url = validate_git_url(git_url)

            # Update status: downloading
            self.update_status(
                status="downloading",
                message="Downloading ZIP file...",
                download_bytes=0,
                force=True
            )

            # Create download progress callback
            def on_download_progress(bytes_downloaded: int) -> None:
                """Update status with download progress."""
                # Format bytes as MB for readability
                mb_downloaded = bytes_downloaded / (1024 * 1024)
                self.update_status(
                    status="downloading",
                    download_bytes=bytes_downloaded,
                    message=f"Downloading ZIP: {mb_downloaded:.1f} MB downloaded"
                )

            # Download repository with progress tracking
            logger.info(f"Downloading repository: {validated_url}")
            repo_path = repository_service.download_repository(validated_url, progress_callback=on_download_progress)

            # Validate downloaded repository
            if not repository_service.validate_repository(repo_path):
                raise RuntimeError("Invalid or corrupted repository")

            # Update status: scanning
            self.update_status(
                status="scanning",
                message="Analyzing dependencies...",
                repo_path=str(repo_path),
                force=True
            )

            # Get total files for progress tracking
            total_files = self._count_files(repo_path)
            self.update_status(
                total_files=total_files,
                current_file=0,
                percentage=0,
                force=True
            )

            # Perform scan with progress updates
            logger.info(f"Scanning repository at: {repo_path}")
            scan_result = self._scan_with_progress(repo_path, total_files)

            # Process results and categorize dependencies
            dependencies_found = len(scan_result.dependencies) if scan_result else 0
            api_calls_found = len(scan_result.api_calls) if hasattr(scan_result, 'api_calls') and scan_result.api_calls else 0

            # Categorize dependencies for the API response format
            categorized_dependencies = self._categorize_dependencies(scan_result)
            infrastructure_usage = scan_result.infrastructure_usage if hasattr(scan_result, 'infrastructure_usage') else {}

            # Update status: completed
            self.update_status(
                status="completed",
                dependencies_found=dependencies_found,
                api_calls_found=api_calls_found,
                scan_result={
                    "dependencies": dependencies_found,
                    "api_calls": api_calls_found,
                    "source_files": len(scan_result.source_files) if hasattr(scan_result, 'source_files') else 0,
                    "categorized_dependencies": categorized_dependencies,
                    "infrastructure_usage": infrastructure_usage
                },
                completed_at=datetime.now(timezone.utc).isoformat(),
                force=True
            )

            logger.info(f"✅ Repository scan completed: {self.repo_name}")
            logger.info(f"   Dependencies found: {dependencies_found}")
            logger.info(f"   API calls found: {api_calls_found}")

        except Exception as e:
            self.fail_with_error(f"Scan failed: {str(e)}", e)

        finally:
            # Always cleanup repository
            if repo_path:
                try:
                    repository_service.cleanup_repository(repo_path)
                    logger.debug(f"Cleaned up repository at {repo_path}")
                except Exception as cleanup_e:
                    logger.warning(f"Failed to cleanup repository: {cleanup_e}")

    def _count_files(self, repo_path: Path) -> int:
        """Count total files in repository for progress tracking.

        Args:
            repo_path: Path to repository

        Returns:
            Total number of files
        """
        try:
            count = sum(1 for _ in Path(repo_path).rglob('*') if _.is_file())
            return max(count, 1)  # At least 1 to avoid division by zero
        except Exception as e:
            logger.warning(f"Failed to count files: {e}")
            return 100  # Default estimate

    def _scan_with_progress(self, repo_path: Path, total_files: int) -> Any:
        """Perform scan with periodic progress updates.

        Args:
            repo_path: Path to repository
            total_files: Total number of files for progress calculation

        Returns:
            Scan result object
        """
        # This is a simplified version - in production, you'd hook into
        # the scanner's progress callbacks if available

        processed_files = 0
        observed_total = max(total_files, 1)

        def on_file_progress(file_path: str) -> None:
            nonlocal processed_files, observed_total
            try:
                processed_files += 1
                observed_total = max(observed_total, processed_files, 1)
                pct = (processed_files / observed_total) * 100

                try:
                    rel_name = str(Path(file_path).relative_to(repo_path))
                except Exception:
                    rel_name = file_path

                self.update_status(
                    current_file=processed_files,
                    total_files=observed_total,
                    percentage=pct,
                    current_filename=rel_name,
                    message="Analyzing dependencies..."
                )
            except Exception:
                logger.debug("Progress callback failed", exc_info=True)

        # Perform actual scan with progress callback
        scan_result = self.scanner.scan_project(
            str(repo_path),
            progress_callback=on_file_progress,
        )

        # Final progress update
        self.update_status(
            current_file=processed_files or observed_total,
            total_files=observed_total,
            percentage=100,
            current_filename=None,
            message="Analyzing results..."
        )

        return scan_result

    def _categorize_dependencies(self, scan_result: Any) -> Dict[str, bool]:
        """Categorize dependencies from scan result into category flags.

        Args:
            scan_result: Scan result object from DependencyScanner

        Returns:
            Dictionary mapping category names to boolean flags
        """
        from dependency_scanner_tool.categorization import DependencyCategorizer
        from pathlib import Path

        # Initialize categorizer with config if available
        categorizer = None
        config_env = os.getenv("CONFIG_PATH")
        config_path = Path(config_env) if config_env else Path(get_config_path())

        if config_path.exists():
            try:
                categorizer = DependencyCategorizer.from_yaml(config_path)
            except Exception as e:
                logger.warning(f"Failed to load categorizer config: {e}")

        if not categorizer:
            categorizer = DependencyCategorizer()

        # Initialize with all categories from config set to False
        category_flags = {}

        # First, add all categories from the config (all set to False initially)
        if categorizer.categories:
            for category in categorizer.categories.keys():
                category_flags[category] = False

        # Now check which categories have dependencies
        if scan_result and hasattr(scan_result, 'dependencies'):
            # Categorize each dependency and update flags
            categorized = categorizer.categorize_dependencies(scan_result.dependencies)

            # Update flags for categories that have dependencies
            for category, deps in categorized.items():
                # Only include categories that are in the config (skip "Uncategorized")
                if category in categorizer.categories:
                    category_flags[category] = len(deps) > 0

        return category_flags


def main():
    """Main entry point for scanner worker subprocess."""
    parser = argparse.ArgumentParser(description='Scanner worker subprocess')
    parser.add_argument('job_id', help='Job ID')
    parser.add_argument('repo_index', type=int, help='Repository index')
    parser.add_argument('repo_name', help='Repository name')
    parser.add_argument('git_url', help='Git URL to scan')

    args = parser.parse_args()

    log_path = setup_worker_logging(args.job_id)

    logger.info(f"Scanner worker started: job={args.job_id}, repo={args.repo_index}, url={args.git_url}")
    logger.info(f"Writing subprocess logs to {log_path}")

    # Create worker and run scan
    worker = ScannerWorker(args.job_id, args.repo_index, args.repo_name)

    try:
        worker.scan_repository(args.git_url)
        logger.info("Scanner worker completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scanner worker failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
