"""Tests for DevPod infrastructure detection."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from dependency_scanner_tool.parsers.devfile_parser import DevfileParser
from dependency_scanner_tool.scanner import DependencyScanner, ScanResult


class TestDevPodDetection:
    """Test DevPod infrastructure detection functionality."""
    
    @pytest.fixture
    def test_data_dir(self):
        """Get the test data directory."""
        return Path(__file__).parent / "test_data" / "devfile_samples"
    
    def test_detect_devpod_usage_with_devfile_yaml(self, test_data_dir):
        """Test detection when devfile.yaml is present."""
        # Test with simple container devfile
        project_dir = test_data_dir / "simple_project_with_devfile"
        project_dir.mkdir(exist_ok=True)
        
        # Copy a devfile to the test project
        devfile_content = """
schemaVersion: 2.2.0
metadata:
  name: test-project
components:
  - name: dev-container
    container:
      image: python:3.9
"""
        (project_dir / "devfile.yaml").write_text(devfile_content)
        
        try:
            result = DevfileParser.detect_devpod_usage(project_dir)
            assert result is True
        finally:
            # Cleanup
            if (project_dir / "devfile.yaml").exists():
                (project_dir / "devfile.yaml").unlink()
            if project_dir.exists():
                project_dir.rmdir()
    
    def test_detect_devpod_usage_with_devcontainer_devfile(self, test_data_dir):
        """Test detection when devfile is in .devcontainer directory."""
        project_dir = test_data_dir / "project_with_devcontainer"
        devcontainer_dir = project_dir / ".devcontainer"
        
        project_dir.mkdir(exist_ok=True)
        devcontainer_dir.mkdir(exist_ok=True)
        
        devfile_content = """
schemaVersion: 2.2.0
metadata:
  name: devcontainer-project
components:
  - name: main
    container:
      image: mcr.microsoft.com/vscode/devcontainers/base:ubuntu
"""
        (devcontainer_dir / "devfile.yaml").write_text(devfile_content)
        
        try:
            result = DevfileParser.detect_devpod_usage(project_dir)
            assert result is True
        finally:
            # Cleanup
            if (devcontainer_dir / "devfile.yaml").exists():
                (devcontainer_dir / "devfile.yaml").unlink()
            if devcontainer_dir.exists():
                devcontainer_dir.rmdir()
            if project_dir.exists():
                project_dir.rmdir()
    
    def test_detect_devpod_usage_no_devfiles(self):
        """Test detection when no devfiles are present."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a project with no devfiles in a clean temporary directory
            project_dir = Path(tmp_dir) / "no_devfiles_project"
            project_dir.mkdir()
            
            # Add some regular files
            (project_dir / "requirements.txt").write_text("flask==2.0.0\n")
            (project_dir / "app.py").write_text("print('Hello World')\n")
            (project_dir / "config.yaml").write_text("database: sqlite\n")
            
            result = DevfileParser.detect_devpod_usage(project_dir)
            assert result is False
    
    def test_detect_devpod_usage_with_yaml_but_not_devfile(self):
        """Test detection with YAML files that are not devfiles."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "yaml_but_not_devfile"
            project_dir.mkdir()
            
            # Add YAML files that are not devfiles
            (project_dir / "docker-compose.yml").write_text("""
version: '3'
services:
  web:
    image: nginx
""")
            
            (project_dir / "config.yaml").write_text("""
database:
  host: localhost
  port: 5432
