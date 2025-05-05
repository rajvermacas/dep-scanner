"""Tests for the HTML report generator CLI script."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dependency_scanner_tool.html_report import main


class TestHTMLReportCLI(unittest.TestCase):
    """Test cases for the HTML report generator CLI script."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample JSON data
        self.json_data = {
            "scan_summary": {
                "languages": {"Python": 75.5, "JavaScript": 24.5},
                "package_managers": ["pip", "npm"],
                "dependency_count": 3,
                "error_count": 1
            },
            "dependency_files": [
                "/path/to/requirements.txt",
                "/path/to/package.json"
            ],
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.28.1",
                    "source_file": "/path/to/requirements.txt",
                    "type": "allowed"
                },
                {
                    "name": "flask",
                    "version": "2.0.1",
                    "source_file": "/path/to/requirements.txt",
                    "type": "unknown"
                },
                {
                    "name": "insecure-package",
                    "version": "1.0.0",
                    "source_file": "/path/to/package.json",
                    "type": "restricted"
                }
            ],
            "errors": ["Error parsing file: /path/to/broken.txt"]
        }

    @patch('dependency_scanner_tool.html_report.argparse.ArgumentParser.parse_args')
    @patch('dependency_scanner_tool.html_report.HTMLReporter')
    def test_main_success(self, mock_reporter_class, mock_parse_args):
        """Test successful execution of the main function."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_json:
            tmp_json_path = Path(tmp_json.name)
            json.dump(self.json_data, tmp_json)
        
        # Create a temporary output file
        tmp_html_path = Path(tempfile.gettempdir()) / "test_report.html"
        
        try:
            # Mock the argument parser
            mock_args = MagicMock()
            mock_args.json_file = str(tmp_json_path)
            mock_args.output = str(tmp_html_path)
            mock_args.title = "Test Report"
            mock_args.template = None
            mock_parse_args.return_value = mock_args
            
            # Mock the HTMLReporter
            mock_reporter = MagicMock()
            mock_reporter_class.return_value = mock_reporter
            
            # Run the main function
            main()
            
            # Verify the reporter was created with the correct arguments
            mock_reporter_class.assert_called_once_with(
                output_path=Path(str(tmp_html_path)),
                template_path=None
            )
            
            # Verify the generate_report method was called with the correct arguments
            mock_reporter.generate_report.assert_called_once_with(
                tmp_json_path,
                title="Test Report"
            )
        finally:
            # Clean up
            if tmp_json_path.exists():
                os.unlink(tmp_json_path)
            if tmp_html_path.exists():
                os.unlink(tmp_html_path)

    @patch('dependency_scanner_tool.html_report.argparse.ArgumentParser.parse_args')
    @patch('dependency_scanner_tool.html_report.HTMLReporter')
    def test_main_with_custom_template(self, mock_reporter_class, mock_parse_args):
        """Test main function with a custom template."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_json:
            tmp_json_path = Path(tmp_json.name)
            json.dump(self.json_data, tmp_json)
        
        # Create a temporary template file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as tmp_template:
            tmp_template_path = Path(tmp_template.name)
            tmp_template.write('<html>{{ title }}</html>')
        
        # Create a temporary output file
        tmp_html_path = Path(tempfile.gettempdir()) / "test_report.html"
        
        try:
            # Mock the argument parser
            mock_args = MagicMock()
            mock_args.json_file = str(tmp_json_path)
            mock_args.output = str(tmp_html_path)
            mock_args.title = "Test Report"
            mock_args.template = str(tmp_template_path)
            mock_parse_args.return_value = mock_args
            
            # Mock the HTMLReporter
            mock_reporter = MagicMock()
            mock_reporter_class.return_value = mock_reporter
            
            # Run the main function
            main()
            
            # Verify the reporter was created with the correct arguments
            # Use str() to ensure consistent comparison
            mock_reporter_class.assert_called_once_with(
                output_path=Path(str(tmp_html_path)),
                template_path=Path(str(tmp_template_path))
            )
            
            # Verify the generate_report method was called with the correct arguments
            mock_reporter.generate_report.assert_called_once_with(
                tmp_json_path,
                title="Test Report"
            )
        finally:
            # Clean up
            if tmp_json_path.exists():
                os.unlink(tmp_json_path)
            if tmp_template_path.exists():
                os.unlink(tmp_template_path)
            if tmp_html_path.exists():
                os.unlink(tmp_html_path)

    @patch('dependency_scanner_tool.html_report.argparse.ArgumentParser.parse_args')
    @patch('dependency_scanner_tool.html_report.HTMLReporter')
    @patch('dependency_scanner_tool.html_report.sys.exit')
    def test_main_json_file_not_found(self, mock_exit, mock_reporter_class, mock_parse_args):
        """Test error handling when the JSON file is not found."""
        # Mock the argument parser
        mock_args = MagicMock()
        mock_args.json_file = "/path/to/nonexistent.json"
        mock_args.output = "report.html"
        mock_args.title = "Test Report"
        mock_args.template = None
        mock_parse_args.return_value = mock_args
        
        # Run the main function
        with self.assertLogs(level='ERROR') as cm:
            main()
            
            # Check that the error was logged
            self.assertTrue(any("JSON file not found" in msg for msg in cm.output))
            
            # Verify sys.exit was called with exit code 1
            mock_exit.assert_called_once_with(1)

    @patch('dependency_scanner_tool.html_report.argparse.ArgumentParser.parse_args')
    @patch('dependency_scanner_tool.html_report.HTMLReporter')
    @patch('dependency_scanner_tool.html_report.sys.exit')
    def test_main_html_generation_error(self, mock_exit, mock_reporter_class, mock_parse_args):
        """Test error handling when HTML generation fails."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_json:
            tmp_json_path = Path(tmp_json.name)
            json.dump(self.json_data, tmp_json)
        
        try:
            # Mock the argument parser
            mock_args = MagicMock()
            mock_args.json_file = str(tmp_json_path)
            mock_args.output = "report.html"
            mock_args.title = "Test Report"
            mock_args.template = None
            mock_parse_args.return_value = mock_args
            
            # Mock the HTMLReporter to raise an exception
            mock_reporter = MagicMock()
            mock_reporter.generate_report.side_effect = Exception("HTML generation failed")
            mock_reporter_class.return_value = mock_reporter
            
            # Run the main function
            with self.assertLogs(level='ERROR') as cm:
                main()
                
                # Check that the error was logged
                self.assertTrue(any("Error generating HTML report" in msg for msg in cm.output))
                
                # Verify sys.exit was called with exit code 1
                mock_exit.assert_called_once_with(1)
        finally:
            # Clean up
            if tmp_json_path.exists():
                os.unlink(tmp_json_path)


if __name__ == '__main__':
    unittest.main()
