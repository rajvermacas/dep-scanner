"""Test cases for scanner.py functionality."""
import tempfile
from pathlib import Path

import pytest

from dep_scanner.scanner import scan_directory, _should_ignore


def test_scan_directory_basic():
    """Test basic directory scanning functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / 'file1.txt').touch()
        (Path(tmpdir) / 'file2.txt').touch()
        (Path(tmpdir) / 'subdir').mkdir()
        (Path(tmpdir) / 'subdir' / 'file3.txt').touch()
        
        # Scan directory
        files = list(scan_directory(tmpdir))
        
        # Verify all files are found
        assert len(files) == 3
        assert any('file1.txt' in str(f) for f in files)
        assert any('file2.txt' in str(f) for f in files)
        assert any('file3.txt' in str(f) for f in files)


def test_scan_directory_with_ignore():
    """Test directory scanning with ignore patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / 'file1.txt').touch()
        (Path(tmpdir) / 'ignore.txt').touch()
        (Path(tmpdir) / 'subdir').mkdir()
        (Path(tmpdir) / 'subdir' / 'file2.txt').touch()
        
        # Scan with ignore pattern
        files = list(scan_directory(tmpdir, ignore_patterns=['ignore.txt']))
        
        # Verify ignored file is not included
        assert len(files) == 2
        assert any('file1.txt' in str(f) for f in files)
        assert any('file2.txt' in str(f) for f in files)
        assert not any('ignore.txt' in str(f) for f in files)


def test_should_ignore():
    """Test the _should_ignore helper function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        test_file = root / 'test.txt'
        test_file.touch()
        
        # Test exact match
        assert _should_ignore(test_file, root, ['test.txt']) is True
        
        # Test pattern match
        assert _should_ignore(test_file, root, ['*.txt']) is True
        
        # Test directory pattern
        subdir = root / 'subdir'
        subdir.mkdir()
        subfile = subdir / 'file.txt'
        subfile.touch()
        assert _should_ignore(subfile, root, ['subdir/']) is True
        
        # Test non-match
        assert _should_ignore(test_file, root, ['other.txt']) is False


def test_empty_directory():
    """Test scanning an empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = list(scan_directory(tmpdir))
        assert len(files) == 0


def test_non_existent_directory():
    """Test scanning a non-existent directory raises appropriate error."""
    # Updated to expect our custom DirectoryAccessError instead of FileNotFoundError
    from dep_scanner.exceptions import DirectoryAccessError
    with pytest.raises(DirectoryAccessError) as excinfo:
        list(scan_directory('/nonexistent/path'))
    
    # Verify the error message contains useful information
    assert "Directory not found" in str(excinfo.value)


def test_permission_denied_directory(tmp_path):
    """Test scanning a directory with permission denied."""
    # Create a directory we can't access
    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()
    restricted_dir.chmod(0o000)  # No permissions
    
    try:
        # Should skip the restricted directory but not fail
        files = list(scan_directory(str(restricted_dir)))
        assert len(files) == 0
    finally:
        # Clean up by restoring permissions
        restricted_dir.chmod(0o755)


def test_permission_denied_file(tmp_path):
    """Test handling of files with permission denied."""
    # Create a directory with a restricted file
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()
    test_file = test_dir / "restricted.txt"
    test_file.touch()
    test_file.chmod(0o000)  # No permissions
    
    try:
        # Should skip the restricted file but not fail
        files = list(scan_directory(str(test_dir)))
        assert len(files) == 0
    finally:
        # Clean up by restoring permissions
        test_file.chmod(0o644)