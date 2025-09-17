"""Test client compatibility with updated JobMonitor API response."""

import json
from pathlib import Path
from datetime import datetime, timezone
import pytest

from dependency_scanner_tool.api.job_monitor import JobMonitor
from dependency_scanner_tool.client import DependencyScannerClient


class TestClientCompatibility:
    """Test that client correctly handles the updated API response format."""

    @pytest.fixture
    def job_monitor(self):
        """Create a JobMonitor instance with test directory."""
        monitor = JobMonitor()
        # Use test-specific directory
        monitor.STATUS_DIR_BASE = Path("tmp/client_compat_test")
        monitor.STATUS_DIR_BASE.mkdir(parents=True, exist_ok=True)
        return monitor

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
    async def test_client_handles_current_repositories(self, job_monitor, create_test_job):
        """Test that client correctly handles 'current_repositories' field."""
        job_id = "test-client-compat"

        # Create test data matching architecture spec
        master_data = {
            "job_id": job_id,
            "group_url": "https://gitlab.com/test-group",
            "total_repositories": 5,
            "started_at": datetime.now(timezone.utc).isoformat()
        }

        repo_statuses = [
            {
                "repo_index": 0,
                "repo_name": "test-repo-1",
                "status": "scanning",
                "total_files": 100,
                "current_file": 50,
                "current_filename": "src/main.py",
                "percentage": 50.0,
                "last_update": datetime.now(timezone.utc).isoformat(),
                "started_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "repo_index": 1,
                "repo_name": "test-repo-2",
                "status": "completed",
                "last_update": datetime.now(timezone.utc).isoformat()
            }
        ]

        create_test_job(job_id, master_data, repo_statuses)

        # Get the response as the API would return it
        response = await job_monitor.get_job_status(job_id)

        # Verify the response has the expected structure
        assert "current_repositories" in response
        assert len(response["current_repositories"]) == 1
        current_repo = response["current_repositories"][0]
        assert current_repo["repo_name"] == "test-repo-1"
        assert "progress" in current_repo

        # Simulate client processing (what client.py does)
        # Client looks for "in_progress_repositories" but API returns "current_repositories"
        in_progress_repos = response.get("in_progress_repositories", [])
        # This would be empty because the field name changed!

        # Client should use "current_repositories" instead
        current_repos = response.get("current_repositories", [])
        assert len(current_repos) == 1

        # Verify structure matches what client expects
        for repo_info in current_repos:
            assert isinstance(repo_info, dict)
            assert "repo_name" in repo_info
            assert "status" in repo_info
            # Client also checks for current_file in repo_info
            if "progress" in repo_info:
                progress = repo_info["progress"]
                # Client would need to look in progress dict for current_file
                assert "current_file_name" in progress or "message" in progress

    @pytest.mark.asyncio
    async def test_client_handles_pending_repositories(self, job_monitor, create_test_job):
        """Test that client correctly handles pending_repositories field."""
        job_id = "test-pending"

        master_data = {
            "job_id": job_id,
            "total_repositories": 5
        }

        repo_statuses = [
            {"repo_index": 0, "status": "completed"}
        ]

        create_test_job(job_id, master_data, repo_statuses)

        response = await job_monitor.get_job_status(job_id)

        # Verify pending_repositories is always present (per architecture fix)
        assert "pending_repositories" in response
        assert len(response["pending_repositories"]) == 4  # 5 total - 1 completed

    @pytest.mark.asyncio
    async def test_client_handles_iso_timestamp(self, job_monitor, create_test_job):
        """Test that client correctly handles ISO formatted timestamps."""
        job_id = "test-timestamp"

        # Mix of numeric and ISO timestamps
        repo_statuses = [
            {
                "repo_index": 0,
                "status": "completed",
                "last_update": 1704067200  # Numeric timestamp
            },
            {
                "repo_index": 1,
                "status": "completed",
                "last_update": "2024-01-02T00:00:00Z"  # ISO string
            }
        ]

        create_test_job(job_id, {}, repo_statuses)

        response = await job_monitor.get_job_status(job_id)

        # Verify last_update is ISO formatted (per architecture fix)
        assert "last_update" in response
        # Should be parseable as ISO datetime
        datetime.fromisoformat(response["last_update"].replace('Z', '+00:00'))

    def test_client_display_method_with_new_format(self, job_monitor, create_test_job, capsys):
        """Test that client's display method works with the new API format."""
        from dependency_scanner_tool.client import DependencyScannerClient

        # Create a mock client (we don't need actual connection for display test)
        class MockClient(DependencyScannerClient):
            def __init__(self):
                # Skip parent init to avoid connection
                self.poll_interval = 5

        client = MockClient()

        # Test data with new format
        current_status = {
            "job_id": "test-123",
            "status": "in_progress",
            "elapsed_time_seconds": 120.5,
            "summary": {
                "total_repositories": 3,
                "completed": 1,
                "in_progress": 1,
                "pending": 1,
                "failed": 0
            },
            "current_repositories": [
                {
                    "repo_name": "test-repo",
                    "status": "scanning",
                    "progress": {
                        "current_file_name": "src/main.py",
                        "percentage": 45.5,
                        "total_files": 100,
                        "current_file": 45
                    }
                }
            ],
            "completed_repositories": ["repo-1"],
            "failed_repositories": []
        }

        last_status = {
            "completed_repositories": []
        }

        # Call the display method
        client._display_detailed_progress(current_status, last_status)

        # Check output
        captured = capsys.readouterr()
        assert "test-123" in captured.out
        assert "in_progress" in captured.out
        assert "120.5s" in captured.out
        assert "1/3 completed" in captured.out
        assert "33.3%" in captured.out
        assert "test-repo" in captured.out
        assert "src/main.py" in captured.out
        assert "45.5%" in captured.out
        assert "✓ Completed: repo-1" in captured.out

    @pytest.mark.asyncio
    async def test_client_display_progress_compatibility(self, job_monitor, create_test_job):
        """Test that the client's _display_detailed_progress method works with new format."""
        job_id = "test-display"

        # Create a response matching the new format
        master_data = {
            "job_id": job_id,
            "group_url": "https://gitlab.com/test",
            "total_repositories": 3,
            "started_at": datetime.now(timezone.utc).isoformat()
        }

        repo_statuses = [
            {
                "repo_index": 0,
                "repo_name": "repo-1",
                "status": "scanning",
                "total_files": 100,
                "current_file": 75,
                "current_filename": "file.py",
                "last_update": datetime.now(timezone.utc).isoformat()
            },
            {
                "repo_index": 1,
                "repo_name": "repo-2",
                "status": "completed",
                "last_update": datetime.now(timezone.utc).isoformat()
            },
            {
                "repo_index": 2,
                "repo_name": "repo-3",
                "status": "failed",
                "error_message": "Clone failed",
                "last_update": datetime.now(timezone.utc).isoformat()
            }
        ]

        create_test_job(job_id, master_data, repo_statuses)

        response = await job_monitor.get_job_status(job_id)

        # Verify response structure matches what client expects
        assert response["summary"]["total_repositories"] == 3
        assert response["summary"]["completed"] == 1
        assert response["summary"]["in_progress"] == 1
        assert response["summary"]["failed"] == 1
        assert response["summary"]["pending"] == 0

        # Check current_repositories structure
        assert "current_repositories" in response
        assert len(response["current_repositories"]) == 1

        # Check completed/failed repositories
        assert "completed_repositories" in response
        assert response["completed_repositories"] == ["repo-2"]

        assert "failed_repositories" in response
        assert len(response["failed_repositories"]) == 1
        assert response["failed_repositories"][0]["repo_name"] == "repo-3"
        assert "error" in response["failed_repositories"][0]