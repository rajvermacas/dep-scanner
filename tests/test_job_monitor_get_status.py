"""Comprehensive tests for JobMonitor.get_job_status method."""

import json
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
import shutil

from dependency_scanner_tool.api.job_monitor import JobMonitor


class TestGetJobStatus:
    """Test suite for JobMonitor.get_job_status method."""

    @pytest.fixture
    def job_monitor(self):
        """Create a JobMonitor instance with test directory."""
        monitor = JobMonitor()
        # Use test-specific directory
        monitor.STATUS_DIR_BASE = Path("tmp/scan_jobs_test")
        monitor.STATUS_DIR_BASE.mkdir(parents=True, exist_ok=True)
        yield monitor
        # Cleanup
        if monitor.STATUS_DIR_BASE.exists():
            shutil.rmtree(monitor.STATUS_DIR_BASE)

    @pytest.fixture
    def create_test_job(self, job_monitor):
        """Helper to create test job directories with status files."""
        def _create(job_id, master_data=None, repo_statuses=None):
            job_dir = job_monitor.STATUS_DIR_BASE / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            # Write master status if provided
            if master_data:
                master_file = job_dir / "master.json"
                with open(master_file, 'w') as f:
                    json.dump(master_data, f, indent=2)

            # Write repository status files
            if repo_statuses:
                for idx, repo_status in enumerate(repo_statuses):
                    repo_file = job_dir / f"repo_{idx}.json"
                    with open(repo_file, 'w') as f:
                        json.dump(repo_status, f, indent=2)

            return job_dir

        return _create

    @pytest.mark.asyncio
    async def test_job_not_found(self, job_monitor):
        """Test response when job directory doesn't exist."""
        result = await job_monitor.get_job_status("nonexistent-job")

        assert result["job_id"] == "nonexistent-job"
        assert result["status"] == "not_found"
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_basic_aggregation(self, job_monitor, create_test_job):
        """Test basic status aggregation from master and repo files."""
        job_id = "test-job-basic"
        started_at = datetime.now(timezone.utc) - timedelta(minutes=5)

        master_data = {
            "job_id": job_id,
            "group_url": "https://gitlab.com/test-group",
            "total_repositories": 5,
            "status": "in_progress",
            "started_at": started_at.isoformat()
        }

        repo_statuses = [
            {
                "repo_index": 0,
                "repo_name": "test-repo-1",
                "status": "completed",
                "last_update": datetime.now(timezone.utc).isoformat()
            },
            {
                "repo_index": 1,
                "repo_name": "test-repo-2",
                "status": "scanning",
                "total_files": 100,
                "current_file": 50,
                "current_filename": "src/main.py",
                "last_update": datetime.now(timezone.utc).isoformat(),
                "started_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "repo_index": 2,
                "repo_name": "test-repo-3",
                "status": "failed",
                "error_message": "Clone failed",
                "last_update": datetime.now(timezone.utc).isoformat()
            }
        ]

        create_test_job(job_id, master_data, repo_statuses)

        result = await job_monitor.get_job_status(job_id)

        # Check basic fields
        assert result["job_id"] == job_id
        assert result["status"] == "in_progress"
        assert result["group_url"] == "https://gitlab.com/test-group"

        # Check summary
        assert result["summary"]["total_repositories"] == 5
        assert result["summary"]["completed"] == 1
        assert result["summary"]["in_progress"] == 1
        assert result["summary"]["failed"] == 1
        assert result["summary"]["pending"] == 2  # 5 total - 1 completed - 1 in_progress - 1 failed

        # Check elapsed time is calculated
        assert "elapsed_time_seconds" in result
        assert result["elapsed_time_seconds"] > 0

        # Check last_update is ISO formatted
        assert "last_update" in result
        assert isinstance(result["last_update"], str)
        # Should be parseable as ISO datetime
        datetime.fromisoformat(result["last_update"].replace('Z', '+00:00'))

        # Check current repositories
        assert "current_repositories" in result
        assert len(result["current_repositories"]) == 1
        current_repo = result["current_repositories"][0]
        assert current_repo["repo_name"] == "test-repo-2"
        assert current_repo["status"] == "scanning"
        assert "progress" in current_repo
        assert current_repo["progress"]["total_files"] == 100
        assert current_repo["progress"]["current_file"] == 50
        assert current_repo["progress"]["percentage"] == 50.0  # Should be calculated

        # Check completed/failed lists
        assert result["completed_repositories"] == ["test-repo-1"]
        assert len(result["failed_repositories"]) == 1
        assert result["failed_repositories"][0]["repo_name"] == "test-repo-3"
        assert result["failed_repositories"][0]["error"] == "Clone failed"

    @pytest.mark.asyncio
    async def test_percentage_calculation(self, job_monitor, create_test_job):
        """Test that percentage is calculated if not provided."""
        job_id = "test-percentage"

        repo_statuses = [
            {
                "repo_index": 0,
                "repo_name": "test-repo",
                "status": "scanning",
                "total_files": 200,
                "current_file": 75,
                # Note: percentage NOT provided, should be calculated
                "last_update": datetime.now(timezone.utc).isoformat()
            }
        ]

        create_test_job(job_id, {}, repo_statuses)

        result = await job_monitor.get_job_status(job_id)

        assert "current_repositories" in result
        assert len(result["current_repositories"]) == 1
        progress = result["current_repositories"][0]["progress"]
        assert progress["percentage"] == 37.5  # (75/200) * 100

    @pytest.mark.asyncio
    async def test_pending_repositories_from_master(self, job_monitor, create_test_job):
        """Test pending repositories list when provided in master."""
        job_id = "test-pending-master"

        master_data = {
            "total_repositories": 5,
            "pending_repositories": [
                "repo-4",
                "repo-5",
                "repo-6"  # More than needed
            ]
        }

        repo_statuses = [
            {"repo_index": 0, "status": "completed"},
            {"repo_index": 1, "status": "completed"}
        ]

        create_test_job(job_id, master_data, repo_statuses)

        result = await job_monitor.get_job_status(job_id)

        # Should have 3 pending (5 total - 2 completed)
        assert result["summary"]["pending"] == 3
        assert "pending_repositories" in result
        assert result["pending_repositories"] == ["repo-4", "repo-5", "repo-6"]

    @pytest.mark.asyncio
    async def test_pending_repositories_placeholder(self, job_monitor, create_test_job):
        """Test pending repositories placeholder when not in master."""
        job_id = "test-pending-placeholder"

        master_data = {
            "total_repositories": 4
            # No pending_repositories list
        }

        repo_statuses = [
            {"repo_index": 0, "status": "completed"}
        ]

        create_test_job(job_id, master_data, repo_statuses)

        result = await job_monitor.get_job_status(job_id)

        # Should have 3 pending (4 total - 1 completed)
        assert result["summary"]["pending"] == 3
        assert "pending_repositories" in result
        # Should have placeholder names
        assert len(result["pending_repositories"]) == 3
        assert result["pending_repositories"][0] == "Repository 1 (pending)"
        assert result["pending_repositories"][1] == "Repository 2 (pending)"
        assert result["pending_repositories"][2] == "Repository 3 (pending)"

    @pytest.mark.asyncio
    async def test_last_update_timestamp_conversion(self, job_monitor, create_test_job):
        """Test conversion of numeric timestamps to ISO format."""
        job_id = "test-timestamp"
        timestamp = 1704067200  # 2024-01-01 00:00:00 UTC

        repo_statuses = [
            {
                "repo_index": 0,
                "status": "completed",
                "last_update": timestamp  # Numeric timestamp
            },
            {
                "repo_index": 1,
                "status": "completed",
                "last_update": "2024-01-02T00:00:00Z"  # ISO string
            }
        ]

        create_test_job(job_id, {}, repo_statuses)

        result = await job_monitor.get_job_status(job_id)

        # Should have the later date (2024-01-02)
        assert "last_update" in result
        assert "2024-01-02" in result["last_update"]

    @pytest.mark.asyncio
    async def test_overall_status_determination(self, job_monitor, create_test_job):
        """Test various overall status determinations."""
        # Test all completed - should return "processing" when master status is not final
        # (scanner_service updates master to "completed" after this)
        job_id = "test-all-completed"
        create_test_job(job_id, {"total_repositories": 2}, [
            {"status": "completed"},
            {"status": "completed"}
        ])
        result = await job_monitor.get_job_status(job_id)
        assert result["status"] == "processing"

        # Test all failed - should return "processing" when master status is not final
        job_id = "test-all-failed"
        create_test_job(job_id, {"total_repositories": 2}, [
            {"status": "failed"},
            {"status": "failed"}
        ])
        result = await job_monitor.get_job_status(job_id)
        assert result["status"] == "processing"

        # Test completed with errors - should return "processing" when master status is not final
        job_id = "test-completed-with-errors"
        create_test_job(job_id, {"total_repositories": 3}, [
            {"status": "completed"},
            {"status": "completed"},
            {"status": "failed"}
        ])
        result = await job_monitor.get_job_status(job_id)
        assert result["status"] == "processing"

        # Test master override (failed)
        job_id = "test-master-failed"
        create_test_job(job_id, {"status": "failed", "total_repositories": 2}, [
            {"status": "completed"}
        ])
        result = await job_monitor.get_job_status(job_id)
        assert result["status"] == "failed"

        # Test initializing
        job_id = "test-initializing"
        create_test_job(job_id, {"total_repositories": 3}, [])
        result = await job_monitor.get_job_status(job_id)
        assert result["status"] == "initializing"

    @pytest.mark.asyncio
    async def test_completed_status_when_master_initializing(self, job_monitor, create_test_job):
        """When all repos complete but master is still 'initializing', status should be 'processing'.
        The scanner_service will update master to 'completed' after processing results."""
        job_id = "test-master-initializing-completed"
        master_data = {
            "total_repositories": 1,
            "status": "initializing"
        }
        repo_statuses = [
            {
                "repo_index": 0,
                "repo_name": "finished-repo",
                "status": "completed"
            }
        ]

        create_test_job(job_id, master_data, repo_statuses)

        result = await job_monitor.get_job_status(job_id)

        assert result["status"] == "processing"
        assert result["completed_repositories"] == ["finished-repo"]

    @pytest.mark.asyncio
    async def test_error_handling(self, job_monitor, create_test_job):
        """Test error handling for corrupted files."""
        job_id = "test-error"
        job_dir = create_test_job(job_id, {"total_repositories": 2}, [])

        # Create a corrupted repo status file
        corrupted_file = job_dir / "repo_0.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json")

        # Should still return a result, skipping the bad file
        result = await job_monitor.get_job_status(job_id)
        assert result["job_id"] == job_id
        assert result["status"] in ["initializing", "in_progress"]  # Should handle gracefully

    @pytest.mark.asyncio
    async def test_no_master_file(self, job_monitor, create_test_job):
        """Test behavior when no master file exists."""
        job_id = "test-no-master"

        # Create job with only repo files, no master
        repo_statuses = [
            {"repo_index": 0, "status": "completed"},
            {"repo_index": 1, "status": "scanning", "total_files": 50, "current_file": 25}
        ]

        create_test_job(job_id, None, repo_statuses)  # No master data

        result = await job_monitor.get_job_status(job_id)

        # Should still aggregate from repo files
        assert result["job_id"] == job_id
        assert result["summary"]["completed"] == 1
        assert result["summary"]["in_progress"] == 1
        # Total repos should default to actual count
        assert result["summary"]["total_repositories"] == 2

    @pytest.mark.asyncio
    async def test_elapsed_time_no_start_time(self, job_monitor, create_test_job):
        """Test elapsed time when no start time is available."""
        job_id = "test-no-start"

        master_data = {
            # No started_at field
            "total_repositories": 1
        }

        create_test_job(job_id, master_data, [])

        result = await job_monitor.get_job_status(job_id)

        # Should default to 0 per current implementation
        assert "elapsed_time_seconds" in result
        assert result["elapsed_time_seconds"] == 0

    @pytest.mark.asyncio
    async def test_progress_message_only(self, job_monitor, create_test_job):
        """Test progress display with message only (no file counts)."""
        job_id = "test-message"

        repo_statuses = [
            {
                "repo_index": 0,
                "repo_name": "test-repo",
                "status": "cloning",
                "message": "Cloning repository...",
                "last_update": datetime.now(timezone.utc).isoformat()
            }
        ]

        create_test_job(job_id, {}, repo_statuses)

        result = await job_monitor.get_job_status(job_id)

        assert "current_repositories" in result
        current = result["current_repositories"][0]
        assert "progress" in current
        assert current["progress"]["message"] == "Cloning repository..."
        assert "total_files" not in current["progress"]

    @pytest.mark.asyncio
    async def test_failed_repository_with_errors_array(self, job_monitor, create_test_job):
        """Test failed repository with errors array format."""
        job_id = "test-failed-errors"

        repo_statuses = [
            {
                "repo_index": 0,
                "repo_name": "test-repo",
                "status": "failed",
                "error_message": "Default error",
                "errors": [
                    {"message": "Specific error from array", "timestamp": "2024-01-01T00:00:00Z"}
                ]
            }
        ]

        create_test_job(job_id, {}, repo_statuses)

        result = await job_monitor.get_job_status(job_id)

        assert "failed_repositories" in result
        failed = result["failed_repositories"][0]
        # Should use error from errors array if available
        assert failed["error"] == "Specific error from array"
