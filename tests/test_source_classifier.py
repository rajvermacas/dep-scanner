"""Tests for source classifier functionality."""

import os
import pytest
from unittest.mock import patch

from dependency_scanner_tool.source_classifier import SourceType, SourceClassifier


class TestSourceClassifier:
    """Test cases for SourceClassifier."""

    def test_init_default(self):
        """Test SourceClassifier initialization with defaults."""
        classifier = SourceClassifier()
        assert classifier.company_name == 'starc'  # Default value
        assert '*starc*' in classifier.internal_domains

    def test_init_with_company_name(self):
        """Test SourceClassifier initialization with custom company name."""
        classifier = SourceClassifier(company_name='mycompany')
        assert classifier.company_name == 'mycompany'
        assert '*mycompany*' in classifier.internal_domains

    @patch.dict(os.environ, {'COMPANY_NAME': 'envcompany'})
    def test_init_with_env_var(self):
        """Test SourceClassifier initialization from environment variable."""
        classifier = SourceClassifier()
        assert classifier.company_name == 'envcompany'
        assert '*envcompany*' in classifier.internal_domains

    def test_init_with_internal_domains(self):
        """Test SourceClassifier initialization with custom internal domains."""
        internal_domains = {'*.internal.com', '*.private.org'}
        classifier = SourceClassifier(
            company_name='testco', 
            internal_domains=internal_domains
        )
        assert classifier.internal_domains == internal_domains.union({'*testco*'})


class TestDependencyClassification:
    """Test cases for dependency classification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = SourceClassifier(company_name='starc')

    def test_classify_dependency_internal_company_name(self):
        """Test dependency classification with company name in dependency."""
        test_cases = [
            'starc-utils',
            'starc.core',
            'starc_common',
            'my-starc-lib',
            'STARC-TOOLS',  # Case insensitive
        ]
        
        for dep_name in test_cases:
            result = self.classifier.classify_dependency(dep_name)
            assert result == SourceType.INTERNAL, f"Failed for dependency: {dep_name}"

    def test_classify_dependency_external(self):
        """Test dependency classification for external dependencies."""
        test_cases = [
            'requests',
            'numpy',
            'flask',
            'django',
            'pytest',
            'external-lib',
            'third-party-package'
        ]
        
        for dep_name in test_cases:
            result = self.classifier.classify_dependency(dep_name)
            assert result == SourceType.EXTERNAL, f"Failed for dependency: {dep_name}"

    def test_classify_dependency_empty_name(self):
        """Test dependency classification with empty name."""
        result = self.classifier.classify_dependency('')
        assert result == SourceType.UNKNOWN

        result = self.classifier.classify_dependency(None)
        assert result == SourceType.UNKNOWN

    def test_classify_dependency_with_custom_patterns(self):
        """Test dependency classification with custom internal domain patterns."""
        internal_domains = {'*internal*', '*company*'}
        classifier = SourceClassifier(
            company_name='testco',
            internal_domains=internal_domains
        )
        
        # Should match internal patterns
        assert classifier.classify_dependency('internal-lib') == SourceType.INTERNAL
        assert classifier.classify_dependency('company-utils') == SourceType.INTERNAL
        assert classifier.classify_dependency('testco-core') == SourceType.INTERNAL
        
        # Should be external
        assert classifier.classify_dependency('external-lib') == SourceType.EXTERNAL


class TestApiCallClassification:
    """Test cases for API call classification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = SourceClassifier(company_name='starc')

    def test_classify_api_call_internal_company_name(self):
        """Test API call classification with company name in URL."""
        test_cases = [
            'https://api.starc.com/v1/users',
            'http://starc.internal.com/api/data',
            'https://services.starc.net/endpoint',
            'http://STARC.COM/api',  # Case insensitive
            'https://my-starc-service.com/api'
        ]
        
        for url in test_cases:
            result = self.classifier.classify_api_call(url)
            assert result == SourceType.INTERNAL, f"Failed for URL: {url}"

    def test_classify_api_call_localhost(self):
        """Test API call classification for localhost and internal IPs."""
        test_cases = [
            'http://localhost:8080/api',
            'https://127.0.0.1:5000/endpoint',
            'http://0.0.0.0:3000/data',
            'https://::1/api',
            'http://10.0.1.5/api',        # Private IP 10.x.x.x
            'https://172.16.0.10/data',   # Private IP 172.16-31.x.x
            'http://192.168.1.100/api',   # Private IP 192.168.x.x
        ]
        
        for url in test_cases:
            result = self.classifier.classify_api_call(url)
            assert result == SourceType.INTERNAL, f"Failed for URL: {url}"

    def test_classify_api_call_external(self):
        """Test API call classification for external APIs."""
        test_cases = [
            'https://api.github.com/repos',
            'http://jsonplaceholder.typicode.com/posts',
            'https://httpbin.org/get',
            'https://api.openweathermap.org/data',
            'http://example.com/api',
            'https://google.com/search',
        ]
        
        for url in test_cases:
            result = self.classifier.classify_api_call(url)
            assert result == SourceType.EXTERNAL, f"Failed for URL: {url}"

    def test_classify_api_call_empty_url(self):
        """Test API call classification with empty URL."""
        result = self.classifier.classify_api_call('')
        assert result == SourceType.UNKNOWN

        result = self.classifier.classify_api_call(None)
        assert result == SourceType.UNKNOWN

    def test_classify_api_call_invalid_url(self):
        """Test API call classification with invalid URL."""
        # Should fall back to string matching
        result = self.classifier.classify_api_call('invalid-url-with-starc')
        assert result == SourceType.INTERNAL

        result = self.classifier.classify_api_call('invalid-url-external')
        assert result == SourceType.UNKNOWN

    def test_classify_api_call_with_custom_patterns(self):
        """Test API call classification with custom internal domain patterns."""
        internal_domains = {'*.internal.com', '*.private.org'}
        classifier = SourceClassifier(
            company_name='testco',
            internal_domains=internal_domains
        )
        
        # Should match internal patterns
        assert classifier.classify_api_call('https://api.internal.com/data') == SourceType.INTERNAL
        assert classifier.classify_api_call('http://service.private.org/api') == SourceType.INTERNAL
        assert classifier.classify_api_call('https://testco.com/api') == SourceType.INTERNAL
        
        # Should be external
        assert classifier.classify_api_call('https://external.com/api') == SourceType.EXTERNAL


