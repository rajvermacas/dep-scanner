"""Tests for the API dependency classification functionality."""

import unittest
from unittest.mock import patch, MagicMock
import yaml

from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiAuthType
from dependency_scanner_tool.api_categorization import ApiDependencyClassifier
from dependency_scanner_tool.scanner import DependencyType


class TestApiDependencyClassifier(unittest.TestCase):
    """Test cases for ApiDependencyClassifier."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "api_dependency_patterns": {
                "allowed_urls": [
                    "https://api.example.com/v1/*",
                    "https://api.trusted-service.com/*"
                ],
                "restricted_urls": [
                    "https://api.restricted-service.com/*",
                    "http://*"
                ],
                "categories": {
                    "Public APIs": [
                        "https://api.public.com/*",
                        "https://api.example.com/v1/public/*"
                    ],
                    "Internal APIs": [
                        "https://api.internal.example.com/*",
                        "https://api.example.com/v1/internal/*"
                    ]
                }
            }
        }
        self.classifier = ApiDependencyClassifier(self.config)
    
    def test_initialization(self):
        """Test classifier initialization with config."""
        self.assertEqual(len(self.classifier.allowed_patterns), 2)
        self.assertEqual(len(self.classifier.restricted_patterns), 2)
        self.assertEqual(len(self.classifier.category_patterns), 2)
        
        # Test initialization with empty config
        empty_classifier = ApiDependencyClassifier({})
        self.assertEqual(len(empty_classifier.allowed_patterns), 0)
        self.assertEqual(len(empty_classifier.restricted_patterns), 0)
        self.assertEqual(len(empty_classifier.category_patterns), 0)
    
    def test_url_matches_pattern(self):
        """Test URL pattern matching."""
        # Test allowed pattern matching
        self.assertTrue(self.classifier._url_matches_pattern(
            "https://api.example.com/v1/users", 
            "https://api.example.com/v1/*"
        ))
        
        # Test restricted pattern matching
        self.assertTrue(self.classifier._url_matches_pattern(
            "http://api.example.com", 
            "http://*"
        ))
        
        # Test non-matching pattern
        self.assertFalse(self.classifier._url_matches_pattern(
            "https://api.other-service.com", 
            "https://api.example.com/*"
        ))
    
    def test_classify_api_call(self):
        """Test API call classification."""
        # Test allowed API call
        allowed_api = ApiCall(
            url="https://api.example.com/v1/users",
            http_method="GET",
            source_file="test.py",
            line_number=10
        )
        self.assertEqual(self.classifier.classify_api_call(allowed_api), DependencyType.ALLOWED)
        
        # Test restricted API call
        restricted_api = ApiCall(
            url="https://api.restricted-service.com/data",
            http_method="POST",
            source_file="test.py",
            line_number=20
        )
        self.assertEqual(self.classifier.classify_api_call(restricted_api), DependencyType.RESTRICTED)
        
        # Test restricted HTTP (non-HTTPS) API call
        http_api = ApiCall(
            url="http://api.example.com/v1/users",
            http_method="GET",
            source_file="test.py",
            line_number=30
        )
        self.assertEqual(self.classifier.classify_api_call(http_api), DependencyType.RESTRICTED)
        
        # Test unknown API call
        unknown_api = ApiCall(
            url="https://api.unknown-service.com/data",
            http_method="GET",
            source_file="test.py",
            line_number=40
        )
        self.assertEqual(self.classifier.classify_api_call(unknown_api), DependencyType.UNKNOWN)
    
    def test_categorize_api_call(self):
        """Test API call categorization."""
        # Test Public API
        public_api = ApiCall(
            url="https://api.public.com/users",
            http_method="GET",
            source_file="test.py",
            line_number=10
        )
        self.assertEqual(self.classifier.categorize_api_call(public_api), ["Public APIs"])
        
        # Test Internal API
        internal_api = ApiCall(
            url="https://api.example.com/v1/internal/users",
            http_method="POST",
            source_file="test.py",
            line_number=20
        )
        self.assertEqual(self.classifier.categorize_api_call(internal_api), ["Internal APIs"])
        
        # Test uncategorized API
        uncategorized_api = ApiCall(
            url="https://api.unknown-service.com/data",
            http_method="GET",
            source_file="test.py",
            line_number=30
        )
        self.assertEqual(self.classifier.categorize_api_call(uncategorized_api), ["Uncategorized"])
    
    def test_categorize_api_calls(self):
        """Test categorization of multiple API calls."""
        api_calls = [
            ApiCall(
                url="https://api.public.com/users",
                http_method="GET",
                source_file="test.py",
                line_number=10
            ),
            ApiCall(
                url="https://api.example.com/v1/internal/users",
                http_method="POST",
                source_file="test.py",
                line_number=20
            ),
            ApiCall(
                url="https://api.unknown-service.com/data",
                http_method="GET",
                source_file="test.py",
                line_number=30
            )
        ]
        
        categorized = self.classifier.categorize_api_calls(api_calls)
        
        self.assertEqual(len(categorized), 3)  # Public, Internal, Uncategorized
        self.assertEqual(len(categorized["Public APIs"]), 1)
        self.assertEqual(len(categorized["Internal APIs"]), 1)
        self.assertEqual(len(categorized["Uncategorized"]), 1)


if __name__ == "__main__":
    unittest.main() 