"""Test cases for pyproject.toml parser."""

import os
import tempfile
from pathlib import Path

import pytest

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.pyproject_toml import PyprojectTomlParser


# Skip tests if tomli/tomllib is not available
import importlib.util

tomli_available = (
    importlib.util.find_spec("tomllib") is not None or 
    importlib.util.find_spec("tomli") is not None
)

pytestmark = pytest.mark.skipif(not tomli_available, reason="tomli/tomllib not available")


def test_pyproject_toml_parser_can_parse():
    """Test that the parser can identify pyproject.toml files."""
    parser = PyprojectTomlParser()
    
    # Should parse pyproject.toml
    assert parser.can_parse(Path("pyproject.toml"))
    assert parser.can_parse(Path("path/to/pyproject.toml"))
    
    # Should parse .toml files
    assert parser.can_parse(Path("custom.toml"))
    
    # Should not parse other files
    assert not parser.can_parse(Path("requirements.txt"))
    assert not parser.can_parse(Path("setup.py"))
    assert not parser.can_parse(Path("package.json"))


def test_pyproject_toml_parser_poetry():
    """Test parsing of pyproject.toml file with Poetry dependencies."""
    parser = PyprojectTomlParser()
    
    # Create a temporary pyproject.toml file with Poetry dependencies
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp_file:
        tmp_file.write("""
[tool.poetry]
name = "example-project"
version = "0.1.0"
description = "An example project"

[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.25.1"
flask = ">=2.0.0"
numpy = "*"

[tool.poetry.dev-dependencies]
pytest = "^6.2.5"
black = "^21.5b2"

[tool.poetry.group.docs.dependencies]
sphinx = "^4.0.0"
""")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse the file
        dependencies = parser.parse(tmp_path)
        
        # Check the parsed dependencies
        assert len(dependencies) == 6
        
        # Check specific dependencies
        dep_names = [dep.name for dep in dependencies]
        assert "requests" in dep_names
        assert "flask" in dep_names
        assert "numpy" in dep_names
        assert "pytest" in dep_names
        assert "black" in dep_names
        assert "sphinx" in dep_names
        
        # Python dependency should be excluded
        assert "python" not in dep_names
        
        # Check versions
        requests_dep = next(dep for dep in dependencies if dep.name == "requests")
        assert requests_dep.version == "^2.25.1"
        
        flask_dep = next(dep for dep in dependencies if dep.name == "flask")
        assert flask_dep.version == ">=2.0.0"
        
        numpy_dep = next(dep for dep in dependencies if dep.name == "numpy")
        assert numpy_dep.version == "*"
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_pyproject_toml_parser_pep621():
    """Test parsing of pyproject.toml file with PEP 621 dependencies."""
    parser = PyprojectTomlParser()
    
    # Create a temporary pyproject.toml file with PEP 621 dependencies
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp_file:
        tmp_file.write("""
[project]
name = "example-project"
version = "0.1.0"
description = "An example project"
dependencies = [
    "requests>=2.25.1",
    "flask==2.0.0",
    "numpy",
    "pandas>=1.3.0,<2.0.0",
]

[project.optional-dependencies]
test = [
    "pytest>=6.0.0",
    "pytest-cov>=2.12.0",
]
dev = [
    "black>=21.5b2",
]
""")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse the file
        dependencies = parser.parse(tmp_path)
        
        # Check the parsed dependencies
        assert len(dependencies) == 7
        
        # Check specific dependencies
        dep_names = [dep.name for dep in dependencies]
        assert "requests" in dep_names
        assert "flask" in dep_names
        assert "numpy" in dep_names
        assert "pandas" in dep_names
        assert "pytest" in dep_names
        assert "pytest-cov" in dep_names
        assert "black" in dep_names
        
        # Check versions
        requests_dep = next(dep for dep in dependencies if dep.name == "requests")
        assert requests_dep.version == ">=2.25.1"
        
        flask_dep = next(dep for dep in dependencies if dep.name == "flask")
        assert flask_dep.version == "==2.0.0"
        
        numpy_dep = next(dep for dep in dependencies if dep.name == "numpy")
        assert numpy_dep.version is None
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_pyproject_toml_parser_setuptools():
    """Test parsing of pyproject.toml file with setuptools dependencies."""
    parser = PyprojectTomlParser()
    
    # Create a temporary pyproject.toml file with setuptools dependencies
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp_file:
        tmp_file.write("""
[build-system]
requires = [
    "setuptools>=42",
    "wheel",
    "cython>=0.29.21",
]
build-backend = "setuptools.build_meta"
""")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse the file
        dependencies = parser.parse(tmp_path)
        
        # Check the parsed dependencies
        assert len(dependencies) == 3
        
        # Check specific dependencies
        dep_names = [dep.name for dep in dependencies]
        assert "setuptools" in dep_names
        assert "wheel" in dep_names
        assert "cython" in dep_names
        
        # Check versions
        setuptools_dep = next(dep for dep in dependencies if dep.name == "setuptools")
        assert setuptools_dep.version == ">=42"
        
        wheel_dep = next(dep for dep in dependencies if dep.name == "wheel")
        assert wheel_dep.version is None
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_pyproject_toml_parser_flit():
    """Test parsing of pyproject.toml file with Flit dependencies."""
    parser = PyprojectTomlParser()
    
    # Create a temporary pyproject.toml file with Flit dependencies
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp_file:
        tmp_file.write("""
[build-system]
requires = ["flit_core>=3.2,<4"]
build-backend = "flit_core.buildapi"

[tool.flit.metadata]
module = "example_project"
author = "Example Author"
requires = [
    "requests>=2.25.1",
    "flask==2.0.0",
    "numpy",
]
requires-dev = [
    "pytest>=6.0.0",
    "black>=21.5b2",
]
""")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse the file
        dependencies = parser.parse(tmp_path)
        
        # Check the parsed dependencies
        assert len(dependencies) == 6
        
        # Check specific dependencies
        dep_names = [dep.name for dep in dependencies]
        assert "flit_core" in dep_names
        assert "requests" in dep_names
        assert "flask" in dep_names
        assert "numpy" in dep_names
        assert "pytest" in dep_names
        assert "black" in dep_names
        
        # Check versions
        flit_dep = next(dep for dep in dependencies if dep.name == "flit_core")
        assert flit_dep.version == ">=3.2,<4"
        
        requests_dep = next(dep for dep in dependencies if dep.name == "requests")
        assert requests_dep.version == ">=2.25.1"
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_pyproject_toml_parser_errors():
    """Test error handling in pyproject.toml parser."""
    parser = PyprojectTomlParser()
    
    # Test with non-existent file
    with pytest.raises(ParsingError):
        parser.parse(Path("/nonexistent/pyproject.toml"))
    
    # Test with invalid TOML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp_file:
        tmp_file.write("""
[tool.poetry
name = "example-project"
version = "0.1.0"
""")  # Missing closing bracket
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse the file - should raise ParsingError
        with pytest.raises(ParsingError):
            parser.parse(tmp_path)
    finally:
        # Clean up
        os.unlink(tmp_path)