class TestPatternMatching:
    """Test cases for pattern matching functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = SourceClassifier(company_name='test')

    def test_matches_pattern_wildcards(self):
        """Test pattern matching with wildcards."""
        assert self.classifier._matches_pattern('testapp', '*test*')
        assert self.classifier._matches_pattern('mytest', '*test*')
        assert self.classifier._matches_pattern('test', '*test*')
        assert self.classifier._matches_pattern('testapp.com', '*test*')
        
        assert not self.classifier._matches_pattern('example', '*test*')
        assert not self.classifier._matches_pattern('app', '*test*')

    def test_matches_pattern_prefix_suffix(self):
        """Test pattern matching with prefix and suffix patterns."""
        assert self.classifier._matches_pattern('testapp', 'test*')
        assert self.classifier._matches_pattern('testing', 'test*')
        assert not self.classifier._matches_pattern('mytest', 'test*')
        
        assert self.classifier._matches_pattern('mytest', '*test')
        assert self.classifier._matches_pattern('unittest', '*test')
        assert not self.classifier._matches_pattern('testing', '*test')

    def test_matches_pattern_exact(self):
        """Test exact pattern matching."""
        assert self.classifier._matches_pattern('test', 'test')
        assert not self.classifier._matches_pattern('testing', 'test')
        assert not self.classifier._matches_pattern('test', 'testing')

    def test_matches_pattern_case_insensitive(self):
        """Test case insensitive pattern matching."""
        assert self.classifier._matches_pattern('TEST', '*test*')
        assert self.classifier._matches_pattern('MyTest', '*test*')
        assert self.classifier._matches_pattern('test', '*TEST*')

    def test_is_localhost_or_internal(self):
        """Test localhost and internal IP detection."""
        # Localhost variants
        assert self.classifier._is_localhost_or_internal('localhost')
        assert self.classifier._is_localhost_or_internal('127.0.0.1')
        assert self.classifier._is_localhost_or_internal('::1')
        assert self.classifier._is_localhost_or_internal('0.0.0.0')
        
        # Internal IP ranges
        assert self.classifier._is_localhost_or_internal('10.0.0.1')
        assert self.classifier._is_localhost_or_internal('10.255.255.255')
        assert self.classifier._is_localhost_or_internal('172.16.0.1')
        assert self.classifier._is_localhost_or_internal('172.31.255.255')
        assert self.classifier._is_localhost_or_internal('192.168.0.1')
        assert self.classifier._is_localhost_or_internal('192.168.255.255')
        
        # External IPs
        assert not self.classifier._is_localhost_or_internal('8.8.8.8')
        assert not self.classifier._is_localhost_or_internal('172.32.0.1')  # Outside range
        assert not self.classifier._is_localhost_or_internal('172.15.0.1')  # Outside range
        assert not self.classifier._is_localhost_or_internal('192.169.0.1')  # Outside range
        assert not self.classifier._is_localhost_or_internal('example.com')
        
        # Empty or None
        assert not self.classifier._is_localhost_or_internal('')
        assert not self.classifier._is_localhost_or_internal(None)


if __name__ == '__main__':
    pytest.main([__file__])