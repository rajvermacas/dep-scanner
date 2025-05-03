"""Tests for the pip dependency parser."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from dep_scanner.parsers.pip_dependencies import PipDependencyParser
from dep_scanner.scanner import DependencyType
from dep_scanner.exceptions import ParsingError


class TestPipDependencyParser:
    """Tests for the PipDependencyParser class."""

    def test_can_parse(self):
        """Test that the parser doesn't claim to parse any files directly."""
        parser = PipDependencyParser()
        
        # The parser doesn't parse files directly, so it should return False
        assert not parser.can_parse(Path("requirements.txt"))
        assert not parser.can_parse(Path("pyproject.toml"))
        assert not parser.can_parse(Path("setup.py"))
    
    @patch("subprocess.run")
    def test_parse_basic(self, mock_run):
        """Test parsing basic pip dependencies."""
        # Mock the subprocess.run call to return a known JSON output
        mock_process = MagicMock()
        mock_process.stdout = json.dumps([
            {"name": "pytest", "version": "7.0.0"},
            {"name": "requests", "version": "2.28.1"},
            {"name": "black", "version": "22.6.0"}
        ])
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        parser = PipDependencyParser()
        dependencies = parser.parse(Path("."))
        
        # Verify the dependencies were extracted correctly
        assert len(dependencies) == 3
        
        # Check the first dependency
        assert dependencies[0].name == "pytest"
        assert dependencies[0].version == "7.0.0"
        assert dependencies[0].source_file == "pip_database"
        assert dependencies[0].dependency_type == DependencyType.UNKNOWN
        
        # Check the second dependency
        assert dependencies[1].name == "requests"
        assert dependencies[1].version == "2.28.1"
        
        # Check the third dependency
        assert dependencies[2].name == "black"
        assert dependencies[2].version == "22.6.0"
        
        # Verify subprocess.run was called correctly
        mock_run.assert_called_once_with(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch("subprocess.run")
    def test_parse_empty(self, mock_run):
        """Test parsing when no dependencies are found."""
        # Mock the subprocess.run call to return an empty list
        mock_process = MagicMock()
        mock_process.stdout = json.dumps([])
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        parser = PipDependencyParser()
        dependencies = parser.parse(Path("."))
        
        # Verify no dependencies were extracted
        assert len(dependencies) == 0
        
        # Verify subprocess.run was called correctly
        mock_run.assert_called_once()
    
    @patch("subprocess.run")
    def test_parse_error(self, mock_run):
        """Test handling of errors during parsing."""
        # Mock the subprocess.run call to raise an exception
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["pip", "list", "--format=json"],
            stderr="Error: pip command failed"
        )
        
        parser = PipDependencyParser()
        
        # Verify that the parser raises a ParsingError
        with pytest.raises(Exception):
            parser.parse(Path("."))
    
    @patch("subprocess.run")
    def test_parse_venv(self, mock_run):
        """Test parsing dependencies from a virtual environment."""
        # Mock the subprocess.run call to return a known JSON output
        mock_process = MagicMock()
        mock_process.stdout = json.dumps([
            {"name": "django", "version": "4.0.0"},
            {"name": "flask", "version": "2.0.1"}
        ])
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Create a mock venv structure
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            
            parser = PipDependencyParser()
            venv_path = Path("/path/to/venv")
            dependencies = parser.parse_venv(venv_path)
            
            # Verify the dependencies were extracted correctly
            assert len(dependencies) == 2
            
            # Check the first dependency
            assert dependencies[0].name == "django"
            assert dependencies[0].version == "4.0.0"
            assert dependencies[0].source_file == f"venv:{venv_path}"
            
            # Check the second dependency
            assert dependencies[1].name == "flask"
            assert dependencies[1].version == "2.0.1"
            
            # Verify subprocess.run was called correctly with the venv pip
            mock_run.assert_called_once()
    
    @patch("pathlib.Path.exists")
    def test_parse_venv_error_no_pip(self, mock_exists):
        """Test handling of errors when pip is not found in the venv."""
        # Mock the Path.exists call to return False (no pip found)
        mock_exists.return_value = False
        
        parser = PipDependencyParser()
        venv_path = Path("/path/to/venv")
        
        # Verify that the parser raises a ParsingError when pip is not found
        with pytest.raises(ParsingError):
            parser.parse_venv(venv_path)
