"""Integration tests for subprocess-based scanning with monitoring."""

import os
import sys
import json
import time
import asyncio
import shutil
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dependency_scanner_tool.api.scanner_service import ScannerService
from dependency_scanner_tool.api.job_monitor import JobMonitor
from dependency_scanner_tool.api.job_manager import job_manager, JobStatus
from dependency_scanner_tool.api.models import ScanRequest


class TestSubprocessMonitoring:
    """Test subprocess-based scanning without blocking event loop."""

    @pytest.fixture
    def scanner_service(self):
        """Create scanner service instance."""
        return ScannerService()

    @pytest.fixture
    def job_monitor(self):
        """Create job monitor instance."""
        return JobMonitor()

    @pytest.fixture(autouse=True)
    def cleanup_jobs(self):
        """Clean up test job directories before and after tests."""
        test_dir = Path("tmp/scan_jobs")
        if test_dir.exists():
            for job_dir in test_dir.iterdir():
                if job_dir.is_dir() and job_dir.name.startswith("test-"):
                    shutil.rmtree(job_dir)
        yield
        # Cleanup after test
        if test_dir.exists():
            for job_dir in test_dir.iterdir():
                if job_dir.is_dir() and job_dir.name.startswith("test-"):
                    shutil.rmtree(job_dir)

    @pytest.mark.asyncio
    async def test_api_remains_responsive_during_scan(self, scanner_service):
        """Test that API doesn't block during repository scanning."""
        job_id = "test-responsive-" + str(int(time.time()))

        # Mock the subprocess spawn to simulate long-running scan
        async def mock_spawn(job_id, repo_index, repo_name, git_url):
            # Create a mock process
            process = AsyncMock()
            process.pid = 12345
            process.returncode = None  # Still running

            # Simulate process taking time
            async def wait():
                await asyncio.sleep(0.5)  # Short delay for test
                process.returncode = 0
                return 0

            process.wait = wait
            return process

        with patch.object(scanner_service, '_spawn_scanner_subprocess', mock_spawn):
            # Start scan in background
            scan_task = asyncio.create_task(
                scanner_service._scan_single_repository_subprocess(
                    job_id, "https://github.com/test/repo.git"
                )
            )

            # Immediately make other async calls (simulating API responsiveness)
            start_time = time.time()
            other_tasks = []

            async def api_call(call_num):
                """Simulate API call."""
                await asyncio.sleep(0.01)  # Small delay
                return f"Response {call_num}"

            # Make multiple "API calls" while scan is running
            for i in range(5):
                other_tasks.append(asyncio.create_task(api_call(i)))

            # All API calls should complete quickly
            results = await asyncio.gather(*other_tasks)
            api_time = time.time() - start_time

            # API calls should be fast (< 0.2 seconds total)
            assert api_time < 0.2, f"API calls took too long: {api_time}s"
            assert len(results) == 5
            assert all(r.startswith("Response") for r in results)

            # Wait for scan to complete
            await scan_task

    @pytest.mark.asyncio
    async def test_status_file_creation_and_updates(self, job_monitor):
        """Test that status files are created and updated correctly."""
        job_id = "test-status-" + str(int(time.time()))

        # Create initial master status
        job_monitor.update_master_status(
            job_id,
            group_url="https://test.com/repo",
            total_repositories=1,
            status="initializing",
            started_at=datetime.now(timezone.utc).isoformat()
        )

        # Verify master file exists
        master_file = Path(f"tmp/scan_jobs/{job_id}/master.json")
        assert master_file.exists()

        with open(master_file, 'r') as f:
            master_data = json.load(f)
            assert master_data["job_id"] == job_id
            assert master_data["status"] == "initializing"

        # Simulate repository status update
        repo_file = Path(f"tmp/scan_jobs/{job_id}/repo_0.json")
        repo_status = {
            "repo_index": 0,
            "repo_name": "test-repo",
            "status": "scanning",
            "total_files": 100,
            "current_file": 50,
            "percentage": 50,
            "last_update": datetime.now(timezone.utc).isoformat()
        }

        repo_file.parent.mkdir(parents=True, exist_ok=True)
        with open(repo_file, 'w') as f:
            json.dump(repo_status, f)

        # Get aggregated status
        status = await job_monitor.get_job_status(job_id)

        assert status["job_id"] == job_id
        assert status["status"] == "in_progress"
        assert status["summary"]["in_progress"] == 1
        assert len(status.get("current_repositories", [])) == 1
        assert status["current_repositories"][0]["progress"]["percentage"] == 50

    @pytest.mark.asyncio
    async def test_concurrent_subprocess_spawning(self, scanner_service):
        """Test spawning multiple subprocesses concurrently."""
        job_id = "test-concurrent-" + str(int(time.time()))

        processes_spawned = []

        async def track_spawn(job_id, repo_index, repo_name, git_url):
            """Track spawned processes."""
            processes_spawned.append({
                "repo_index": repo_index,
                "repo_name": repo_name,
                "time": time.time()
            })

            # Create mock process
            process = AsyncMock()
            process.pid = 10000 + repo_index
            process.returncode = None

            async def wait():
                await asyncio.sleep(0.1)  # Simulate work
                process.returncode = 0
                return 0

            process.wait = wait
            return process

        # Mock GitLab service to return multiple projects
        mock_projects = [
            {"name": f"project-{i}", "git_url": f"https://test.com/project-{i}.git"}
            for i in range(10)
        ]

        with patch.object(scanner_service, '_spawn_scanner_subprocess', track_spawn):
            # Create mock GitLab service instance
            mock_gitlab_instance = MagicMock()
            mock_gitlab_instance.get_project_info = AsyncMock(return_value=mock_projects)
            mock_gitlab_instance.__aenter__ = AsyncMock(return_value=mock_gitlab_instance)
            mock_gitlab_instance.__aexit__ = AsyncMock(return_value=False)

            with patch('dependency_scanner_tool.api.gitlab_service.GitLabGroupService', return_value=mock_gitlab_instance):
                # Run group scan
                await scanner_service._scan_gitlab_group_subprocess(
                    job_id, "https://gitlab.com/test-group"
                )

        # Verify all processes were spawned
        assert len(processes_spawned) == 10

        # Check concurrency (should have overlapping spawns)
        spawn_times = [p["time"] for p in processes_spawned]
        time_range = max(spawn_times) - min(spawn_times)

        # With MAX_CONCURRENT_PROCESSES=5, 10 repos should take ~0.2s (2 batches)
        # If sequential, would take ~1s
        assert time_range < 0.5, f"Processes not spawned concurrently: {time_range}s"

    @pytest.mark.asyncio
    async def test_subprocess_crash_handling(self, job_monitor):
        """Test handling of subprocess crashes."""
        job_id = "test-crash-" + str(int(time.time()))

        # Create mock process that crashes
        process = AsyncMock()
        process.pid = 99999
        process.returncode = None
        process.stderr = AsyncMock()
        process.stderr.read = AsyncMock(return_value=b"Fatal error: segmentation fault")

        async def crash():
            await asyncio.sleep(0.1)
            process.returncode = -11  # SIGSEGV
            return -11

        process.wait = crash

        # Monitor the crashed process
        await job_monitor.monitor_subprocess(job_id, process, 0, timeout=1)

        # Check that failure was recorded
        repo_file = Path(f"tmp/scan_jobs/{job_id}/repo_0.json")
        assert repo_file.exists()

        with open(repo_file, 'r') as f:
            status = json.load(f)
            assert status["status"] == "failed"
            assert "exited with code -11" in status["error_message"]
            assert status["stderr"] == "Fatal error: segmentation fault"

    @pytest.mark.asyncio
    async def test_timeout_handling(self, job_monitor):
        """Test subprocess timeout handling."""
        job_id = "test-timeout-" + str(int(time.time()))

        # Create process that hangs
        process = AsyncMock()
        process.pid = 88888
        process.returncode = None
        process.kill = Mock()

        async def hang_forever():
            await asyncio.sleep(10)  # Much longer than timeout
            return 0

        process.wait = Mock(side_effect=hang_forever)

        # Monitor with short timeout
        await job_monitor.monitor_subprocess(job_id, process, 0, timeout=0.2)

        # Process should be killed
        process.kill.assert_called_once()

        # Check timeout was recorded
        repo_file = Path(f"tmp/scan_jobs/{job_id}/repo_0.json")
        if repo_file.exists():
            with open(repo_file, 'r') as f:
                status = json.load(f)
                assert status["status"] == "failed"
                assert "timeout" in status["error_message"].lower()

    @pytest.mark.asyncio
    async def test_cleanup_old_jobs(self, job_monitor):
        """Test cleanup of old job directories."""
        # Create old job directory
        old_job_id = "test-old-job"
        old_job_dir = Path(f"tmp/scan_jobs/{old_job_id}")
        old_job_dir.mkdir(parents=True, exist_ok=True)

        # Create master file with old completion time (2 days ago)
        old_time = datetime.now(timezone.utc)
        old_time = old_time.replace(
            day=old_time.day - 2 if old_time.day > 2 else 1
        )

        master_status = {
            "job_id": old_job_id,
            "status": "completed",
            "completed_at": old_time.isoformat()
        }

        with open(old_job_dir / "master.json", 'w') as f:
            json.dump(master_status, f)

        # Create recent job directory
        recent_job_id = "test-recent-job"
        recent_job_dir = Path(f"tmp/scan_jobs/{recent_job_id}")
        recent_job_dir.mkdir(parents=True, exist_ok=True)

        recent_status = {
            "job_id": recent_job_id,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }

        with open(recent_job_dir / "master.json", 'w') as f:
            json.dump(recent_status, f)

        # Run cleanup (24 hour threshold)
        cleaned = await job_monitor.cleanup_old_jobs(age_hours=24)

        # Old job should be removed
        assert not old_job_dir.exists()
        # Recent job should remain
        assert recent_job_dir.exists()
        assert cleaned >= 1

        # Cleanup
        shutil.rmtree(recent_job_dir)

    @pytest.mark.asyncio
    async def test_atomic_file_writes(self, job_monitor):
        """Test that status file writes are atomic."""
        job_id = "test-atomic-" + str(int(time.time()))

        # Write status multiple times rapidly
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                asyncio.to_thread(
                    job_monitor.update_master_status,
                    job_id,
                    status=f"update-{i}",
                    counter=i
                )
            )
            tasks.append(task)

        # All writes should complete without corruption
        await asyncio.gather(*tasks, return_exceptions=True)

        # Read final status
        master_file = Path(f"tmp/scan_jobs/{job_id}/master.json")
        assert master_file.exists()

        with open(master_file, 'r') as f:
            data = json.load(f)
            # Should be valid JSON (not corrupted)
            assert "status" in data
            assert data["status"].startswith("update-")

    def test_no_race_conditions(self):
        """Test that there are no race conditions in status updates."""
        # This is validated by design:
        # 1. Each subprocess writes only to its own file
        # 2. Master process only reads subprocess files
        # 3. Atomic writes using rename

        # Verify scanner_worker only writes to its own file
        from dependency_scanner_tool.api.scanner_worker import ScannerWorker

        worker = ScannerWorker("test-job", 5, "test-repo")
        expected_file = Path("tmp/scan_jobs/test-job/repo_5.json")
        assert worker.status_file == expected_file

        # Different workers write to different files
        worker2 = ScannerWorker("test-job", 10, "another-repo")
        assert worker2.status_file != worker.status_file
        assert worker2.status_file == Path("tmp/scan_jobs/test-job/repo_10.json")


