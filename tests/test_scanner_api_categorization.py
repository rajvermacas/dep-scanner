"""Integration tests for API dependency categorization in the scanner."""

import unittest
from unittest.mock import patch, MagicMock
import yaml
import tempfile
from pathlib import Path

from dependency_scanner_tool.scanner import DependencyScanner, DependencyType
from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiAuthType
from dependency_scanner_tool.api_categorization import ApiDependencyClassifier


class TestScannerApiCategorization(unittest.TestCase):
    """Test cases for API categorization in the scanner."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock API analyzer manager
        self.api_analyzer_manager = MagicMock()
        
        # Create sample API calls
        self.api_calls = [
            ApiCall(
                url="https://api.example.com/v1/users",
                http_method="GET",
                source_file="test.py",
                line_number=10
            ),
            ApiCall(
                url="https://api.public.com/users",
                http_method="GET",
                source_file="test.py",
                line_number=20
            ),
            ApiCall(
                url="http://api.insecure.com/data",
                http_method="POST",
                source_file="test.py",
                line_number=30
            )
        ]
        
        # Mock analyze_file to return the test API calls
        self.api_analyzer_manager.analyze_file.return_value = self.api_calls
        
        # Create a temporary config file
        self.config_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False)
        self.config_file.write(yaml.dump({
            "api_dependency_patterns": {
                "allowed_urls": [
                    "https://api.example.com/v1/*"
                ],
                "restricted_urls": [
                    "http://*"
                ],
                "categories": {
                    "Public APIs": [
                        "https://api.public.com/*"
                    ],
                    "Internal APIs": [
                        "https://api.example.com/*"
                    ]
                }
            }
        }))
        self.config_file.flush()
        self.config_file.close()
        
        # Create language detector and package manager detector mocks
        self.language_detector = MagicMock()
        self.language_detector.detect_languages.return_value = {"Python": 100.0}
        
        self.package_manager_detector = MagicMock()
        self.package_manager_detector.detect_package_managers.return_value = set(["pip"])
        
        # Create parser manager and analyzer manager mocks
        self.parser_manager = MagicMock()
        self.parser_manager.parse_files.return_value = {}
        
        self.analyzer_manager = MagicMock()
        self.analyzer_manager.analyze_file.return_value = []
        
        # Create a temporary directory for the test project
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)
        
        # Create a test source file
        (self.project_path / "test.py").touch()
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            # Remove the temporary config file
            Path(self.config_file.name).unlink(missing_ok=True)
        except (PermissionError, OSError):
            # On Windows, sometimes the file is still being used
            pass
        
        # Remove the temporary directory
        self.temp_dir.cleanup()
    
    def test_api_categorization_in_scanner(self):
        """Test that the scanner correctly categorizes API calls."""
        # Create the scanner with our mocks
        with patch('yaml.safe_load') as mock_yaml_load:
            # Mock the config loading in the scanner
            mock_yaml_load.return_value = yaml.safe_load(open(self.config_file.name, 'r'))
            test_config = mock_yaml_load.return_value
            from dependency_scanner_tool.api_categorization import ApiDependencyClassifier
            api_classifier = ApiDependencyClassifier(test_config)
            scanner = DependencyScanner(
                language_detector=self.language_detector,
                package_manager_detector=self.package_manager_detector,
                parser_manager=self.parser_manager,
                analyzer_manager=self.analyzer_manager,
                api_analyzer_manager=self.api_analyzer_manager,
                api_dependency_classifier=api_classifier
            )
            
            # Mock the _find_source_files and _find_api_scannable_files methods
            with patch.object(scanner, '_find_source_files') as mock_find_files, \
                 patch.object(scanner, '_find_api_scannable_files') as mock_find_api_files:
                mock_find_files.return_value = [self.project_path / "test.py"]
                mock_find_api_files.return_value = [self.project_path / "test.py"]

                # Run the scan
                scan_result = scanner.scan_project(str(self.project_path))
            
            # Verify that API calls were added to the result
            self.assertEqual(len(scan_result.api_calls), 3)
            
            # Verify that API calls were categorized
            self.assertIsNotNone(scan_result.categorized_api_calls)
            print('DEBUG categorized_api_calls:', scan_result.categorized_api_calls)
            self.assertEqual(len(scan_result.categorized_api_calls), 3)  # Public, Internal, Uncategorized
            
            # Verify correct categorization
            self.assertIn("Public APIs", scan_result.categorized_api_calls)
            self.assertIn("Internal APIs", scan_result.categorized_api_calls)
            
            # Verify that API calls were classified
            allowed_api = None
            restricted_api = None
            
            for api in scan_result.api_calls:
                if api.url == "https://api.example.com/v1/users":
                    allowed_api = api
                elif api.url == "http://api.insecure.com/data":
                    restricted_api = api
            
            self.assertIsNotNone(allowed_api)
            self.assertIsNotNone(restricted_api)
            self.assertEqual(allowed_api.dependency_type, DependencyType.ALLOWED)
            self.assertEqual(restricted_api.dependency_type, DependencyType.RESTRICTED)


if __name__ == "__main__":
    unittest.main() 