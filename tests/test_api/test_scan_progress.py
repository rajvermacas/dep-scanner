"""Tests for /scan/{job_id} progress API covering long-running flows."""

import json
import time
from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def client():
    from dependency_scanner_tool.api.app import app
    return TestClient(app)


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f)


class TestScanProgressLongRunning:
    @pytest.mark.asyncio
    async def test_long_running_single_repo_updates_over_time(self, client):
        """Simulate a long-running single-repo job and verify incremental updates."""
        job_id = f"test-long-run-{int(time.time())}"
        job_dir = Path(f"tmp/scan_jobs/{job_id}")

        # Initial master status
        master = {
            "job_id": job_id,
            "group_url": "https://example.com/repo.git",
            "total_repositories": 1,
            "status": "initializing",
            "started_at": _iso_now(),
            "pending_repositories": ["repo"],
            "completed_repositories": [],
            "failed_repositories": []
        }
        _write(job_dir / "master.json", master)

        # First progress write (10%)
        repo0 = {
            "repo_index": 0,
            "repo_name": "repo",
            "status": "scanning",
            "total_files": 200,
            "current_file": 20,
            "percentage": 10,
            "current_filename": "src/a.py",
            "last_update": _iso_now(),
        }
        _write(job_dir / "repo_0.json", repo0)

        with patch('dependency_scanner_tool.api.auth.verify_credentials', return_value=True):
            r1 = client.get(f"/scan/{job_id}", auth=("u", "p"))
            assert r1.status_code == 200
            d1 = r1.json()
            assert d1["job_id"] == job_id
            assert d1["status"] in ("in_progress", "initializing")
            assert d1["summary"]["total_repositories"] == 1
            assert d1["summary"]["in_progress"] == 1
            assert len(d1.get("current_repositories", [])) == 1
            cur = d1["current_repositories"][0]
            assert cur["repo_name"] == "repo"
            assert cur["progress"]["total_files"] == 200
            assert cur["progress"]["current_file"] == 20
            assert cur["progress"]["percentage"] == 10
            assert cur["progress"]["current_file_name"] == "src/a.py"

        # Second progress write (50%)
        repo0.update({
            "current_file": 100,
            "percentage": 50,
            "current_filename": "src/b.py",
            "last_update": _iso_now(),
        })
        _write(job_dir / "repo_0.json", repo0)

        with patch('dependency_scanner_tool.api.auth.verify_credentials', return_value=True):
            r2 = client.get(f"/scan/{job_id}", auth=("u", "p"))
            assert r2.status_code == 200
            d2 = r2.json()
            cur2 = d2["current_repositories"][0]
            assert cur2["progress"]["current_file"] == 100
            assert cur2["progress"]["percentage"] == 50
            assert cur2["progress"]["current_file_name"] == "src/b.py"

        # Finalize (completed with results)
        repo0.update({
            "status": "completed",
            "current_file": 200,
            "percentage": 100,
            "current_filename": None,
            "scan_result": {
                "dependencies": 12,
                "api_calls": 3,
                "source_files": 200,
                "categorized_dependencies": {"database": True, "cache": False},
                "infrastructure_usage": {"aws": True}
            },
            "last_update": _iso_now(),
        })
        _write(job_dir / "repo_0.json", repo0)

        # Update master to completed
        master.update({
            "status": "completed",
            "pending_repositories": [],
            "completed_repositories": ["repo"],
            "last_aggregation": _iso_now(),
        })
        _write(job_dir / "master.json", master)

        with patch('dependency_scanner_tool.api.auth.verify_credentials', return_value=True):
            r3 = client.get(f"/scan/{job_id}", auth=("u", "p"))
            assert r3.status_code == 200
            d3 = r3.json()
            assert d3["status"] in ("completed", "completed_with_errors")
            assert d3["summary"]["completed"] == 1
            assert d3["summary"]["failed"] == 0
            # Completed list should include repo
            assert "completed_repositories" in d3
            assert "repo" in d3["completed_repositories"]

        # Cleanup
        if job_dir.exists():
            for p in job_dir.iterdir():
                p.unlink()
            job_dir.rmdir()

    @pytest.mark.asyncio
    async def test_multi_repo_mixed_status_aggregation(self, client):
        """Verify aggregation for multiple repos with mixed states."""
        job_id = f"test-mixed-{int(time.time())}"
        job_dir = Path(f"tmp/scan_jobs/{job_id}")

        master = {
            "job_id": job_id,
            "group_url": "https://example.com/group",
            "total_repositories": 3,
            "status": "in_progress",
            "started_at": _iso_now(),
        }
        _write(job_dir / "master.json", master)

        # repo_0 scanning
        _write(job_dir / "repo_0.json", {
            "repo_index": 0,
            "repo_name": "p0",
            "status": "scanning",
            "total_files": 50,
            "current_file": 25,
            "percentage": 50,
            "current_filename": "a.py",
            "last_update": _iso_now(),
        })
        # repo_1 failed
        _write(job_dir / "repo_1.json", {
            "repo_index": 1,
            "repo_name": "p1",
            "status": "failed",
            "error_message": "Network error",
            "errors": [{"message": "Network error", "timestamp": _iso_now()}],
            "last_update": _iso_now(),
        })
        # repo_2 not yet present -> counts as pending

        with patch('dependency_scanner_tool.api.auth.verify_credentials', return_value=True):
            r = client.get(f"/scan/{job_id}", auth=("u", "p"))
            assert r.status_code == 200
            d = r.json()
            assert d["summary"]["total_repositories"] == 3
            assert d["summary"]["in_progress"] == 1
            assert d["summary"]["failed"] == 1
            assert d["summary"]["pending"] == 1
            assert any(fr.get("repo_name") == "p1" for fr in d.get("failed_repositories", []))
            cur = d.get("current_repositories", [])[0]
            assert cur["progress"]["total_files"] == 50
            assert cur["progress"]["current_file"] == 25
            assert cur["progress"]["percentage"] == 50

        # Cleanup
        if job_dir.exists():
            for p in job_dir.iterdir():
                p.unlink()
            job_dir.rmdir()