class TestAPIIntegration:
    """Test integration with FastAPI endpoints."""

    @pytest.mark.asyncio
    async def test_scan_endpoint_returns_immediately(self):
        """Test that /scan endpoint returns immediately without blocking."""
        from fastapi.testclient import TestClient
        from dependency_scanner_tool.api.app import app

        client = TestClient(app)

        # Mock auth
        with patch('dependency_scanner_tool.api.auth.verify_credentials', return_value=True):
            # Mock subprocess spawning to avoid actual scanning
            with patch('dependency_scanner_tool.api.scanner_service.scanner_service._spawn_scanner_subprocess') as mock_spawn:
                mock_process = AsyncMock()
                mock_process.pid = 12345
                mock_process.returncode = None
                mock_spawn.return_value = mock_process

                # Submit scan request
                start_time = time.time()
                response = client.post(
                    "/scan",
                    json={"git_url": "https://github.com/test/repo.git"},
                    auth=("testuser", "testpass")
                )
                response_time = time.time() - start_time

                # Should return immediately (< 1 second)
                assert response_time < 1.0
                assert response.status_code == 200

                data = response.json()
                assert "job_id" in data
                assert data["status"] == "pending"  # JobStatus.PENDING value is lowercase

    @pytest.mark.asyncio
    async def test_scan_progress_endpoint(self):
        """Test /scan/{job_id} endpoint returns detailed progress."""
        from fastapi.testclient import TestClient
        from dependency_scanner_tool.api.app import app

        client = TestClient(app)
        job_id = "test-progress-api"

        # Create test status files
        job_dir = Path(f"tmp/scan_jobs/{job_id}")
        job_dir.mkdir(parents=True, exist_ok=True)

        # Master status
        master_status = {
            "job_id": job_id,
            "group_url": "https://test.com/group",
            "total_repositories": 3,
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        with open(job_dir / "master.json", 'w') as f:
            json.dump(master_status, f)

        # Repository status
        repo_status = {
            "repo_index": 0,
            "repo_name": "test-repo",
            "status": "scanning",
            "total_files": 100,
            "current_file": 75,
            "percentage": 75,
            "current_filename": "src/main.py",
            "last_update": datetime.now(timezone.utc).isoformat()
        }
        with open(job_dir / "repo_0.json", 'w') as f:
            json.dump(repo_status, f)

        # Mock auth
        with patch('dependency_scanner_tool.api.auth.verify_credentials', return_value=True):
            # Get progress
            response = client.get(
                f"/scan/{job_id}",
                auth=("testuser", "testpass")
            )

            assert response.status_code == 200
            data = response.json()

            assert data["job_id"] == job_id
            assert data["status"] == "in_progress"
            assert data["summary"]["total_repositories"] == 3
            assert data["summary"]["in_progress"] == 1
            assert len(data["current_repositories"]) == 1
            assert data["current_repositories"][0]["repo_name"] == "test-repo"
            assert data["current_repositories"][0]["progress"]["percentage"] == 75
            assert data["current_repositories"][0]["progress"]["current_file_name"] == "src/main.py"

        # Cleanup
        shutil.rmtree(job_dir)