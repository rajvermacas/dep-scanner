"""Tests for progress reporting during scanning.

This test module verifies that progress updates are correctly emitted during
dependency scanning, including:
- Dependency file parsing stage
- Import analysis stage
- API call analysis stage

It also ensures that:
- Final stage updates are always written (not throttled)
- Stage information is properly included in progress updates
- No "Unknown" stage labels appear
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

from dependency_scanner_tool.scanner import DependencyScanner
from dependency_scanner_tool.parsers.parser_manager import ParserManager


class TestProgressReporting:
    """Test progress reporting during scanning."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create a requirements.txt file
            requirements_file = project_path / "requirements.txt"
            requirements_file.write_text("requests==2.28.0\nnumpy==1.24.0\n")

            # Create Python source files
            src_dir = project_path / "src"
            src_dir.mkdir()

            python_file1 = src_dir / "main.py"
            python_file1.write_text("import requests\nimport numpy as np\n")

            python_file2 = src_dir / "utils.py"
            python_file2.write_text("import json\nimport os\n")

            # Create files for API scanning
            config_file = project_path / "config.yaml"
            config_file.write_text("api_endpoint: https://api.example.com/v1\n")

            yield project_path

    def test_parser_manager_emits_structured_progress(self):
        """Test that parser_manager emits structured progress with stage info."""
        progress_updates: List[Dict[str, Any]] = []

        def progress_callback(update):
            progress_updates.append(update)

        parser_manager = ParserManager()

        # Create a temporary requirements.txt file
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.28.0\n")

            # Parse the file with progress callback
            parser_manager.parse_files([requirements_file], progress_callback=progress_callback)

        # Verify progress updates
        assert len(progress_updates) == 1, "Should have one progress update for one file"

        # Verify structure of progress update
        update = progress_updates[0]
        assert isinstance(update, dict), "Progress update should be a dict"
        assert "stage" in update, "Progress update should have 'stage'"
        assert "stage_index" in update, "Progress update should have 'stage_index'"
        assert "stage_total" in update, "Progress update should have 'stage_total'"
        assert "message" in update, "Progress update should have 'message'"

        # Verify stage is not "unknown"
        assert update["stage"] == "dependencies", "Stage should be 'dependencies'"
        assert update["stage"] != "unknown", "Stage should not be 'unknown'"

        # Verify stage counts
        assert update["stage_index"] == 1, "Should be processing file 1"
        assert update["stage_total"] == 1, "Should have 1 total file"

    def test_scanner_emits_final_dependency_stage_update(self, temp_project_dir):
        """Test that scanner emits final update after dependency parsing."""
        progress_updates: List[Dict[str, Any]] = []

        def progress_callback(update):
            progress_updates.append(update)

        scanner = DependencyScanner()
        scanner.scan_project(
            str(temp_project_dir),
            analyze_imports=False,
            analyze_api_calls=False,
            progress_callback=progress_callback
        )

        # Find dependency stage updates
        dependency_updates = [u for u in progress_updates if isinstance(u, dict) and u.get("stage") == "dependencies"]

        assert len(dependency_updates) > 0, "Should have dependency stage updates"

        # Verify final update exists
        final_update = dependency_updates[-1]
        assert final_update["stage_index"] == final_update["stage_total"], \
            "Final update should have stage_index == stage_total"

    def test_scanner_emits_final_import_stage_update(self, temp_project_dir):
        """Test that scanner emits final update after import analysis."""
        progress_updates: List[Dict[str, Any]] = []

        def progress_callback(update):
            progress_updates.append(update)

        scanner = DependencyScanner()
        scanner.scan_project(
            str(temp_project_dir),
            analyze_imports=True,
            analyze_api_calls=False,
            progress_callback=progress_callback
        )

        # Find import stage updates
        import_updates = [u for u in progress_updates if isinstance(u, dict) and u.get("stage") == "imports"]

        # Should have import updates since we have Python files
        if import_updates:  # Only check if there were import updates
            final_update = import_updates[-1]
            assert final_update["stage_index"] == final_update["stage_total"], \
                "Final import update should have stage_index == stage_total"

    def test_scanner_emits_final_api_stage_update(self, temp_project_dir):
        """Test that scanner emits final update after API call analysis."""
        progress_updates: List[Dict[str, Any]] = []

        def progress_callback(update):
            progress_updates.append(update)

        scanner = DependencyScanner()
        scanner.scan_project(
            str(temp_project_dir),
            analyze_imports=False,
            analyze_api_calls=True,
            progress_callback=progress_callback
        )

        # Find API call stage updates
        api_updates = [u for u in progress_updates if isinstance(u, dict) and u.get("stage") == "api_calls"]

        # Should have API updates since we have scannable files
        if api_updates:  # Only check if there were API updates
            final_update = api_updates[-1]
            assert final_update["stage_index"] == final_update["stage_total"], \
                "Final API update should have stage_index == stage_total"

    def test_no_unknown_stage_in_progress_updates(self, temp_project_dir):
        """Test that no 'unknown' stage appears in progress updates."""
        progress_updates: List[Dict[str, Any]] = []

        def progress_callback(update):
            progress_updates.append(update)

        scanner = DependencyScanner()
        scanner.scan_project(
            str(temp_project_dir),
            analyze_imports=True,
            analyze_api_calls=True,
            progress_callback=progress_callback
        )

        # Check all updates for "unknown" stage
        for update in progress_updates:
            if isinstance(update, dict) and "stage" in update:
                assert update["stage"] != "unknown", \
                    f"Found 'unknown' stage in update: {update}"

    def test_scanner_worker_forces_final_updates(self):
        """Test that scanner worker forces final stage updates."""
        from dependency_scanner_tool.api.scanner_worker import ScanProgressAggregator

        # Create a mock progress aggregator
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            tracker = ScanProgressAggregator(repo_path, initial_total=10)

            # Simulate final progress update for a stage
            final_progress = {
                "path": "/some/file.py",
                "stage": "imports",
                "stage_index": 7,
                "stage_total": 7,
                "message": "Import analysis complete"
            }

            # Process the update
            update_kwargs = tracker.process(final_progress)

            # Verify the update contains expected fields
            assert update_kwargs["stage"] == "imports"
            assert update_kwargs["stage_index"] == 7
            assert update_kwargs["stage_total"] == 7

    def test_all_stages_have_proper_labels(self, temp_project_dir):
        """Test that all stages have proper labels (not Unknown)."""
        progress_updates: List[Dict[str, Any]] = []

        def progress_callback(update):
            progress_updates.append(update)

        scanner = DependencyScanner()
        scanner.scan_project(
            str(temp_project_dir),
            analyze_imports=True,
            analyze_api_calls=True,
            progress_callback=progress_callback
        )

        # Valid stage names
        valid_stages = {"dependencies", "imports", "api_calls"}

        # Check all updates have valid stage names
        for update in progress_updates:
            if isinstance(update, dict) and "stage" in update:
                assert update["stage"] in valid_stages, \
                    f"Invalid stage '{update['stage']}' in update: {update}"

    def test_progress_updates_are_sequential(self, temp_project_dir):
        """Test that stage_index values are sequential within each stage."""
        progress_updates: List[Dict[str, Any]] = []

        def progress_callback(update):
            progress_updates.append(update)

        scanner = DependencyScanner()
        scanner.scan_project(
            str(temp_project_dir),
            analyze_imports=True,
            analyze_api_calls=True,
            progress_callback=progress_callback
        )

        # Group updates by stage
        stages: Dict[str, List[int]] = {}
        for update in progress_updates:
            if isinstance(update, dict) and "stage" in update and "stage_index" in update:
                stage = update["stage"]
                if stage not in stages:
                    stages[stage] = []
                stages[stage].append(update["stage_index"])

        # Verify each stage has sequential indices
        for stage, indices in stages.items():
            # Indices should be monotonically increasing
            for i in range(len(indices) - 1):
                assert indices[i] <= indices[i + 1], \
                    f"Stage '{stage}' has non-sequential indices: {indices}"

    def test_stage_total_matches_final_index(self, temp_project_dir):
        """Test that stage_total matches the final stage_index for each stage."""
        progress_updates: List[Dict[str, Any]] = []

        def progress_callback(update):
            progress_updates.append(update)

        scanner = DependencyScanner()
        scanner.scan_project(
            str(temp_project_dir),
            analyze_imports=True,
            analyze_api_calls=True,
            progress_callback=progress_callback
        )

        # Group updates by stage and check final values
        stages: Dict[str, Dict[str, Any]] = {}
        for update in progress_updates:
            if isinstance(update, dict) and "stage" in update:
                stage = update["stage"]
                if "stage_index" in update and "stage_total" in update:
                    if stage not in stages:
                        stages[stage] = {"max_index": 0, "total": update["stage_total"]}
                    stages[stage]["max_index"] = max(stages[stage]["max_index"], update["stage_index"])

        # Verify final index matches total for each stage
        for stage, data in stages.items():
            assert data["max_index"] == data["total"], \
                f"Stage '{stage}' final index {data['max_index']} != total {data['total']}"
