"""Tests for the JSON reporter module."""

import json
import os
import tempfile
import unittest
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from dependency_scanner_tool.reporters.json_reporter import JSONReporter
from dependency_scanner_tool.scanner import ScanResult, Dependency, DependencyType


class TestJSONReporter(unittest.TestCase):
    """Test cases for the JSONReporter class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample scan result
        self.scan_result = ScanResult(
            languages={"Python": 75.5, "JavaScript": 24.5},
            package_managers={"pip", "npm"},
            dependency_files=[Path("/path/to/requirements.txt"), Path("/path/to/package.json")],
            dependencies=[
                Dependency(
                    name="requests",
                    version="2.28.1",
                    source_file="/path/to/requirements.txt",
                    dependency_type=DependencyType.ALLOWED
                ),
                Dependency(
                    name="flask",
                    version="2.0.1",
                    source_file="/path/to/requirements.txt",
                    dependency_type=DependencyType.UNKNOWN
                ),
                Dependency(
                    name="insecure-package",
                    version="1.0.0",
                    source_file="/path/to/package.json",
                    dependency_type=DependencyType.RESTRICTED
                ),
                Dependency(
                    name="internal-tool",
                    version="0.1.0",
                    source_file="/path/to/requirements.txt",
                    dependency_type=DependencyType.UNKNOWN # Type will be updated by categorization
                ),
                Dependency(
                    name="utility-lib",
                    version="1.2.3",
                    source_file="/path/to/package.json",
                    dependency_type=DependencyType.UNKNOWN
                )
            ],
            errors=["Error parsing file: /path/to/broken.txt"]
        )

        self.sample_dict_category_config = {
            "categories": {
                "Internal Tools": {
                    "dependencies": ["internal-tool", "another-internal-*"],
                    "description": "Tools developed and used internally."
                },
                "Utilities": {
                    "dependencies": ["utility-lib"],
                    "description": "Common utility libraries."
                }
            }
        }

    def test_convert_to_dict(self):
        """Test converting a ScanResult to a dictionary."""
        reporter = JSONReporter()
        result_dict = reporter._convert_to_dict(self.scan_result)
        
        # Check the structure of the dictionary
        self.assertIn("scan_summary", result_dict)
        self.assertIn("languages", result_dict["scan_summary"])
        self.assertIn("package_managers", result_dict["scan_summary"])
        self.assertIn("dependency_count", result_dict["scan_summary"])
        self.assertIn("error_count", result_dict["scan_summary"])
        
        self.assertIn("dependency_files", result_dict)
        self.assertIn("dependencies", result_dict)
        self.assertIn("errors", result_dict)
        
        # Check the values
        self.assertEqual(result_dict["scan_summary"]["languages"]["Python"], 75.5)
        self.assertEqual(result_dict["scan_summary"]["languages"]["JavaScript"], 24.5)
        self.assertEqual(set(result_dict["scan_summary"]["package_managers"]), {"pip", "npm"})
        self.assertEqual(result_dict["scan_summary"]["dependency_count"], 3)
        self.assertEqual(result_dict["scan_summary"]["error_count"], 1)
        
        self.assertEqual(len(result_dict["dependency_files"]), 2)
        self.assertEqual(len(result_dict["dependencies"]), 3)
        self.assertEqual(len(result_dict["errors"]), 1)
        
        # Check dependency serialization
        dep = result_dict["dependencies"][0]
        self.assertIn("name", dep)
        self.assertIn("version", dep)
        self.assertIn("source_file", dep)
        self.assertIn("type", dep)

    def test_generate_report_string(self):
        """Test generating a JSON report as a string."""
        reporter = JSONReporter()
        json_output = reporter.generate_report(self.scan_result)
        
        # Verify the output is valid JSON
        result_dict = json.loads(json_output)
        
        # Check the structure
        self.assertIn("scan_summary", result_dict)
        self.assertIn("dependency_files", result_dict)
        self.assertIn("dependencies", result_dict)
        self.assertIn("errors", result_dict)

    def test_generate_report_file(self):
        """Test generating a JSON report to a file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            # Generate the report
            reporter = JSONReporter(output_path=tmp_path)
            reporter.generate_report(self.scan_result)
            
            # Verify the file exists and contains valid JSON
            self.assertTrue(tmp_path.exists())
            
            with open(tmp_path, 'r') as f:
                result_dict = json.load(f)
            
            # Check the structure
            self.assertIn("scan_summary", result_dict)
            self.assertIn("dependency_files", result_dict)
            self.assertIn("dependencies", result_dict)
            self.assertIn("errors", result_dict)
        finally:
            # Clean up
            if tmp_path.exists():
                os.unlink(tmp_path)

    @patch('dependency_scanner_tool.reporters.json_reporter.open')
    def test_generate_report_file_error(self, mock_open):
        """Test error handling when writing to a file fails."""
        # Configure logger to capture logs
        logger = logging.getLogger('dependency_scanner_tool.reporters.json_reporter')
        original_level = logger.level
        logger.setLevel(logging.ERROR)
        
        # Create a handler that captures log records
        log_capture = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())
        
        handler = TestHandler()
        logger.addHandler(handler)
        
        try:
            # Mock open to raise an IOError
            mock_open.side_effect = IOError("Failed to write file")
            
            # Create a reporter with a mock output path
            reporter = JSONReporter(output_path=Path("/path/to/output.json"))
            
            # Generate the report, which should still return the JSON string
            # even though writing to the file failed
            json_output = reporter.generate_report(self.scan_result)
            
            # Check that the error was logged
            self.assertTrue(any("Failed to write JSON report" in msg for msg in log_capture))
            
            # Verify the output is still valid JSON
            result_dict = json.loads(json_output)
            self.assertIn("scan_summary", result_dict)
        finally:
            # Restore original logger configuration
            logger.removeHandler(handler)
            logger.setLevel(original_level)

    def test_generate_report_with_dict_category_config(self):
        """Test generating a report with category_config as a dictionary."""
        reporter = JSONReporter(category_config=self.sample_dict_category_config)

        # Modify a local ScanResult for this test to have specific dependencies
        # for categorization by the dict config.
        test_scan_result = ScanResult(
            languages={"Python": 100.0},
            package_managers={"pip"},
            dependency_files=[Path("/path/to/requirements.txt")],
            dependencies=[
                Dependency(name="internal-tool", version="0.1.0", source_file="/path/to/requirements.txt"),
                Dependency(name="utility-lib", version="1.2.3", source_file="/path/to/requirements.txt"),
                Dependency(name="requests", version="2.28.1", source_file="/path/to/requirements.txt"), # Uncategorized
            ],
            errors=[]
        )

        json_output = reporter.generate_report(test_scan_result)
        result_dict = json.loads(json_output)

        self.assertIn("categorized_dependencies", result_dict)
        self.assertIn("Internal Tools", result_dict["categorized_dependencies"])
        self.assertIn("Utilities", result_dict["categorized_dependencies"])

        internal_deps = result_dict["categorized_dependencies"]["Internal Tools"]
        utility_deps = result_dict["categorized_dependencies"]["Utilities"]

        self.assertEqual(len(internal_deps), 1)
        self.assertEqual(internal_deps[0]["name"], "internal-tool")

        self.assertEqual(len(utility_deps), 1)
        self.assertEqual(utility_deps[0]["name"], "utility-lib")

        # Check unified_categories as well
        self.assertIn("unified_categories", result_dict)
        self.assertIn("Internal Tools", result_dict["unified_categories"])
        self.assertIn("Utilities", result_dict["unified_categories"])

        unified_internal = result_dict["unified_categories"]["Internal Tools"]
        unified_utilities = result_dict["unified_categories"]["Utilities"]

        self.assertEqual(len(unified_internal["dependencies"]), 1)
        self.assertEqual(unified_internal["dependencies"][0]["name"], "internal-tool")
        self.assertEqual(len(unified_internal["api_calls"]), 0) # No API calls in this test

        self.assertEqual(len(unified_utilities["dependencies"]), 1)
        self.assertEqual(unified_utilities["dependencies"][0]["name"], "utility-lib")
        self.assertEqual(len(unified_utilities["api_calls"]), 0)


if __name__ == '__main__':
    unittest.main()
