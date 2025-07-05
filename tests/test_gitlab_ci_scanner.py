"""Tests for GitLab CI scanner."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from typing import List

from dependency_scanner_tool.infrastructure_scanners.gitlab_ci import GitLabCIScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType
from dependency_scanner_tool.scanner import DependencyType


class TestGitLabCIScanner:
    """Test class for GitLab CI scanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = GitLabCIScanner()
    
    def test_get_supported_file_patterns(self):
        """Test that GitLab CI scanner returns correct file patterns."""
        patterns = self.scanner.get_supported_file_patterns()
        assert ".gitlab-ci.yml" in patterns
        assert ".gitlab-ci.yaml" in patterns
    
    def test_get_infrastructure_type(self):
        """Test that GitLab CI scanner returns correct infrastructure type."""
        assert self.scanner.get_infrastructure_type() == InfrastructureType.CICD
    
    def test_can_handle_gitlab_ci_files(self):
        """Test that scanner can handle GitLab CI files."""
        test_files = [
            Path(".gitlab-ci.yml"),
            Path(".gitlab-ci.yaml"),
        ]
        for test_file in test_files:
            assert self.scanner.can_handle_file(test_file)
    
    def test_cannot_handle_other_files(self):
        """Test that scanner rejects non-GitLab CI files."""
        test_files = [
            Path("Dockerfile"),
            Path("main.py"),
            Path("config.yaml"),
            Path("gitlab-ci.yml"),  # Missing the dot prefix
            Path("ci.yml")
        ]
        for test_file in test_files:
            assert not self.scanner.can_handle_file(test_file)
    
    def test_scan_basic_pipeline(self):
        """Test scanning a basic GitLab CI pipeline."""
        pipeline_content = """
stages:
  - build
  - test
  - deploy

build_job:
  stage: build
  script:
    - echo "Building..."
    - make build

test_job:
  stage: test
  script:
    - echo "Testing..."
    - make test

deploy_job:
  stage: deploy
  script:
    - echo "Deploying..."
    - make deploy
  only:
    - main
"""
        with patch('builtins.open', mock_open_read(pipeline_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".gitlab-ci.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.type == InfrastructureType.CICD
        assert component.name == "gitlab-ci-pipeline"
        assert component.service == "gitlab-ci"
        assert component.subtype == "pipeline"
        assert component.source_file == ".gitlab-ci.yml"
        assert component.configuration["stages"] == ["build", "test", "deploy"]
        assert "build_job" in component.configuration["jobs"]
        assert "test_job" in component.configuration["jobs"]
        assert "deploy_job" in component.configuration["jobs"]
    
    def test_scan_pipeline_with_variables(self):
        """Test scanning pipeline with variables."""
        pipeline_content = """
variables:
  DATABASE_URL: "postgres://localhost/test"
  NODE_ENV: "test"

stages:
  - test

test_job:
  stage: test
  variables:
    API_KEY: "test-key"
  script:
    - npm test
"""
        with patch('builtins.open', mock_open_read(pipeline_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".gitlab-ci.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        assert "variables" in component.configuration
        assert component.configuration["variables"]["DATABASE_URL"] == "postgres://localhost/test"
        assert component.configuration["variables"]["NODE_ENV"] == "test"
        assert component.configuration["jobs"]["test_job"]["variables"]["API_KEY"] == "test-key"
    
    def test_scan_pipeline_with_services(self):
        """Test scanning pipeline with services."""
        pipeline_content = """
services:
  - postgres:13
  - redis:6

stages:
  - test

test_with_services:
  stage: test
  services:
    - mysql:8.0
  script:
    - echo "Testing with services"
"""
        with patch('builtins.open', mock_open_read(pipeline_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".gitlab-ci.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        assert "services" in component.configuration
        assert "postgres:13" in component.configuration["services"]
        assert "redis:6" in component.configuration["services"]
        assert "mysql:8.0" in component.configuration["jobs"]["test_with_services"]["services"]
    
    def test_scan_pipeline_with_include(self):
        """Test scanning pipeline with includes."""
        pipeline_content = """
include:
  - local: '/templates/.gitlab-ci-template.yml'
  - project: 'my-group/my-project'
    file: '/templates/.gitlab-ci-template.yml'

stages:
  - build

build_job:
  stage: build
  script:
    - echo "Building..."
"""
        with patch('builtins.open', mock_open_read(pipeline_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".gitlab-ci.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        assert "include" in component.configuration
        assert len(component.configuration["include"]) == 2
    
    def test_scan_pipeline_with_image_and_cache(self):
        """Test scanning pipeline with Docker image and cache."""
        pipeline_content = """
image: node:16

cache:
  paths:
    - node_modules/

stages:
  - build

build_job:
  stage: build
  image: node:18
  cache:
    key: "$CI_COMMIT_REF_SLUG"
    paths:
      - dist/
  script:
    - npm install
    - npm run build
"""
        with patch('builtins.open', mock_open_read(pipeline_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".gitlab-ci.yml"))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.configuration["image"] == "node:16"
        assert "cache" in component.configuration
        assert component.configuration["jobs"]["build_job"]["image"] == "node:18"
    
    def test_scan_invalid_yaml(self):
        """Test scanning invalid YAML content."""
        invalid_content = "invalid: yaml: content: ["
        
        with patch('builtins.open', mock_open_read(invalid_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".gitlab-ci.yml"))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.CICD
        assert component.name == "gitlab-ci-pipeline"
        assert component.service == "gitlab-ci"
        assert component.subtype == "unknown"
    
    def test_scan_nonexistent_file(self):
        """Test scanning a non-existent file."""
        components = self.scanner.scan_file(Path("nonexistent/.gitlab-ci.yml"))
        assert components == []
    
    def test_scan_empty_file(self):
        """Test scanning an empty file."""
        with patch('builtins.open', mock_open_read("")), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path(".gitlab-ci.yml"))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.CICD
        assert component.name == "gitlab-ci-pipeline"
        assert component.service == "gitlab-ci"
        assert component.subtype == "unknown"
    
    def test_scan_with_file_read_error(self):
        """Test scanning when file cannot be read."""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            components = self.scanner.scan_file(Path(".gitlab-ci.yml"))
        
        assert components == []


def mock_open_read(content: str):
    """Mock open function that returns the given content."""
    from unittest.mock import mock_open
    return mock_open(read_data=content)