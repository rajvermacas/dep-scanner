"""Tests for the Generic API call analyzer."""

import tempfile
from pathlib import Path
from unittest import TestCase

from dependency_scanner_tool.api_analyzers.generic_api_analyzer import GenericApiCallAnalyzer
from dependency_scanner_tool.api_analyzers.base import ApiAuthType


class TestGenericApiCallAnalyzer(TestCase):
    """Test cases for the Generic API call analyzer."""

    def setUp(self):
        """Set up the test environment."""
        self.analyzer = GenericApiCallAnalyzer()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()

    def test_can_analyze_javascript(self):
        """Test that the analyzer can identify JavaScript files."""
        js_file = self.temp_path / "test.js"
        js_file.touch()
        self.assertTrue(self.analyzer.can_analyze(js_file))

    def test_can_analyze_go(self):
        """Test that the analyzer can identify Go files."""
        go_file = self.temp_path / "test.go"
        go_file.touch()
        self.assertTrue(self.analyzer.can_analyze(go_file))

    def test_can_analyze_ruby(self):
        """Test that the analyzer can identify Ruby files."""
        rb_file = self.temp_path / "test.rb"
        rb_file.touch()
        self.assertTrue(self.analyzer.can_analyze(rb_file))

    def test_analyze_javascript(self):
        """Test detecting URLs in JavaScript."""
        content = '''
        // API configuration
        const API_BASE_URL = "https://api.example.com/v1";
        const WEBHOOK_URL = 'https://webhook.site/unique-id';

        // Fetch calls
        fetch("https://api.github.com/users")
          .then(response => response.json());

        // Template literals
        const url = `https://api.openweathermap.org/data/2.5/weather`;

        // Axios
        axios.get("https://jsonplaceholder.typicode.com/posts");
        '''

        js_file = self.temp_path / "api_client.js"
        with open(js_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(js_file)

        # Should find all URLs
        self.assertGreaterEqual(len(api_calls), 5)

        # Check that URLs are detected
        urls = [call.url for call in api_calls]
        self.assertIn('https://api.example.com/v1', urls)
        self.assertIn('https://webhook.site/unique-id', urls)
        self.assertIn('https://api.github.com/users', urls)
        self.assertIn('https://api.openweathermap.org/data/2.5/weather', urls)
        self.assertIn('https://jsonplaceholder.typicode.com/posts', urls)

    def test_analyze_go(self):
        """Test detecting URLs in Go."""
        content = '''
        package main

        import (
            "net/http"
        )

        const (
            apiBaseURL = "https://api.example.com/v1"
            authURL    = "https://auth.example.com/token"
        )

        func main() {
            // GET request
            resp, err := http.Get("https://api.github.com/repos")

            // POST request
            http.Post("https://api.example.com/users", "application/json", nil)
        }
        '''

        go_file = self.temp_path / "api_client.go"
        with open(go_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(go_file)

        # Should find all URLs
        self.assertGreaterEqual(len(api_calls), 4)

        # Check that URLs are detected
        urls = [call.url for call in api_calls]
        self.assertIn('https://api.example.com/v1', urls)
        self.assertIn('https://auth.example.com/token', urls)
        self.assertIn('https://api.github.com/repos', urls)
        self.assertIn('https://api.example.com/users', urls)

        # Check that URL was detected (method detection is language-specific)
        get_calls = [call for call in api_calls if call.url == 'https://api.github.com/repos']
        self.assertEqual(len(get_calls), 1)

    def test_analyze_ruby(self):
        """Test detecting URLs in Ruby."""
        content = '''
        require 'net/http'
        require 'uri'

        # Configuration
        API_BASE_URL = "https://api.example.com/v1"
        WEBHOOK_URL = 'https://webhook.site/unique-id'

        # HTTP requests
        uri = URI("https://api.github.com/users")
        response = Net::HTTP.get(uri)

        # POST request
        Net::HTTP.post(URI("https://api.example.com/users"), data)
        '''

        rb_file = self.temp_path / "api_client.rb"
        with open(rb_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(rb_file)

        # Should find all URLs
        self.assertGreaterEqual(len(api_calls), 4)

        # Check that URLs are detected
        urls = [call.url for call in api_calls]
        self.assertIn('https://api.example.com/v1', urls)
        self.assertIn('https://webhook.site/unique-id', urls)
        self.assertIn('https://api.github.com/users', urls)
        self.assertIn('https://api.example.com/users', urls)

    def test_analyze_json_config(self):
        """Test detecting URLs in JSON configuration."""
        content = '''
        {
          "api": {
            "baseUrl": "https://api.example.com/v1",
            "endpoints": {
              "users": "https://api.example.com/users",
              "auth": "https://auth.example.com/token"
            }
          },
          "webhooks": [
            "https://webhook.site/unique-id-1",
            "https://webhook.site/unique-id-2"
          ]
        }
        '''

        json_file = self.temp_path / "config.json"
        with open(json_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(json_file)

        # Should find all URLs
        self.assertEqual(len(api_calls), 5)

        # Check that URLs are detected
        urls = [call.url for call in api_calls]
        self.assertIn('https://api.example.com/v1', urls)
        self.assertIn('https://api.example.com/users', urls)
        self.assertIn('https://auth.example.com/token', urls)
        self.assertIn('https://webhook.site/unique-id-1', urls)
        self.assertIn('https://webhook.site/unique-id-2', urls)

    def test_analyze_yaml_config(self):
        """Test detecting URLs in YAML configuration."""
        content = '''
        api:
          baseUrl: "https://api.example.com/v1"
          endpoints:
            users: "https://api.example.com/users"
            auth: "https://auth.example.com/token"

        webhooks:
          - "https://webhook.site/unique-id-1"
          - "https://webhook.site/unique-id-2"
        '''

        yaml_file = self.temp_path / "config.yaml"
        with open(yaml_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(yaml_file)

        # Should find all URLs
        self.assertEqual(len(api_calls), 5)

        # Check that URLs are detected
        urls = [call.url for call in api_calls]
        self.assertIn('https://api.example.com/v1', urls)

    def test_analyze_markdown_docs(self):
        """Test detecting URLs in Markdown documentation."""
        content = '''
        # API Documentation

        ## Endpoints

        - Users API: https://api.example.com/users
        - Auth API: https://auth.example.com/token
        - GitHub API: https://api.github.com/repos

        ## Configuration

        Set your base URL to `https://api.example.com/v1`

        [API Reference](https://docs.example.com/api)
        '''

        md_file = self.temp_path / "README.md"
        with open(md_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(md_file)

        # Should find all URLs
        self.assertGreaterEqual(len(api_calls), 5)

        # Check that URLs are detected
        urls = [call.url for call in api_calls]
        self.assertIn('https://api.example.com/users', urls)
        self.assertIn('https://auth.example.com/token', urls)
        self.assertIn('https://api.github.com/repos', urls)

    def test_exclude_example_domains(self):
        """Test that example domains are excluded."""
        content = '''
        // These should be excluded
        const example1 = "https://example.com/api";
        const example2 = "https://www.example.org/data";
        const localhost = "https://localhost:8080/api";
        const loopback = "https://127.0.0.1:8080/api";

        // These should be included
        const real1 = "https://api.github.com/users";
        const real2 = "https://api.example.io/data";
        const api = "https://api.example.org/data";  # Valid API URL pattern
        '''

        js_file = self.temp_path / "test_exclusions.js"
        with open(js_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(js_file)

        # Should only find real URLs
        urls = [call.url for call in api_calls]
        self.assertNotIn('https://example.com/api', urls)
        self.assertNotIn('https://www.example.org/data', urls)
        self.assertNotIn('https://localhost:8080/api', urls)
        self.assertNotIn('https://127.0.0.1:8080/api', urls)
        self.assertIn('https://api.github.com/users', urls)
        self.assertIn('https://api.example.io/data', urls)
        self.assertIn('https://api.example.org/data', urls)  # Valid subdomain

    def test_detect_http_methods(self):
        """Test HTTP method detection from context."""
        content = '''
        // GET request
        fetch("https://api.example.com/users", { method: 'GET' });

        // POST request
        axios.post("https://api.example.com/users", data);

        // PUT request
        http.put("https://api.example.com/users/1");

        // DELETE request
        client.delete("https://api.example.com/users/1");
        '''

        js_file = self.temp_path / "methods.js"
        with open(js_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(js_file)

        # Check method detection
        get_calls = [call for call in api_calls if 'GET' in call.http_method]
        self.assertGreaterEqual(len(get_calls), 1)

        post_calls = [call for call in api_calls if 'POST' in call.http_method]
        self.assertGreaterEqual(len(post_calls), 1)

        put_calls = [call for call in api_calls if 'PUT' in call.http_method]
        self.assertGreaterEqual(len(put_calls), 1)

        delete_calls = [call for call in api_calls if 'DELETE' in call.http_method]
        self.assertGreaterEqual(len(delete_calls), 1)

    def test_detect_authentication(self):
        """Test authentication type detection."""
        content = '''
        // Bearer token
        fetch("https://api.example.com/users", {
          headers: {
            'Authorization': 'Bearer token123'
          }
        });

        // API Key
        axios.get("https://api.example.com/data", {
          headers: { 'X-API-Key': 'key123' }
        });

        // Basic auth
        http.get("https://api.example.com/secure", {
          auth: { type: 'basic' }
        });
        '''

        js_file = self.temp_path / "auth.js"
        with open(js_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(js_file)

        # Check auth detection
        token_calls = [call for call in api_calls if call.auth_type == ApiAuthType.TOKEN]
        self.assertGreaterEqual(len(token_calls), 1)

        api_key_calls = [call for call in api_calls if call.auth_type == ApiAuthType.API_KEY]
        self.assertGreaterEqual(len(api_key_calls), 1)

        basic_calls = [call for call in api_calls if call.auth_type == ApiAuthType.BASIC]
        self.assertGreaterEqual(len(basic_calls), 1)

    def test_skip_binary_files(self):
        """Test that binary files are skipped."""
        # Create a binary file
        binary_file = self.temp_path / "test.pyc"
        binary_file.write_bytes(b'\x00\x01\x02\x03')

        api_calls = self.analyzer.analyze(binary_file)

        # Should return empty list for binary files
        self.assertEqual(len(api_calls), 0)

    def test_analyze_typescript(self):
        """Test detecting URLs in TypeScript."""
        content = '''
        interface ApiConfig {
          baseUrl: string;
          authUrl: string;
        }

        const config: ApiConfig = {
          baseUrl: "https://api.example.com/v1",
          authUrl: "https://auth.example.com/token"
        };

        // Async function
        async function fetchUsers(): Promise<User[]> {
          const response = await fetch("https://api.example.com/users");
          return response.json();
        }
        '''

        ts_file = self.temp_path / "api_client.ts"
        with open(ts_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(ts_file)

        # Should find all URLs
        self.assertEqual(len(api_calls), 3)

        urls = [call.url for call in api_calls]
        self.assertIn('https://api.example.com/v1', urls)
        self.assertIn('https://auth.example.com/token', urls)
        self.assertIn('https://api.example.com/users', urls)
