"""
Tests for ignore_patterns configuration functionality.
"""

import os
import tempfile
from pathlib import Path
import pytest
import yaml

from src.dependency_scanner_tool.scanner import DependencyScanner


class TestIgnorePatterns:
    """Test suite for ignore_patterns configuration."""

    def test_ignore_patterns_from_config(self):
        """Test that ignore_patterns from config.yaml are properly applied during scanning."""
        # Load config
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        ignore_patterns = config.get("ignore_patterns", [])
        assert ignore_patterns, "config.yaml should have ignore_patterns defined"

        # Get test data path
        test_path = Path(__file__).parent / "test_data" / "ignore_patterns_test"
        assert test_path.exists(), f"Test data path {test_path} does not exist"

        # Initialize scanner with ignore patterns
        scanner = DependencyScanner(ignore_patterns=ignore_patterns)

        # Perform scan
        result = scanner.scan_project(project_path=str(test_path))

        # Check dependency_files - these should only be from valid directories
        for dep_file in result.dependency_files:
            # Convert to Path for easier checking
            file_path = Path(dep_file)
            parts = file_path.parts

            # Check against each ignore pattern
            assert ".venv" not in parts, f"Found .venv in dependency file: {dep_file}"
            assert ".venv-win" not in parts, f"Found .venv-win in dependency file: {dep_file}"
            assert "__pycache__" not in parts, f"Found __pycache__ in dependency file: {dep_file}"
            assert ".git" not in parts, f"Found .git in dependency file: {dep_file}"
            assert not str(file_path).endswith(".pyc"), f"Found .pyc file in dependency files: {dep_file}"

        # Verify that valid files were scanned
        valid_files_found = any("valid_dir" in str(f) for f in result.dependency_files)
        assert valid_files_found, "Valid directory files should be scanned"

        # Verify dependencies were found from valid files
        assert len(result.dependencies) > 0, "Should find dependencies from valid files"

        # Check that we found the expected dependencies
        dep_names = {dep.name for dep in result.dependencies}
        assert "requests" in dep_names, "Should find requests dependency"
        assert "numpy" in dep_names, "Should find numpy dependency"

    def test_ignore_patterns_exclude_specific_dirs(self):
        """Test that each specific ignore pattern correctly excludes its target."""
        test_path = Path(__file__).parent / "test_data" / "ignore_patterns_test"

        # Test each pattern individually
        patterns_to_test = [
            (".venv", ".venv"),
            (".venv-win", ".venv-win"),
            ("__pycache__", "__pycache__"),
            ("*.pyc", ".pyc"),
            (".git", ".git")
        ]

        for pattern, check_string in patterns_to_test:
            scanner = DependencyScanner(ignore_patterns=[pattern])

            result = scanner.scan_project(project_path=str(test_path))

            # Check both dependency files and source files (via dependencies)
            all_files = list(result.dependency_files)
            all_files.extend([Path(d.source_file) for d in result.dependencies if d.source_file])

            # Verify the pattern excluded its target
            if pattern == "*.pyc":
                assert not any(str(f).endswith(".pyc") for f in all_files), \
                    f"Pattern {pattern} failed: found .pyc files in {all_files}"
            else:
                assert not any(check_string in str(f) for f in all_files), \
                    f"Pattern {pattern} failed: found {check_string} in {all_files}"

    def test_no_ignore_patterns_scans_everything(self):
        """Test that without ignore patterns, all directories are scanned."""
        test_path = Path(__file__).parent / "test_data" / "ignore_patterns_test"

        # Scan without any ignore patterns
        scanner = DependencyScanner(ignore_patterns=[])

        result = scanner.scan_project(project_path=str(test_path))

        # Check both dependency files and source files
        all_files = list(result.dependency_files)
        all_files.extend([Path(d.source_file) for d in result.dependencies if d.source_file])

        # Should find files when no patterns are ignored
        assert len(all_files) > 0, "Should scan files when no ignore patterns"

    def test_multiple_ignore_patterns_combined(self):
        """Test that multiple ignore patterns work together correctly."""
        test_path = Path(__file__).parent / "test_data" / "ignore_patterns_test"

        scanner = DependencyScanner(
            ignore_patterns=[".venv", ".venv-win", "__pycache__", "*.pyc", ".git"]
        )

        result = scanner.scan_project(project_path=str(test_path))

        # Check both dependency files and source files
        all_files = list(result.dependency_files)
        all_files.extend([Path(d.source_file) for d in result.dependencies if d.source_file])

        # Verify all patterns are applied
        for file_path in all_files:
            file_path = Path(file_path)
            parts = file_path.parts

            assert ".venv" not in parts
            assert ".venv-win" not in parts
            assert "__pycache__" not in parts
            assert ".git" not in parts
            assert not str(file_path).endswith(".pyc")

        # Should still find valid files
        assert any("valid_dir" in str(f) for f in all_files)
