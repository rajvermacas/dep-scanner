"""Test cases for requirements.txt parser."""

import os
import tempfile
from pathlib import Path

import pytest

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.requirements_txt import RequirementsTxtParser


def test_requirements_txt_parser_can_parse():
    """Test that the parser can identify requirements.txt files."""
    parser = RequirementsTxtParser()
    
    # Should parse requirements.txt
    assert parser.can_parse(Path("requirements.txt"))
    assert parser.can_parse(Path("requirements-dev.txt"))
    assert parser.can_parse(Path("requirements-test.txt"))
    assert parser.can_parse(Path("path/to/requirements.txt"))
    
    # Should parse .txt files
    assert parser.can_parse(Path("custom_requirements.txt"))
    
    # Should not parse other files
    assert not parser.can_parse(Path("pyproject.toml"))
    assert not parser.can_parse(Path("setup.py"))
    assert not parser.can_parse(Path("package.json"))


def test_requirements_txt_parser_basic():
    """Test basic parsing of requirements.txt file."""
    parser = RequirementsTxtParser()
    
    # Create a temporary requirements.txt file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("""
# This is a comment
requests==2.25.1
flask>=2.0.0
numpy
pandas<1.3.0
# Another comment
pytest>=6.0.0,<7.0.0
""")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse the file
        dependencies = parser.parse(tmp_path)
        
        # Check the parsed dependencies
        assert len(dependencies) == 5
        
        # Check specific dependencies
        dep_names = [dep.name for dep in dependencies]
        assert "requests" in dep_names
        assert "flask" in dep_names
        assert "numpy" in dep_names
        assert "pandas" in dep_names
        assert "pytest" in dep_names
        
        # Check versions
        requests_dep = next(dep for dep in dependencies if dep.name == "requests")
        assert requests_dep.version == "==2.25.1"
        
        flask_dep = next(dep for dep in dependencies if dep.name == "flask")
        assert flask_dep.version == ">=2.0.0"
        
        numpy_dep = next(dep for dep in dependencies if dep.name == "numpy")
        assert numpy_dep.version is None
        
        pandas_dep = next(dep for dep in dependencies if dep.name == "pandas")
        assert pandas_dep.version == "<1.3.0"
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_requirements_txt_parser_complex():
    """Test parsing of complex requirements.txt file."""
    parser = RequirementsTxtParser()
    
    # Create a temporary requirements.txt file with complex requirements
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("""
# Requirements with extras
requests[security]==2.25.1
django[argon2]>=3.2.0

# Requirements with environment markers
importlib-metadata; python_version < '3.8'

# Line continuations
black==21.5b2 \\
    --hash=sha256:1fc0e0a2c8b4d341dace98d5f1679663c5b14687a2cce7af585e5a0a08f9cdb5

# Options (should be ignored)
-r other-requirements.txt
--no-binary :all:

# Editable installs (should be ignored)
-e git+https://github.com/user/project.git#egg=project
--editable ./path/to/project
""")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse the file
        dependencies = parser.parse(tmp_path)
        
        # Check the parsed dependencies
        assert len(dependencies) == 3
        
        # Check specific dependencies
        dep_names = [dep.name for dep in dependencies]
        assert "requests" in dep_names
        assert "django" in dep_names
        assert "importlib-metadata" in dep_names
        
        # Check versions
        requests_dep = next(dep for dep in dependencies if dep.name == "requests")
        assert requests_dep.version == "==2.25.1"
        
        django_dep = next(dep for dep in dependencies if dep.name == "django")
        assert django_dep.version == ">=3.2.0"
        
        # Check that black is not included (due to line continuation handling)
        assert "black" not in dep_names
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_requirements_txt_parser_errors():
    """Test error handling in requirements.txt parser."""
    parser = RequirementsTxtParser()
    
    # Test with non-existent file
    with pytest.raises(ParsingError):
        parser.parse(Path("/nonexistent/requirements.txt"))
    
    # Test with invalid requirements
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("""
# Valid requirement
requests==2.25.1
# Invalid requirement
@invalid==1.0.0
""")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse the file - should not raise an exception but log a warning
        dependencies = parser.parse(tmp_path)
        
        # Should only have the valid requirement
        assert len(dependencies) == 1
        assert dependencies[0].name == "requests"
        assert dependencies[0].version == "==2.25.1"
    finally:
        # Clean up
        os.unlink(tmp_path)
