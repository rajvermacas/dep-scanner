"""Tests for HTML report generation with API categorization."""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from dependency_scanner_tool.scanner import ScanResult, DependencyType
from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiAuthType
from dependency_scanner_tool.reporters.html_reporter import HTMLReporter


class TestHtmlReportApiCategorization(unittest.TestCase):
    """Test cases for HTML report generation with API categorization."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample API calls
        self.api_calls = [
            ApiCall(
                url="https://api.example.com/v1/users",
                http_method="GET",
                source_file="test.py",
                line_number=10,
                dependency_type=DependencyType.ALLOWED
            ),
            ApiCall(
                url="https://api.public.com/users",
                http_method="GET",
                source_file="test.py",
                line_number=20,
                dependency_type=DependencyType.UNKNOWN
            ),
            ApiCall(
                url="http://api.insecure.com/data",
                http_method="POST",
                source_file="test.py",
                line_number=30,
                dependency_type=DependencyType.RESTRICTED
            )
        ]
        
        # Create categorized API calls
        self.categorized_api_calls = {
            "Public APIs": [self.api_calls[1]],
            "Internal APIs": [self.api_calls[0]],
            "Uncategorized": [self.api_calls[2]]
        }
        
        # Create a mock scan result
        self.scan_result = ScanResult(
            languages={"Python": 100.0},
            package_managers=set(["pip"]),
            dependency_files=[Path("requirements.txt")],
            dependencies=[],
            api_calls=self.api_calls,
            categorized_api_calls=self.categorized_api_calls,
            errors=[]
        )
        
        # Create a temporary config file
        self.config_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        self.config_file.write("""
allowed_categories:
  - "Public APIs"

restricted_categories:
  - "Internal APIs"

ignore_patterns:
  - ".venv"
  - "__pycache__"
  - "*.pyc"
  - ".git"

api_dependency_patterns:
  allowed_urls:
    - "https://api.example.com/v1/*"
  
  restricted_urls:
    - "http://*"
  
  categories:
    "Public APIs":
      - "https://api.public.com/*"
    "Internal APIs":
      - "https://api.example.com/*"
""")
        self.config_file.flush()
        self.config_file.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary config file
        Path(self.config_file.name).unlink()
    
    def test_html_report_includes_api_categorization(self):
        """Test that HTML report includes API categorization."""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
            output_path = Path(temp_html.name)
        
        try:
            # Create a JSON reporter with our scan result
            with patch('yaml.safe_load') as mock_yaml_load:
                # Mock the config loading in the HTMLReporter
                with open(self.config_file.name, 'r') as f:
                    mock_yaml_load.return_value = {"allowed_categories": ["Public APIs"], "restricted_categories": ["Internal APIs"]}
                
                # Create the reporter
                reporter = HTMLReporter(output_path=output_path)
                
                # Generate the report
                html_output = reporter.generate_report(self.scan_result)
                
                # Verify that the report contains API calls
                self.assertIn("REST API Calls", html_output)
                
                # Verify that the report contains API categorization
                self.assertIn("Public APIs", html_output)
                self.assertIn("Internal APIs", html_output)
                
                # Verify that the report contains API status
                self.assertIn("badge-allowed", html_output)
                self.assertIn("badge-restricted", html_output)
                
                # Verify that specific URLs are in the report
                self.assertIn("https://api.example.com/v1/users", html_output)
                self.assertIn("https://api.public.com/users", html_output)
                self.assertIn("http://api.insecure.com/data", html_output)
        finally:
            # Clean up the temporary HTML file
            output_path.unlink()


if __name__ == "__main__":
    unittest.main() 