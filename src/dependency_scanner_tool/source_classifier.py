"""Source classification for dependencies and API calls."""

import os
import re
from enum import Enum
from typing import Set, List, Optional
from urllib.parse import urlparse

class SourceType(Enum):
    """Enumeration for source types."""
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"

class SourceClassifier:
    """Classifies dependencies and API calls as internal or external."""
    
    def __init__(self, company_name: Optional[str] = None, internal_domains: Optional[Set[str]] = None):
        """Initialize the source classifier.
        
        Args:
            company_name: Company name to identify internal sources (defaults to env var COMPANY_NAME)
            internal_domains: Set of internal domain patterns (defaults to empty set)
        """
        self.company_name = company_name or os.getenv('COMPANY_NAME', 'starc')
        self.internal_domains = internal_domains or set()
        
        # Add company name as an internal domain pattern if provided
        if self.company_name:
            self.internal_domains.add(f"*{self.company_name}*")
    
    def classify_dependency(self, dependency_name: str) -> SourceType:
        """Classify a dependency as internal or external.
        
        Args:
            dependency_name: Name of the dependency to classify
            
        Returns:
            SourceType indicating if the dependency is internal or external
        """
        if not dependency_name:
            return SourceType.UNKNOWN
            
        # Check if dependency name contains company name
        if self.company_name and self.company_name.lower() in dependency_name.lower():
            return SourceType.INTERNAL
            
        # Check against internal domain patterns
        for pattern in self.internal_domains:
            if self._matches_pattern(dependency_name, pattern):
                return SourceType.INTERNAL
                
        return SourceType.EXTERNAL
    
    def classify_api_call(self, url: str) -> SourceType:
        """Classify an API call as internal or external.
        
        Args:
            url: URL of the API call to classify
            
        Returns:
            SourceType indicating if the API call is internal or external
        """
        if not url:
            return SourceType.UNKNOWN
            
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # If no domain was parsed, fall back to string matching
            if not domain:
                if self.company_name and self.company_name.lower() in url.lower():
                    return SourceType.INTERNAL
                return SourceType.UNKNOWN
            
            # Check if domain contains company name
            if self.company_name and self.company_name.lower() in domain:
                return SourceType.INTERNAL
                
            # Check localhost/internal IP patterns
            if self._is_localhost_or_internal(domain):
                return SourceType.INTERNAL
                
            # Check against internal domain patterns
            for pattern in self.internal_domains:
                if self._matches_pattern(domain, pattern):
                    return SourceType.INTERNAL
                    
            return SourceType.EXTERNAL
            
        except Exception:
            # If URL parsing fails, check if company name is in the URL string
            if self.company_name and self.company_name.lower() in url.lower():
                return SourceType.INTERNAL
            return SourceType.UNKNOWN
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a pattern (supports wildcards).
        
        Args:
            text: Text to check
            pattern: Pattern to match against (supports * wildcards)
            
        Returns:
            True if text matches pattern, False otherwise
        """
        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace('*', '.*')
        regex_pattern = f'^{regex_pattern}$'
        
        try:
            return bool(re.match(regex_pattern, text.lower(), re.IGNORECASE))
        except re.error:
            # If regex compilation fails, do simple substring match
            return pattern.lower().replace('*', '') in text.lower()
    
    def _is_localhost_or_internal(self, domain: str) -> bool:
        """Check if domain is localhost or internal IP.
        
        Args:
            domain: Domain to check
            
        Returns:
            True if domain is localhost or internal IP, False otherwise
        """
        if not domain:
            return False
            
        # Check for localhost variants
        localhost_patterns = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
        if any(pattern in domain for pattern in localhost_patterns):
            return True
            
        # Check for internal IP ranges
        internal_ip_patterns = [
            r'^10\.',           # 10.0.0.0/8
            r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',  # 172.16.0.0/12
            r'^192\.168\.',     # 192.168.0.0/16
        ]
        
        for pattern in internal_ip_patterns:
            if re.match(pattern, domain):
                return True
                
        return False