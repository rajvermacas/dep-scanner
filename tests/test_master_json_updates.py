"""Test that master.json is updated when repositories complete."""

import json
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import pytest
import shutil

from dependency_scanner_tool.api.job_monitor import JobMonitor


class TestMasterJsonUpdates:
    """Test suite for master.json repository list updates."""

    @pytest.fixture
    def job_monitor(self):
        """Create a JobMonitor instance with test directory."""
        monitor = JobMonitor()
        # Use test-specific directory
        monitor.STATUS_DIR_BASE = Path("tmp/master_update_test")
        monitor.STATUS_DIR_BASE.mkdir(parents=True, exist_ok=True)
        yield monitor
        # Cleanup
        if monitor.STATUS_DIR_BASE.exists():
            shutil.rmtree(monitor.STATUS_DIR_BASE)

    @pytest.fixture
    def create_test_job(self, job_monitor):
        """Helper to create test job with initial master.json."""
        def _create(job_id, pending_repos):
            job_dir = job_monitor.STATUS_DIR_BASE / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            # Create initial master.json
            master_data = {
                "job_id": job_id,
                "group_url": "https://gitlab.com/test-group",
                "total_repositories": len(pending_repos),
                "status": "initializing",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "pending_repositories": pending_repos,
                "completed_repositories": [],
                "failed_repositories": []
            }

            master_file = job_dir / "master.json"
            with open(master_file, 'w') as f:
                json.dump(master_data, f, indent=2)

            return job_dir

        return _create

    @pytest.mark.asyncio
    async def test_repository_completion_updates_master(self, job_monitor, create_test_job):
        """Test that completing a repository updates master.json lists."""
        job_id = "test-completion"
        pending_repos = ["repo-1", "repo-2", "repo-3"]

        job_dir = create_test_job(job_id, pending_repos)

        # Create a completed repo status file
        repo_status = {
            "repo_index": 0,
            "repo_name": "repo-1",
            "status": "completed",
            "last_update": datetime.now(timezone.utc).isoformat()
        }

        repo_file = job_dir / "repo_0.json"
        with open(repo_file, 'w') as f:
            json.dump(repo_status, f, indent=2)

        # Call the update method
        await job_monitor._update_repository_completion(job_id, 0)

        # Read updated master.json
        master_file = job_dir / "master.json"
        with open(master_file, 'r') as f:
            master_data = json.load(f)

        # Verify updates
        assert "repo-1" not in master_data["pending_repositories"]
        assert "repo-1" in master_data["completed_repositories"]
        assert len(master_data["pending_repositories"]) == 2
        assert len(master_data["completed_repositories"]) == 1
        assert len(master_data["failed_repositories"]) == 0

    @pytest.mark.asyncio
    async def test_repository_failure_updates_master(self, job_monitor, create_test_job):
        """Test that failing a repository updates master.json lists."""
        job_id = "test-failure"
        pending_repos = ["repo-1", "repo-2", "repo-3"]

        job_dir = create_test_job(job_id, pending_repos)

        # Create a failed repo status file
        repo_status = {
            "repo_index": 1,
            "repo_name": "repo-2",
            "status": "failed",
            "error_message": "Clone failed: Access denied",
            "last_update": datetime.now(timezone.utc).isoformat()
        }

        repo_file = job_dir / "repo_1.json"
        with open(repo_file, 'w') as f:
            json.dump(repo_status, f, indent=2)

        # Call the update method
        await job_monitor._update_repository_completion(job_id, 1)

        # Read updated master.json
        master_file = job_dir / "master.json"
        with open(master_file, 'r') as f:
            master_data = json.load(f)

        # Verify updates
        assert "repo-2" not in master_data["pending_repositories"]
        assert len(master_data["pending_repositories"]) == 2
        assert len(master_data["completed_repositories"]) == 0
        assert len(master_data["failed_repositories"]) == 1

        # Check failed repo structure
        failed_repo = master_data["failed_repositories"][0]
        assert failed_repo["repo_name"] == "repo-2"
        assert failed_repo["error"] == "Clone failed: Access denied"
        assert failed_repo["status"] == "failed"

    @pytest.mark.asyncio
    async def test_multiple_completions_update_master(self, job_monitor, create_test_job):
        """Test multiple repositories completing updates master.json correctly."""
        job_id = "test-multiple"
        pending_repos = ["repo-1", "repo-2", "repo-3", "repo-4"]

        job_dir = create_test_job(job_id, pending_repos)

        # Complete first repository
        repo_status_1 = {
            "repo_index": 0,
            "repo_name": "repo-1",
            "status": "completed"
        }
        with open(job_dir / "repo_0.json", 'w') as f:
            json.dump(repo_status_1, f)

        await job_monitor._update_repository_completion(job_id, 0)

        # Fail second repository
        repo_status_2 = {
            "repo_index": 1,
            "repo_name": "repo-2",
            "status": "failed",
            "error_message": "Network error"
        }
        with open(job_dir / "repo_1.json", 'w') as f:
            json.dump(repo_status_2, f)

        await job_monitor._update_repository_completion(job_id, 1)

        # Complete third repository
        repo_status_3 = {
            "repo_index": 2,
            "repo_name": "repo-3",
            "status": "completed"
        }
        with open(job_dir / "repo_2.json", 'w') as f:
            json.dump(repo_status_3, f)

        await job_monitor._update_repository_completion(job_id, 2)

        # Read final master.json
        master_file = job_dir / "master.json"
        with open(master_file, 'r') as f:
            master_data = json.load(f)

        # Verify final state
        assert master_data["pending_repositories"] == ["repo-4"]
        assert set(master_data["completed_repositories"]) == {"repo-1", "repo-3"}
        assert len(master_data["failed_repositories"]) == 1
        assert master_data["failed_repositories"][0]["repo_name"] == "repo-2"

    @pytest.mark.asyncio
    async def test_duplicate_completion_handled(self, job_monitor, create_test_job):
        """Test that duplicate completions don't create duplicates in lists."""
        job_id = "test-duplicate"
        pending_repos = ["repo-1", "repo-2"]

        job_dir = create_test_job(job_id, pending_repos)

        # Create a completed repo status file
        repo_status = {
            "repo_index": 0,
            "repo_name": "repo-1",
            "status": "completed"
        }

        repo_file = job_dir / "repo_0.json"
        with open(repo_file, 'w') as f:
            json.dump(repo_status, f)

        # Call update twice
        await job_monitor._update_repository_completion(job_id, 0)
        await job_monitor._update_repository_completion(job_id, 0)

        # Read master.json
        master_file = job_dir / "master.json"
        with open(master_file, 'r') as f:
            master_data = json.load(f)

        # Should only have one entry
        assert len(master_data["completed_repositories"]) == 1
        assert master_data["completed_repositories"] == ["repo-1"]

    @pytest.mark.asyncio
    async def test_timeout_status_updates_master(self, job_monitor, create_test_job):
        """Test that timeout status updates master.json correctly."""
        job_id = "test-timeout"
        pending_repos = ["repo-1"]

        job_dir = create_test_job(job_id, pending_repos)

        # Create a timeout repo status file
        repo_status = {
            "repo_index": 0,
            "repo_name": "repo-1",
            "status": "timeout",
            "error_message": "Process killed after 3600 seconds timeout"
        }

        repo_file = job_dir / "repo_0.json"
        with open(repo_file, 'w') as f:
            json.dump(repo_status, f)

        # Call the update method
        await job_monitor._update_repository_completion(job_id, 0)

        # Read updated master.json
        master_file = job_dir / "master.json"
        with open(master_file, 'r') as f:
            master_data = json.load(f)

        # Verify timeout is treated as failure
        assert len(master_data["pending_repositories"]) == 0
        assert len(master_data["failed_repositories"]) == 1
        failed_repo = master_data["failed_repositories"][0]
        assert failed_repo["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_missing_repo_file_handled_gracefully(self, job_monitor, create_test_job):
        """Test that missing repo file doesn't crash the update."""
        job_id = "test-missing"
        pending_repos = ["repo-1"]

        create_test_job(job_id, pending_repos)

        # Try to update without creating repo file
        await job_monitor._update_repository_completion(job_id, 0)

        # Read master.json - should be unchanged
        master_file = job_monitor.STATUS_DIR_BASE / job_id / "master.json"
        with open(master_file, 'r') as f:
            master_data = json.load(f)

        # Should still be pending
        assert master_data["pending_repositories"] == ["repo-1"]
        assert len(master_data["completed_repositories"]) == 0
        assert len(master_data["failed_repositories"]) == 0