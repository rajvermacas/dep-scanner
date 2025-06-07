"""Module for categorizing API dependencies based on URL patterns."""

import fnmatch
import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Set, TYPE_CHECKING

from dependency_scanner_tool.api_analyzers.base import ApiCall


logger = logging.getLogger(__name__)


class ApiDependencyClassifier:
    """Classifies API dependencies based on URL patterns."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the API dependency classifier.
        
        Args:
            config: Configuration dictionary containing API URL patterns.
                   Expected format: {
                       "categories": {
                           "Category1": {
                               "api_patterns": ["pattern1", "pattern2"],
                               "status": "allowed"
                           },
                           "Category2": {
                               "api_patterns": ["pattern3"],
                               "status": "restricted"
                           }
                       }
                   }
                   Or legacy format: {
                       "api_dependency_patterns": {
                           "allowed_urls": ["pattern1", "pattern2"],
                           "restricted_urls": ["pattern3"],
                           "categories": {
                               "Category1": ["pattern4", "pattern5"],
                               "Category2": ["pattern6"]
                           }
                       }
                   }
        """
        self.allowed_patterns: List[str] = []
        self.restricted_patterns: List[str] = []
        self.category_patterns: Dict[str, List[str]] = {}
        
        # Handle new unified structure
        if config and "categories" in config:
            for category_name, category_data in config["categories"].items():
                if isinstance(category_data, dict):
                    api_patterns = category_data.get("api_patterns", [])
                    if api_patterns:
                        self.category_patterns[category_name] = api_patterns
                        
                        # Add patterns to allowed/restricted based on status
                        status = category_data.get("status", "cannot_determine")
                        if status == "allowed":
                            self.allowed_patterns.extend(api_patterns)
                        elif status == "restricted":
                            self.restricted_patterns.extend(api_patterns)
            
            print(f"DEBUG: LOADED category_patterns: {self.category_patterns}")
            logger.info(f"Initialized API dependency classifier with {len(self.allowed_patterns)} allowed patterns, "
                       f"{len(self.restricted_patterns)} restricted patterns, and "
                       f"{len(self.category_patterns)} category patterns")
        
        # Handle legacy structure for backward compatibility
        elif config and "api_dependency_patterns" in config:
            api_config = config["api_dependency_patterns"]
            self.allowed_patterns = api_config.get("allowed_urls", [])
            self.restricted_patterns = api_config.get("restricted_urls", [])
            self.category_patterns = api_config.get("categories", {})
            print(f"DEBUG: LOADED legacy category_patterns: {self.category_patterns}")
            logger.info(f"Initialized API dependency classifier with {len(self.allowed_patterns)} allowed patterns, "
                       f"{len(self.restricted_patterns)} restricted patterns, and "
                       f"{len(self.category_patterns)} category patterns")
        else:
            logger.info("Initialized API dependency classifier with no patterns")
    
    def _url_matches_pattern(self, url: str, pattern: str) -> bool:
        """Check if a URL matches a pattern.
        
        Args:
            url: The URL to check
            pattern: The pattern to match against
            
        Returns:
            True if the URL matches the pattern, False otherwise
        """
        # Convert glob pattern to regex pattern
        # Replace * with .* and escape other special regex characters
        regex_pattern = fnmatch.translate(pattern)
        match = re.match(regex_pattern, url)
        return bool(match)
    
    def classify_api_call(self, api_call: ApiCall) -> str:
        """Classify an API call based on the configured patterns.
        
        Args:
            api_call: API call to classify
            
        Returns:
            Classification of the API call as a string: 'allowed', 'restricted', or 'cannot_determine'
        """
        url = api_call.url
        
        # Check if the URL matches any allowed pattern
        for pattern in self.allowed_patterns:
            if self._url_matches_pattern(url, pattern):
                return "allowed"
        
        # Check if the URL matches any restricted pattern
        for pattern in self.restricted_patterns:
            if self._url_matches_pattern(url, pattern):
                return "restricted"
        
        return "cannot_determine"
    
    def categorize_api_call(self, api_call: ApiCall) -> List[str]:
        """Categorize an API call based on the configured category patterns.
        
        Args:
            api_call: API call to categorize
            
        Returns:
            List of category names the API call belongs to, or ["Uncategorized"] if none
        """
        url = api_call.url
        matching_categories = []
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                match = self._url_matches_pattern(url, pattern)
                print(f"DEBUG: Checking if URL '{url}' matches pattern '{pattern}' for category '{category}': {match}")
                if match:
                    matching_categories.append(category)
                    break
        return matching_categories if matching_categories else ["Uncategorized"]
    
    def categorize_api_calls(self, api_calls: List[ApiCall]) -> Dict[str, List[ApiCall]]:
        """Categorize multiple API calls.
        
        Args:
            api_calls: List of API calls to categorize
            
        Returns:
            Dictionary mapping category names to lists of API calls
        """
        # Debug: print all URLs and patterns
        print(f"DEBUG: Categorizing API calls: {[api_call.url for api_call in api_calls]}")
        print(f"DEBUG: Using category patterns: {self.category_patterns}")
        # Start with all categories from config and 'Uncategorized', all with empty lists
        all_categories = set(self.category_patterns.keys()) | {"Uncategorized"}
        categorized = {category: [] for category in all_categories}
        for api_call in api_calls:
            categories = self.categorize_api_call(api_call)
            for category in categories:
                categorized[category].append(api_call)
        logger.info(f"Categorized {len(api_calls)} API calls into {len(categorized)} categories")
        return categorized
