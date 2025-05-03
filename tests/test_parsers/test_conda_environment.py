"""Tests for the conda environment file parser."""

import os
import tempfile
from pathlib import Path

import pytest

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.conda_environment import CondaEnvironmentParser
from dep_scanner.scanner import DependencyType


class TestCondaEnvironmentParser:
    """Tests for the CondaEnvironmentParser class."""
    
    def test_can_parse(self):
        """Test that the parser can parse conda environment files."""
        parser = CondaEnvironmentParser()
        
        # Should parse environment.yml files
        assert parser.can_parse(Path("environment.yml"))
        assert parser.can_parse(Path("path/to/environment.yml"))
        
        # Should parse environment.yaml files
        assert parser.can_parse(Path("environment.yaml"))
        assert parser.can_parse(Path("path/to/environment.yaml"))
        
        # Should not parse other files
        assert not parser.can_parse(Path("requirements.txt"))
        assert not parser.can_parse(Path("pyproject.toml"))
        assert not parser.can_parse(Path("setup.py"))
    
    def test_parse_basic(self):
        """Test parsing a basic conda environment file."""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"""
name: myenv
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - numpy=1.21.0
  - pandas>=1.3.0
  - matplotlib
""")
            file_path = Path(f.name)
        
        try:
            parser = CondaEnvironmentParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 4
            
            # Check that the dependencies have the correct attributes
            python_dep = next(d for d in dependencies if d.name == "python")
            assert python_dep.version == "3.9"
            assert python_dep.source_file == str(file_path)
            assert python_dep.dependency_type == DependencyType.UNKNOWN
            
            numpy_dep = next(d for d in dependencies if d.name == "numpy")
            assert numpy_dep.version == "1.21.0"
            
            pandas_dep = next(d for d in dependencies if d.name == "pandas")
            assert pandas_dep.version == ">=1.3.0"
            
            matplotlib_dep = next(d for d in dependencies if d.name == "matplotlib")
            assert matplotlib_dep.version is None
        finally:
            os.unlink(file_path)
    
    def test_parse_with_pip_dependencies(self):
        """Test parsing a conda environment file with pip dependencies."""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"""
name: myenv
channels:
  - conda-forge
dependencies:
  - python=3.9
  - numpy=1.21.0
  - pip
  - pip:
    - requests>=2.25.0
    - flask
""")
            file_path = Path(f.name)
        
        try:
            parser = CondaEnvironmentParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies (3 conda + 2 pip)
            assert len(dependencies) == 5
            
            # Check conda dependencies
            conda_deps = [d for d in dependencies if d.name in ["python", "numpy", "pip"]]
            assert len(conda_deps) == 3
            
            # Check pip dependencies
            pip_deps = [d for d in dependencies if d.name in ["requests", "flask"]]
            assert len(pip_deps) == 2
            
            requests_dep = next(d for d in dependencies if d.name == "requests")
            assert requests_dep.version == ">=2.25.0"
            assert requests_dep.source_file == str(file_path)
            
            flask_dep = next(d for d in dependencies if d.name == "flask")
            assert flask_dep.version is None
        finally:
            os.unlink(file_path)
    
    def test_parse_empty_file(self):
        """Test parsing an empty conda environment file."""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"")
            file_path = Path(f.name)
        
        try:
            parser = CondaEnvironmentParser()
            dependencies = parser.parse(file_path)
            
            # Should return an empty list for an empty file
            assert len(dependencies) == 0
        finally:
            os.unlink(file_path)
    
    def test_parse_invalid_yaml(self):
        """Test parsing an invalid YAML file."""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"""
name: myenv
channels:
  - conda-forge
dependencies:
  - python=3.9
  - numpy=1.21.0
  invalid yaml content
""")
            file_path = Path(f.name)
        
        try:
            parser = CondaEnvironmentParser()
            with pytest.raises(ParsingError):
                parser.parse(file_path)
        finally:
            os.unlink(file_path)
    
    def test_parse_missing_dependencies(self):
        """Test parsing a conda environment file with missing dependencies section."""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            f.write(b"""
name: myenv
channels:
  - conda-forge
  - defaults
""")
            file_path = Path(f.name)
        
        try:
            parser = CondaEnvironmentParser()
            dependencies = parser.parse(file_path)
            
            # Should return an empty list for a file with no dependencies
            assert len(dependencies) == 0
        finally:
            os.unlink(file_path)
