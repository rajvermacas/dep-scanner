"""Test that scanner_worker correctly detects categories from API calls."""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from dependency_scanner_tool.api.scanner_worker import ScannerWorker
from dependency_scanner_tool.scanner import ScanResult
from dependency_scanner_tool.api_analyzers.base import ApiCall


class TestScannerWorkerApiCategorization(unittest.TestCase):
    """Test scanner worker API call categorization."""

    def test_categorize_dependencies_includes_api_calls(self):
        """Test that _categorize_dependencies marks categories with API calls as Found."""

        # Create mock scan result with API calls but NO dependencies
        api_calls = [
            ApiCall(
                url="https://util.com/test",
                http_method="GET",
                source_file="test.txt",
                line_number=1,
                status="allowed"
            )
        ]

        categorized_api_calls = {
            "Util": [api_calls[0]],
        }

        scan_result = ScanResult(
            languages={"Python": 100.0},
            package_managers=set(),
            dependency_files=[],
            dependencies=[],  # NO dependencies
            api_calls=api_calls,
            categorized_api_calls=categorized_api_calls,
            errors=[]
        )

        # Create worker and test categorization
        worker = ScannerWorker("test-job", 0, "test-repo")
        category_flags = worker._categorize_dependencies(scan_result)

        # Util should be True because of the API call
        self.assertTrue(category_flags.get("Util", False),
                       "Util category should be True when API call is found")

    def test_categorize_dependencies_combines_deps_and_api_calls(self):
        """Test that categories are marked Found if they have EITHER dependencies OR API calls."""
        from dependency_scanner_tool.scanner import Dependency, DependencyType

        # Category with dependency only
        dependencies = [
            Dependency(
                name="pytest",
                version="7.0.0",
                source_file="requirements.txt",
                dependency_type=DependencyType.ALLOWED
            )
        ]

        # Category with API call only
        api_calls = [
            ApiCall(
                url="https://util.com/test",
                http_method="GET",
                source_file="test.txt",
                line_number=1,
                status="allowed"
            )
        ]

        categorized_api_calls = {
            "Util": [api_calls[0]],
        }

        scan_result = ScanResult(
            languages={"Python": 100.0},
            package_managers=set(),
            dependency_files=[],
            dependencies=dependencies,
            api_calls=api_calls,
            categorized_api_calls=categorized_api_calls,
            errors=[]
        )

        worker = ScannerWorker("test-job", 0, "test-repo")
        category_flags = worker._categorize_dependencies(scan_result)

        # Both categories should be True
        self.assertTrue(category_flags.get("Util", False),
                       "Util should be True (has API call)")
        self.assertTrue(category_flags.get("Data Science", False),
                       "Data Science should be True (has dependency)")

    def test_categorize_dependencies_ignores_uncategorized(self):
        """Test that 'Uncategorized' API calls don't create a category."""

        api_calls = [
            ApiCall(
                url="https://unknown.example.com/api",
                http_method="GET",
                source_file="test.txt",
                line_number=1,
                status="cannot_determine"
            )
        ]

        categorized_api_calls = {
            "Uncategorized": [api_calls[0]],
        }

        scan_result = ScanResult(
            languages={"Python": 100.0},
            package_managers=set(),
            dependency_files=[],
            dependencies=[],
            api_calls=api_calls,
            categorized_api_calls=categorized_api_calls,
            errors=[]
        )

        worker = ScannerWorker("test-job", 0, "test-repo")
        category_flags = worker._categorize_dependencies(scan_result)

        # "Uncategorized" should not be in category_flags
        self.assertNotIn("Uncategorized", category_flags,
                        "Uncategorized should not appear in category flags")


if __name__ == "__main__":
    unittest.main()
