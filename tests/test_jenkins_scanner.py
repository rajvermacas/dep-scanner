"""Tests for Jenkins scanner."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from typing import List

from dependency_scanner_tool.infrastructure_scanners.jenkins import JenkinsScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType
from dependency_scanner_tool.scanner import DependencyType


class TestJenkinsScanner:
    """Test class for Jenkins scanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = JenkinsScanner()
    
    def test_get_supported_file_patterns(self):
        """Test that Jenkins scanner returns correct file patterns."""
        patterns = self.scanner.get_supported_file_patterns()
        assert "Jenkinsfile" in patterns
        assert "Jenkinsfile.*" in patterns
        assert "*.jenkins" in patterns
    
    def test_get_infrastructure_type(self):
        """Test that Jenkins scanner returns correct infrastructure type."""
        assert self.scanner.get_infrastructure_type() == InfrastructureType.CICD
    
    def test_can_handle_jenkinsfile(self):
        """Test that scanner can handle Jenkinsfile."""
        test_file = Path("Jenkinsfile")
        assert self.scanner.can_handle_file(test_file)
    
    def test_can_handle_jenkinsfile_with_extension(self):
        """Test that scanner can handle Jenkinsfile.groovy."""
        test_file = Path("Jenkinsfile.groovy")
        assert self.scanner.can_handle_file(test_file)
    
    def test_can_handle_jenkins_extension(self):
        """Test that scanner can handle *.jenkins files."""
        test_file = Path("pipeline.jenkins")
        assert self.scanner.can_handle_file(test_file)
    
    def test_cannot_handle_other_files(self):
        """Test that scanner rejects non-Jenkins files."""
        test_files = [
            Path("Dockerfile"),
            Path("main.py"),
            Path("config.yaml"),
            Path("jenkins.txt")
        ]
        for test_file in test_files:
            assert not self.scanner.can_handle_file(test_file)
    
    def test_scan_basic_declarative_pipeline(self):
        """Test scanning a basic declarative Jenkinsfile."""
        jenkinsfile_content = """
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'make build'
            }
        }
        stage('Test') {
            steps {
                sh 'make test'
            }
        }
        stage('Deploy') {
            steps {
                sh 'make deploy'
            }
        }
    }
}
"""
        with patch('builtins.open', mock_open_read(jenkinsfile_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path("Jenkinsfile"))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.type == InfrastructureType.CICD
        assert component.name == "jenkins-pipeline"
        assert component.service == "jenkins"
        assert component.subtype == "declarative"
        assert component.source_file == "Jenkinsfile"
        assert component.configuration["agent"] == "any"
        assert len(component.configuration["stages"]) == 3
        assert "Build" in component.configuration["stages"]
        assert "Test" in component.configuration["stages"]
        assert "Deploy" in component.configuration["stages"]
    
    def test_scan_scripted_pipeline(self):
        """Test scanning a scripted Jenkinsfile."""
        jenkinsfile_content = """
node {
    stage('Checkout') {
        checkout scm
    }
    stage('Build') {
        sh 'mvn clean compile'
    }
    stage('Test') {
        sh 'mvn test'
    }
}
"""
        with patch('builtins.open', mock_open_read(jenkinsfile_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path("Jenkinsfile"))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.type == InfrastructureType.CICD
        assert component.name == "jenkins-pipeline"
        assert component.service == "jenkins"
        assert component.subtype == "scripted"
        assert component.source_file == "Jenkinsfile"
        assert len(component.configuration["stages"]) == 3
    
    def test_scan_pipeline_with_tools(self):
        """Test scanning pipeline with tools configuration."""
        jenkinsfile_content = """
pipeline {
    agent any
    tools {
        maven 'Maven-3.8.1'
        jdk 'JDK-11'
    }
    stages {
        stage('Build') {
            steps {
                sh 'mvn clean compile'
            }
        }
    }
}
"""
        with patch('builtins.open', mock_open_read(jenkinsfile_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path("Jenkinsfile"))
        
        assert len(components) == 1
        component = components[0]
        
        assert "tools" in component.configuration
        assert component.configuration["tools"]["maven"] == "Maven-3.8.1"
        assert component.configuration["tools"]["jdk"] == "JDK-11"
    
    def test_scan_pipeline_with_environment(self):
        """Test scanning pipeline with environment variables."""
        jenkinsfile_content = """
pipeline {
    agent any
    environment {
        AWS_REGION = 'us-east-1'
        DOCKER_IMAGE = 'myapp:latest'
    }
    stages {
        stage('Deploy') {
            steps {
                sh 'aws deploy'
            }
        }
    }
}
"""
        with patch('builtins.open', mock_open_read(jenkinsfile_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path("Jenkinsfile"))
        
        assert len(components) == 1
        component = components[0]
        
        assert "environment" in component.configuration
        assert component.configuration["environment"]["AWS_REGION"] == "us-east-1"
        assert component.configuration["environment"]["DOCKER_IMAGE"] == "myapp:latest"
    
    def test_scan_nonexistent_file(self):
        """Test scanning a non-existent file."""
        components = self.scanner.scan_file(Path("nonexistent.jenkins"))
        assert components == []
    
    def test_scan_empty_file(self):
        """Test scanning an empty file."""
        with patch('builtins.open', mock_open_read("")), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path("Jenkinsfile"))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.CICD
        assert component.name == "jenkins-pipeline"
        assert component.service == "jenkins"
        assert component.subtype == "unknown"
    
    def test_scan_invalid_jenkinsfile(self):
        """Test scanning invalid Jenkinsfile content."""
        invalid_content = "This is not a valid Jenkinsfile"
        
        with patch('builtins.open', mock_open_read(invalid_content)), \
             patch('pathlib.Path.exists', return_value=True):
            components = self.scanner.scan_file(Path("Jenkinsfile"))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.CICD
        assert component.name == "jenkins-pipeline"
        assert component.service == "jenkins"
        assert component.subtype == "unknown"
    
    def test_scan_with_file_read_error(self):
        """Test scanning when file cannot be read."""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            components = self.scanner.scan_file(Path("Jenkinsfile"))
        
        assert components == []


def mock_open_read(content: str):
    """Mock open function that returns the given content."""
    from unittest.mock import mock_open
    return mock_open(read_data=content)