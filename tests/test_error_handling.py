"""Test cases for error handling functionality."""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from dep_scanner.exceptions import (
    DirectoryAccessError,
)
from dep_scanner.file_utils import (
    analyze_directory_extensions,
    detect_languages,
    detect_dependency_files,
)
from dep_scanner.scanner import scan_directory, _should_ignore


def test_directory_access_error():
    """Test that DirectoryAccessError is raised for non-existent directories."""
    # Test with non-existent directory
    with pytest.raises(DirectoryAccessError) as excinfo:
        list(scan_directory("/nonexistent/path"))
    
    assert "Directory not found" in str(excinfo.value)
    
    # Test with a file instead of a directory
    with tempfile.NamedTemporaryFile() as tmp_file:
        with pytest.raises(DirectoryAccessError) as excinfo:
            list(scan_directory(tmp_file.name))
        
        assert "Not a directory" in str(excinfo.value)


def test_permission_error_handling():
    """Test handling of permission errors."""
    # Instead of testing with actual permission changes (which can be unreliable in test environments),
    # we'll mock the os.access function to simulate permission denied
    with patch('os.access', return_value=False):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # This should raise DirectoryAccessError because we mocked os.access to return False
            with pytest.raises(DirectoryAccessError) as excinfo:
                analyze_directory_extensions(tmp_path)
            
            assert "Permission denied" in str(excinfo.value)


def test_should_ignore_error_handling():
    """Test error handling in _should_ignore function."""
    # Test with a file path that is not relative to root_dir
    root_dir = Path("/some/root")
    file_path = Path("/different/path/file.txt")
    
    with pytest.raises(ValueError) as excinfo:
        _should_ignore(file_path, root_dir, ["*.txt"])
    
    assert "not relative to root directory" in str(excinfo.value)


def test_analyze_directory_extensions_error_handling():
    """Test error handling in analyze_directory_extensions function."""
    # Test with non-existent directory
    with pytest.raises(DirectoryAccessError) as excinfo:
        analyze_directory_extensions(Path("/nonexistent/path"))
    
    assert "Directory does not exist" in str(excinfo.value)


def test_detect_languages_error_handling():
    """Test error handling in detect_languages function."""
    # Test with non-existent directory
    with pytest.raises(DirectoryAccessError) as excinfo:
        detect_languages(Path("/nonexistent/path"))
    
    assert "Directory does not exist" in str(excinfo.value)


def test_detect_dependency_files_error_handling():
    """Test error handling in detect_dependency_files function."""
    # Test with non-existent directory
    with pytest.raises(DirectoryAccessError) as excinfo:
        detect_dependency_files(Path("/nonexistent/path"))
    
    assert "Directory does not exist" in str(excinfo.value)


@patch('dep_scanner.scanner.scan_directory')
def test_scan_directory_exception_handling(mock_scan):
    """Test that exceptions in scan_directory are properly handled."""
    # Setup the mock to raise an exception
    mock_scan.side_effect = Exception("Test exception")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(DirectoryAccessError) as excinfo:
            list(detect_dependency_files(Path(tmpdir)))
        
        assert "Error scanning directory" in str(excinfo.value)


def test_error_message_content():
    """Test that error messages contain useful information."""
    # Instead of testing the logging mechanism, let's test the error message content
    with pytest.raises(DirectoryAccessError) as excinfo:
        detect_languages(Path("/nonexistent/path"))
    
    # Verify that the error message contains useful information
    error_message = str(excinfo.value)
    assert "Directory does not exist" in error_message
    assert "/nonexistent/path" in error_message


def test_graceful_handling_of_permission_issues():
    """Test that permission issues are handled gracefully during scanning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file with no permissions
        test_file = Path(tmpdir) / "noperm.txt"
        test_file.touch()
        
        try:
            # Remove all permissions
            test_file.chmod(0o000)
            
            # This should not raise an exception, just skip the file
            files = list(scan_directory(tmpdir))
            
            # The directory should be scanned successfully, but the file should be skipped
            assert len(files) == 0
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)
