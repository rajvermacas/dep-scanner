"""Tests for the Python API call analyzer."""

import tempfile
from pathlib import Path
from unittest import TestCase

from dependency_scanner_tool.api_analyzers.python_api_analyzer import PythonApiCallAnalyzer
from dependency_scanner_tool.api_analyzers.base import ApiAuthType


class TestPythonApiCallAnalyzer(TestCase):
    """Test cases for the Python API call analyzer."""

    def setUp(self):
        """Set up the test environment."""
        self.analyzer = PythonApiCallAnalyzer()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()

    def test_can_analyze(self):
        """Test that the analyzer can identify Python files."""
        # Create a Python file
        py_file = self.temp_path / "test.py"
        py_file.touch()
        self.assertTrue(self.analyzer.can_analyze(py_file))

        # Create a non-Python file
        txt_file = self.temp_path / "test.txt"
        txt_file.touch()
        self.assertFalse(self.analyzer.can_analyze(txt_file))

    def test_analyze_requests(self):
        """Test detecting requests library calls."""
        content = '''
        import requests

        # Simple GET request
        response = requests.get('https://api.example.com/users')
        
        # POST request with JSON data
        data = {'name': 'John', 'email': 'john@example.com'}
        response = requests.post('https://api.example.com/users', json=data)
        '''

        py_file = self.temp_path / "requests_example.py"
        with open(py_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(py_file)
        
        # Should find two API calls
        self.assertEqual(len(api_calls), 2)
        
        # Check first API call (GET)
        self.assertEqual(api_calls[0].url, 'https://api.example.com/users')
        self.assertEqual(api_calls[0].http_method, 'GET')
        
        # Check second API call (POST)
        self.assertEqual(api_calls[1].url, 'https://api.example.com/users')
        self.assertEqual(api_calls[1].http_method, 'POST')

    def test_analyze_requests_with_auth(self):
        """Test detecting requests with authentication."""
        content = '''
        import requests
        
        # Basic auth
        response = requests.get('https://api.example.com/users', auth=('user', 'pass'))
        
        # Token auth
        headers = {'Authorization': 'Bearer my-token'}
        response = requests.get('https://api.example.com/profile', headers=headers)
        
        # API key auth
        headers = {'X-API-Key': 'my-api-key'}
        response = requests.get('https://api.example.com/data', headers=headers)
        '''

        py_file = self.temp_path / "auth_requests.py"
        with open(py_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(py_file)
        
        # Should find three API calls
        self.assertEqual(len(api_calls), 3)
        
        # Check first API call (Basic auth)
        self.assertEqual(api_calls[0].url, 'https://api.example.com/users')
        self.assertEqual(api_calls[0].auth_type, ApiAuthType.BASIC)
        
        # Check second API call (Token auth)
        self.assertEqual(api_calls[1].url, 'https://api.example.com/profile')
        self.assertEqual(api_calls[1].auth_type, ApiAuthType.TOKEN)

    def test_analyze_urllib(self):
        """Test detecting urllib.request calls."""
        content = '''
        import urllib.request
        import json
        
        # Simple GET request
        with urllib.request.urlopen('https://api.example.com/data') as response:
            data = json.loads(response.read())
        
        # POST request
        data = {'name': 'John', 'email': 'john@example.com'}
        data_bytes = json.dumps(data).encode('utf-8')
        req = urllib.request.Request('https://api.example.com/users', 
                                    data=data_bytes, 
                                    method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
        '''

        py_file = self.temp_path / "urllib_example.py"
        with open(py_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(py_file)
        
        # Should find at least one API call (the simple GET)
        self.assertGreaterEqual(len(api_calls), 1)
        
        # Check the API call
        self.assertEqual(api_calls[0].url, 'https://api.example.com/data')

    def test_analyze_httpx(self):
        """Test detecting httpx calls."""
        content = '''
        import httpx
        
        # Synchronous request
        response = httpx.get('https://api.example.com/data')
        
        # With client
        with httpx.Client() as client:
            response = client.post('https://api.example.com/users', 
                                  json={'name': 'John'})
        
        # Async client
        async def fetch():
            async with httpx.AsyncClient() as client:
                response = await client.get('https://api.example.com/async')
                return response.json()
        '''

        py_file = self.temp_path / "httpx_example.py"
        with open(py_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(py_file)
        
        # Should find at least one API call
        self.assertGreaterEqual(len(api_calls), 1)
        
        # Check the API call
        self.assertEqual(api_calls[0].url, 'https://api.example.com/data')

    def test_analyze_with_syntax_error(self):
        """Test analyzing a file with syntax errors."""
        content = '''
        import requests
        
        # This line has a syntax error
        response = requests.get('https://api.example.com/users'
        
        # This should still be detected using regex fallback
        response = requests.post('https://api.example.com/login', json={'username': 'admin'})
        '''

        py_file = self.temp_path / "syntax_error.py"
        with open(py_file, "w") as f:
            f.write(content)

        api_calls = self.analyzer.analyze(py_file)
        
        # Should find two API calls using regex fallback
        self.assertEqual(len(api_calls), 2)
        
        # Check the API calls
        urls = [call.url for call in api_calls]
        self.assertIn('https://api.example.com/users', urls)
        self.assertIn('https://api.example.com/login', urls) 