""")
            
            result = DevfileParser.detect_devpod_usage(project_dir)
            assert result is False
    
    def test_detect_devpod_usage_invalid_directory(self):
        """Test detection with invalid directory path."""
        invalid_path = Path("/nonexistent/directory")
        result = DevfileParser.detect_devpod_usage(invalid_path)
        assert result is False
    
    def test_detect_devpod_usage_file_not_directory(self, tmp_path):
        """Test detection when path is a file, not a directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is a file, not a directory")
        
        result = DevfileParser.detect_devpod_usage(test_file)
        assert result is False
    
    def test_detect_devpod_usage_with_custom_name_devfile(self, tmp_path):
        """Test detection with custom-named devfile (content-based detection)."""
        project_dir = tmp_path / "custom_devfile_project"
        project_dir.mkdir()
        
        # Create a devfile with a custom name
        devfile_content = """
schemaVersion: 2.2.0
metadata:
  name: custom-devfile
  displayName: Custom Development Environment
components:
  - name: nodejs-app
    container:
      image: node:16-alpine
      mountSources: true
commands:
  - id: install
    exec:
      component: nodejs-app
      commandLine: npm install
"""
        (project_dir / "my-custom-devfile.yaml").write_text(devfile_content)
        
        result = DevfileParser.detect_devpod_usage(project_dir)
        assert result is True
    
    def test_scanner_integration_with_devpod_detection(self, tmp_path):
        """Test that the main scanner integrates DevPod detection."""
        # Create a test project with a devfile
        project_dir = tmp_path / "scanner_integration_test"
        project_dir.mkdir()
        
        # Add a requirements.txt for regular dependencies
        (project_dir / "requirements.txt").write_text("flask==2.0.0\ngunicorn==20.1.0\n")
        
        # Add a devfile
        devfile_content = """
schemaVersion: 2.2.0
metadata:
  name: flask-app
components:
  - name: flask-dev
    container:
      image: python:3.9-slim
      mountSources: true
"""
        (project_dir / "devfile.yaml").write_text(devfile_content)
        
        # Create scanner and scan the project
        scanner = DependencyScanner()
        result = scanner.scan_project(str(project_dir))
        
        # Verify infrastructure usage is detected
        assert isinstance(result, ScanResult)
        assert result.infrastructure_usage is not None
        assert "devpods" in result.infrastructure_usage
        assert result.infrastructure_usage["devpods"] is True
        
        # Verify regular dependencies are still detected
        assert len(result.dependencies) > 0
        dep_names = [dep.name for dep in result.dependencies]
        assert "flask" in dep_names
        assert "gunicorn" in dep_names
    
    def test_scanner_integration_no_devpod(self, tmp_path):
        """Test that the scanner reports no DevPod usage when none present."""
        # Create a test project without devfiles
        project_dir = tmp_path / "no_devpod_project"
        project_dir.mkdir()
        
        # Add only regular files
        (project_dir / "requirements.txt").write_text("requests==2.25.0\n")
        (project_dir / "app.py").write_text("import requests\nprint('Hello')\n")
        
        # Create scanner and scan the project
        scanner = DependencyScanner()
        result = scanner.scan_project(str(project_dir))
        
        # Verify infrastructure usage shows no DevPods
        assert isinstance(result, ScanResult)
        assert result.infrastructure_usage is not None
        assert "devpods" in result.infrastructure_usage
        assert result.infrastructure_usage["devpods"] is False
    
    @patch('dependency_scanner_tool.parsers.devfile_parser.DevfileParser.detect_devpod_usage')
    def test_scanner_handles_devpod_detection_error(self, mock_detect, tmp_path):
        """Test that scanner handles DevPod detection errors gracefully."""
        # Mock the detection to raise an exception
        mock_detect.side_effect = Exception("Detection failed")
        
        project_dir = tmp_path / "error_test_project"
        project_dir.mkdir()
        (project_dir / "requirements.txt").write_text("flask==2.0.0\n")
        
        # Create scanner and scan the project
        scanner = DependencyScanner()
        result = scanner.scan_project(str(project_dir))
        
        # Verify the scanner handles the error gracefully
        assert isinstance(result, ScanResult)
        assert result.infrastructure_usage is not None
        assert result.infrastructure_usage["devpods"] is False
        assert any("Error detecting DevPod usage" in error for error in result.errors)
    
    def test_devpod_detection_with_existing_test_samples(self, test_data_dir):
        """Test DevPod detection using existing test sample devfiles."""
        # Test with the existing simple container devfile
        simple_devfile = test_data_dir / "simple_container_devfile.yaml"
        if simple_devfile.exists():
            # Create a temporary project directory and copy the devfile
            temp_project = test_data_dir / "temp_detection_test"
            temp_project.mkdir(exist_ok=True)
            
            try:
                # Copy the devfile with standard name
                import shutil
                shutil.copy2(simple_devfile, temp_project / "devfile.yaml")
                
                result = DevfileParser.detect_devpod_usage(temp_project)
                assert result is True
                
            finally:
                # Cleanup
                if (temp_project / "devfile.yaml").exists():
                    (temp_project / "devfile.yaml").unlink()
                if temp_project.exists():
                    temp_project.rmdir()
    
    def test_devpod_detection_performance(self, tmp_path):
        """Test DevPod detection performance with many YAML files."""
        project_dir = tmp_path / "performance_test"
        project_dir.mkdir()
        
        # Create many non-devfile YAML files
        for i in range(50):
            yaml_file = project_dir / f"config_{i}.yaml"
            yaml_file.write_text(f"""
database:
  host: db{i}.example.com
  port: 5432
services:
  - name: service{i}
    port: {8000 + i}
""")
        
        # Add one actual devfile
        devfile = project_dir / "devfile.yaml"
        devfile.write_text("""
schemaVersion: 2.2.0
metadata:
  name: performance-test
components:
  - name: app
    container:
      image: alpine:latest
""")
        
        # Should still detect DevPod usage efficiently
        result = DevfileParser.detect_devpod_usage(project_dir)
        assert result is True