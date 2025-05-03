"""Test cases for parser manager."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.parser_manager import ParserManager
from dep_scanner.parsers.requirements_txt import RequirementsTxtParser
from dep_scanner.parsers.pyproject_toml import PyprojectTomlParser
from dep_scanner.scanner import Dependency


def test_parser_manager_initialization():
    """Test that the parser manager initializes correctly."""
    manager = ParserManager()
    
    # Check that parsers are registered
    assert len(manager.parsers) >= 2  # At least requirements.txt and pyproject.toml parsers
    
    # Check that specific parsers are available
    parser_classes = [parser.__class__ for parser in manager.parsers.values()]
    assert RequirementsTxtParser in parser_classes
    assert PyprojectTomlParser in parser_classes


def test_get_parser_for_file():
    """Test that the parser manager can find the correct parser for a file."""
    manager = ParserManager()
    
    # Test requirements.txt parser
    parser = manager.get_parser_for_file(Path("requirements.txt"))
    assert parser is not None
    assert isinstance(parser, RequirementsTxtParser)
    
    # Test pyproject.toml parser
    parser = manager.get_parser_for_file(Path("pyproject.toml"))
    assert parser is not None
    assert isinstance(parser, PyprojectTomlParser)
    
    # Test with unsupported file
    parser = manager.get_parser_for_file(Path("unsupported.xyz"))
    assert parser is None


def test_parse_file():
    """Test parsing a single file."""
    manager = ParserManager()
    
    # Create a temporary requirements.txt file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("""
requests==2.25.1
flask>=2.0.0
""")
        requirements_path = Path(tmp_file.name)
    
    try:
        # Parse the requirements.txt file
        dependencies = manager.parse_file(requirements_path)
        
        # Check the parsed dependencies
        assert len(dependencies) == 2
        assert any(dep.name == "requests" for dep in dependencies)
        assert any(dep.name == "flask" for dep in dependencies)
    finally:
        # Clean up
        os.unlink(requirements_path)
    
    # Test with unsupported file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as tmp_file:
        tmp_file.write("This is not a supported file format")
        unsupported_path = Path(tmp_file.name)
    
    try:
        # Parse the unsupported file - should raise ParsingError
        with pytest.raises(ParsingError):
            manager.parse_file(unsupported_path)
    finally:
        # Clean up
        os.unlink(unsupported_path)


def test_parse_files():
    """Test parsing multiple files."""
    manager = ParserManager()
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as req_file:
        req_file.write("""
requests==2.25.1
flask>=2.0.0
""")
        requirements_path = Path(req_file.name)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as unsupported_file:
        unsupported_file.write("This is not a supported file format")
        unsupported_path = Path(unsupported_file.name)
    
    try:
        # Parse both files
        results = manager.parse_files([requirements_path, unsupported_path])
        
        # Check the results
        assert len(results) == 2
        assert requirements_path in results
        assert unsupported_path in results
        
        # Check requirements.txt dependencies
        assert len(results[requirements_path]) == 2
        
        # Check unsupported file (should be empty list, not error)
        assert len(results[unsupported_path]) == 0
    finally:
        # Clean up
        os.unlink(requirements_path)
        os.unlink(unsupported_path)


def test_get_supported_extensions_and_filenames():
    """Test getting supported extensions and filenames."""
    manager = ParserManager()
    
    extensions = manager.get_supported_extensions()
    filenames = manager.get_supported_filenames()
    
    # Check that we have some extensions and filenames
    assert len(extensions) > 0
    assert len(filenames) > 0
    
    # Check specific extensions and filenames we expect to support
    assert ".txt" in extensions
    assert ".toml" in extensions
    assert "requirements.txt" in filenames
    assert "pyproject.toml" in filenames


def test_extract_pip_dependencies():
    """Test extracting pip dependencies."""
    # Create test dependencies
    test_dependencies = [
        Dependency(name="pytest", version="7.0.0", source_file="pip_database"),
        Dependency(name="requests", version="2.28.1", source_file="pip_database")
    ]
    
    # Create a mock parser instance
    mock_parser = mock.MagicMock()
    mock_parser.parse.return_value = test_dependencies
    
    # Create parser manager and manually set the parsers dictionary
    manager = ParserManager()
    manager.parsers = {"pip_dependencies": mock_parser}
    
    # Extract dependencies
    dependencies = manager.extract_pip_dependencies()
    
    # Verify the dependencies were extracted correctly
    assert len(dependencies) == 2
    assert dependencies[0].name == "pytest"
    assert dependencies[1].name == "requests"


def test_extract_venv_dependencies():
    """Test extracting virtual environment dependencies."""
    # Create test dependencies
    test_dependencies = [
        Dependency(name="django", version="4.0.0", source_file="venv:/path/to/venv"),
        Dependency(name="flask", version="2.0.1", source_file="venv:/path/to/venv")
    ]
    
    # Create a mock parser instance
    mock_parser = mock.MagicMock()
    mock_parser.parse_venv.return_value = test_dependencies
    
    # Create parser manager and manually set the parsers dictionary
    manager = ParserManager()
    manager.parsers = {"pip_dependencies": mock_parser}
    
    # Extract dependencies
    dependencies = manager.extract_venv_dependencies(Path("/path/to/venv"))
    
    # Verify the dependencies were extracted correctly
    assert len(dependencies) == 2
    assert dependencies[0].name == "django"
    assert dependencies[1].name == "flask"


def test_extract_pip_dependencies_error():
    """Test handling errors when extracting pip dependencies."""
    # Create a mock parser instance
    mock_parser = mock.MagicMock()
    mock_parser.parse.side_effect = Exception("Test error")
    
    # Create parser manager and manually set the parsers dictionary
    manager = ParserManager()
    manager.parsers = {"pip_dependencies": mock_parser}
    
    # Extract dependencies - should handle the exception gracefully
    try:
        dependencies = manager.extract_pip_dependencies()
        # Verify that no dependencies were returned
        assert len(dependencies) == 0
    except Exception as e:
        pytest.fail(f"extract_pip_dependencies() raised {type(e).__name__} unexpectedly!")


def test_extract_venv_dependencies_error():
    """Test handling errors when extracting virtual environment dependencies."""
    # Create a mock parser instance
    mock_parser = mock.MagicMock()
    mock_parser.parse_venv.side_effect = Exception("Test error")
    
    # Create parser manager and manually set the parsers dictionary
    manager = ParserManager()
    manager.parsers = {"pip_dependencies": mock_parser}
    
    # Extract dependencies - should raise a ParsingError
    with pytest.raises(ParsingError) as excinfo:
        manager.extract_venv_dependencies(Path("/path/to/venv"))
    
    # Verify that the error message contains the original exception message
    assert "Test error" in str(excinfo.value)
