"""Tests for GitHub Actions scanner."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from typing import List

from dependency_scanner_tool.infrastructure_scanners.github_actions import GitHubActionsScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType
from dependency_scanner_tool.scanner import DependencyType


class TestGitHubActionsScanner:
    """Test class for GitHub Actions scanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = GitHubActionsScanner()
    
    def test_get_supported_file_patterns(self):
        """Test that GitHub Actions scanner returns correct file patterns."""
        patterns = self.scanner.get_supported_file_patterns()
        assert ".github/workflows/*.yml" in patterns
        assert ".github/workflows/*.yaml" in patterns
    
    def test_get_infrastructure_type(self):
        """Test that GitHub Actions scanner returns correct infrastructure type."""
        assert self.scanner.get_infrastructure_type() == InfrastructureType.CICD
    
    def test_can_handle_workflow_files(self):
        """Test that scanner can handle GitHub Actions workflow files."""
        test_files = [
            Path(".github/workflows/ci.yml"),
            Path(".github/workflows/deploy.yaml"),
            Path(".github/workflows/test.yml")
        ]
        for test_file in test_files:
            assert self.scanner.can_handle_file(test_file)
    
    def test_cannot_handle_other_files(self):
        """Test that scanner rejects non-GitHub Actions files."""
        test_files = [
            Path("Dockerfile"),
            Path("main.py"),
            Path("config.yaml"),
            Path("workflow.yml"),  # Not in .github/workflows/
            Path(".github/issue_template.md")
        ]
        for test_file in test_files:
            assert not self.scanner.can_handle_file(test_file)
    
    def test_scan_basic_workflow(self):
        """Test scanning a basic GitHub Actions workflow."""
        workflow_content = """
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: pytest
"""
        with patch('builtins.open', mock_open_read(workflow_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".github/workflows/ci.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.type == InfrastructureType.CICD
        assert component.name == "CI"
        assert component.service == "github-actions"
        assert component.subtype == "workflow"
        assert component.source_file == ".github/workflows/ci.yml"
        assert component.configuration["on"]["push"]["branches"] == ["main"]
        assert component.configuration["on"]["pull_request"]["branches"] == ["main"]
        assert "test" in component.configuration["jobs"]
        assert component.configuration["jobs"]["test"]["runs-on"] == "ubuntu-latest"
    
    def test_scan_workflow_with_multiple_jobs(self):
        """Test scanning workflow with multiple jobs."""
        workflow_content = """
name: Build and Deploy
on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build
      run: npm run build
  
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Test
      run: npm test
  
  deploy:
    needs: [build, test]
    runs-on: ubuntu-latest
    steps:
    - name: Deploy
      run: echo "Deploying..."
"""
        with patch('builtins.open', mock_open_read(workflow_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".github/workflows/deploy.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.name == "Build and Deploy"
        assert len(component.configuration["jobs"]) == 3
        assert "build" in component.configuration["jobs"]
        assert "test" in component.configuration["jobs"]
        assert "deploy" in component.configuration["jobs"]
        assert component.configuration["jobs"]["deploy"]["needs"] == ["build", "test"]
    
    def test_scan_workflow_with_actions(self):
        """Test scanning workflow with various actions."""
        workflow_content = """
name: Complex Workflow
on: [push]

jobs:
  main:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-node@v3
      with:
        node-version: '16'
    - uses: docker/build-push-action@v3
      with:
        push: true
        tags: myapp:latest
"""
        with patch('builtins.open', mock_open_read(workflow_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".github/workflows/complex.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        # Check actions are extracted
        job_steps = component.configuration["jobs"]["main"]["steps"]
        assert len(job_steps) == 3
        assert any("actions/checkout@v3" in str(step) for step in job_steps)
        assert any("actions/setup-node@v3" in str(step) for step in job_steps)
        assert any("docker/build-push-action@v3" in str(step) for step in job_steps)
    
    def test_scan_workflow_with_environment_secrets(self):
        """Test scanning workflow with environment variables and secrets."""
        workflow_content = """
name: Deploy with Secrets
on: [push]

env:
  NODE_ENV: production
  APP_NAME: myapp

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
    - uses: actions/checkout@v3
    - name: Deploy
      env:
        API_KEY: ${{ secrets.API_KEY }}
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
      run: |
        echo "Deploying with API_KEY"
"""
        with patch('builtins.open', mock_open_read(workflow_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".github/workflows/deploy.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.configuration["env"]["NODE_ENV"] == "production"
        assert component.configuration["env"]["APP_NAME"] == "myapp"
        assert component.configuration["jobs"]["deploy"]["environment"] == "production"
    
    def test_scan_invalid_yaml(self):
        """Test scanning invalid YAML content."""
        invalid_content = "invalid: yaml: content: ["
        
        with patch('builtins.open', mock_open_read(invalid_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".github/workflows/invalid.yml"))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.CICD
        assert component.name == "github-actions-workflow"
        assert component.service == "github-actions"
        assert component.subtype == "unknown"
    
    def test_scan_nonexistent_file(self):
        """Test scanning a non-existent file."""
        components = self.scanner.scan_file(Path(".github/workflows/nonexistent.yml"))
        assert components == []
    
    def test_scan_empty_file(self):
        """Test scanning an empty file."""
        with patch('builtins.open', mock_open_read("")), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".github/workflows/empty.yml"))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.CICD
        assert component.name == "github-actions-workflow"
        assert component.service == "github-actions"
        assert component.subtype == "unknown"
    
    def test_scan_with_file_read_error(self):
        """Test scanning when file cannot be read."""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            components = self.scanner.scan_file(Path(".github/workflows/test.yml"))
        
        assert components == []


def mock_open_read(content: str):
    """Mock open function that returns the given content."""
    from unittest.mock import mock_open
    return mock_open(read_data=content)