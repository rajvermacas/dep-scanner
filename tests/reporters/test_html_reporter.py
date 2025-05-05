"""Tests for the HTML reporter module."""

import json
import os
import tempfile
import unittest
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import jinja2

from dependency_scanner_tool.reporters.html_reporter import HTMLReporter
from dependency_scanner_tool.scanner import ScanResult, Dependency, DependencyType


class TestHTMLReporter(unittest.TestCase):
    """Test cases for the HTMLReporter class."""

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
                )
            ],
            errors=["Error parsing file: /path/to/broken.txt"]
        )
        
        # Create a sample JSON string
        self.json_data = json.dumps({
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
        })

    @patch('dependency_scanner_tool.reporters.html_reporter.jinja2.Environment')
    def test_get_template_default(self, mock_env):
        """Test getting the default template."""
        # Mock the Jinja2 environment
        mock_template = MagicMock()
        mock_env_instance = MagicMock()
        mock_env.return_value = mock_env_instance
        mock_env_instance.get_template.return_value = mock_template
        
        # Create a reporter
        reporter = HTMLReporter()
        
        # Get the template
        template = reporter._get_template()
        
        # Verify the template was retrieved from the environment
        mock_env_instance.get_template.assert_called_once_with('report.html')
        self.assertEqual(template, mock_template)

    @patch('dependency_scanner_tool.reporters.html_reporter.jinja2.Environment')
    def test_get_template_custom(self, mock_env):
        """Test getting a custom template."""
        # Create a temporary file with a custom template
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as tmp:
            tmp_path = Path(tmp.name)
            tmp.write('<html>{{ title }}</html>')
        
        try:
            # Mock the Jinja2 environment
            mock_env_instance = MagicMock()
            mock_env.return_value = mock_env_instance
            mock_env_instance.from_string.return_value = 'custom_template'
            
            # Create a reporter with the custom template
            reporter = HTMLReporter(template_path=tmp_path)
            
            # Get the template
            template = reporter._get_template()
            
            # Verify the template was created from the string
            self.assertEqual(mock_env_instance.from_string.call_count, 1)
            self.assertEqual(template, 'custom_template')
        finally:
            # Clean up
            if tmp_path.exists():
                os.unlink(tmp_path)

    @patch('dependency_scanner_tool.reporters.html_reporter.jinja2.Environment')
    def test_get_template_fallback(self, mock_env):
        """Test fallback to basic template when default is not found."""
        # Mock the Jinja2 environment to raise TemplateNotFound
        mock_env_instance = MagicMock()
        mock_env.return_value = mock_env_instance
        mock_env_instance.get_template.side_effect = jinja2.exceptions.TemplateNotFound('report.html')
        mock_env_instance.from_string.return_value = 'basic_template'
        
        # Create a reporter
        reporter = HTMLReporter()
        
        # Configure logger to capture logs
        logger = logging.getLogger('dependency_scanner_tool.reporters.html_reporter')
        original_level = logger.level
        logger.setLevel(logging.WARNING)
        
        # Create a handler that captures log records
        log_capture = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())
        
        handler = TestHandler()
        logger.addHandler(handler)
        
        try:
            # Get the template, which should fall back to the basic template
            template = reporter._get_template()
            
            # Check that the warning was logged
            self.assertTrue(any("Default template not found" in msg for msg in log_capture))
            
            # Verify the basic template was used
            self.assertEqual(mock_env_instance.from_string.call_count, 1)
            self.assertEqual(template, 'basic_template')
        finally:
            # Restore original logger configuration
            logger.removeHandler(handler)
            logger.setLevel(original_level)

    @patch('dependency_scanner_tool.reporters.html_reporter.HTMLReporter._get_template')
    def test_generate_report_from_scan_result(self, mock_get_template):
        """Test generating an HTML report from a ScanResult object."""
        # Mock the template
        mock_template = MagicMock()
        mock_template.render.return_value = '<html>Report</html>'
        mock_get_template.return_value = mock_template
        
        # Create a reporter
        reporter = HTMLReporter()
        
        # Generate the report
        html_output = reporter.generate_report(self.scan_result, title="Test Report")
        
        # Verify the template was rendered with the correct data
        mock_template.render.assert_called_once()
        args, kwargs = mock_template.render.call_args
        self.assertEqual(kwargs['title'], "Test Report")
        self.assertIn('data', kwargs)
        self.assertIn('dependency_count', kwargs)
        self.assertIn('error_count', kwargs)
        self.assertIn('languages', kwargs)
        self.assertIn('package_managers', kwargs)
        
        # Verify the output
        self.assertEqual(html_output, '<html>Report</html>')

    @patch('dependency_scanner_tool.reporters.html_reporter.HTMLReporter._get_template')
    def test_generate_report_from_json_string(self, mock_get_template):
        """Test generating an HTML report from a JSON string."""
        # Mock the template
        mock_template = MagicMock()
        mock_template.render.return_value = '<html>Report</html>'
        mock_get_template.return_value = mock_template
        
        # Create a reporter
        reporter = HTMLReporter()
        
        # Generate the report
        html_output = reporter.generate_report(self.json_data, title="Test Report")
        
        # Verify the template was rendered with the correct data
        mock_template.render.assert_called_once()
        args, kwargs = mock_template.render.call_args
        self.assertEqual(kwargs['title'], "Test Report")
        self.assertIn('data', kwargs)
        
        # Verify the output
        self.assertEqual(html_output, '<html>Report</html>')

    @patch('dependency_scanner_tool.reporters.html_reporter.HTMLReporter._get_template')
    def test_generate_report_to_file(self, mock_get_template):
        """Test generating an HTML report to a file."""
        # Mock the template
        mock_template = MagicMock()
        mock_template.render.return_value = '<html>Report</html>'
        mock_get_template.return_value = mock_template
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            # Create a reporter with the output path
            reporter = HTMLReporter(output_path=tmp_path)
            
            # Generate the report
            html_output = reporter.generate_report(self.scan_result, title="Test Report")
            
            # Verify the file exists and contains the HTML
            self.assertTrue(tmp_path.exists())
            
            with open(tmp_path, 'r') as f:
                file_content = f.read()
            
            self.assertEqual(file_content, '<html>Report</html>')
        finally:
            # Clean up
            if tmp_path.exists():
                os.unlink(tmp_path)

    @patch('dependency_scanner_tool.reporters.html_reporter.HTMLReporter._get_template')
    @patch('dependency_scanner_tool.reporters.html_reporter.open')
    def test_generate_report_file_error(self, mock_open, mock_get_template):
        """Test error handling when writing to a file fails."""
        # Mock the template
        mock_template = MagicMock()
        mock_template.render.return_value = '<html>Report</html>'
        mock_get_template.return_value = mock_template
        
        # Configure logger to capture logs
        logger = logging.getLogger('dependency_scanner_tool.reporters.html_reporter')
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
            # Mock open to raise a FileNotFoundError
            mock_open.side_effect = FileNotFoundError("File not found")
            
            # Create a reporter with a mock output path
            reporter = HTMLReporter(output_path=Path("/path/to/output.html"))
            
            # Generate the report, which should still return the HTML string
            # even though writing to the file failed
            html_output = reporter.generate_report(self.scan_result)
            
            # Check that the error was logged
            self.assertTrue(any("Failed to write HTML report" in msg for msg in log_capture))
            
            # Verify the output is still the HTML string
            self.assertEqual(html_output, '<html>Report</html>')
        finally:
            # Restore original logger configuration
            logger.removeHandler(handler)
            logger.setLevel(original_level)

    def test_generate_report_invalid_input(self):
        """Test error handling with invalid input."""
        # Create a reporter
        reporter = HTMLReporter()
        
        # Try to generate a report with an invalid input
        with self.assertRaises(ValueError):
            reporter.generate_report(123)  # Not a ScanResult, JSON string, or file path


if __name__ == '__main__':
    unittest.main()
