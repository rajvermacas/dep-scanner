"""Test cases for file_utils.py functionality."""
import tempfile
from pathlib import Path


from dep_scanner.file_utils import (
    get_file_language,
    get_file_type,
    analyze_directory_extensions,
    detect_languages,
    detect_dependency_files,
)


def test_get_file_language():
    """Test the get_file_language function."""
    # Test Python files
    assert get_file_language(Path("test.py")) == "Python"
    assert get_file_language(Path("test.pyi")) == "Python"
    
    # Test JavaScript/TypeScript files
    assert get_file_language(Path("test.js")) == "JavaScript"
    assert get_file_language(Path("test.ts")) == "TypeScript"
    
    # Test Java files
    assert get_file_language(Path("Test.java")) == "Java"
    
    # Test special files
    assert get_file_language(Path("requirements.txt")) == "Python-Dependencies"
    assert get_file_language(Path("package.json")) == "Node-Dependencies"
    assert get_file_language(Path("Dockerfile")) == "Docker"
    
    # Test unknown extension
    assert get_file_language(Path("test.unknown")) is None
    
    # Test no extension
    assert get_file_language(Path("testfile")) is None


def test_get_file_type():
    """Test the get_file_type function."""
    # Test source files
    assert get_file_type(Path("test.py")) == "source_file"
    assert get_file_type(Path("test.java")) == "source_file"
    
    # Test dependency files
    assert get_file_type(Path("requirements.txt")) == "dependency_file"
    assert get_file_type(Path("package.json")) == "dependency_file"
    
    # Test binary files
    assert get_file_type(Path("test.exe")) == "binary_file"
    assert get_file_type(Path("test.dll")) == "binary_file"
    
    # Test image files
    assert get_file_type(Path("test.png")) == "image_file"
    assert get_file_type(Path("test.jpg")) == "image_file"
    
    # Test document files
    assert get_file_type(Path("test.pdf")) == "document_file"
    assert get_file_type(Path("test.docx")) == "document_file"
    
    # Test unknown files
    assert get_file_type(Path("test.unknown")) == "unknown_file"


def test_analyze_directory_extensions():
    """Test analyzing directory extensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / 'file1.py').touch()
        (Path(tmpdir) / 'file2.py').touch()
        (Path(tmpdir) / 'file3.js').touch()
        (Path(tmpdir) / 'file4.txt').touch()
        
        # Create a subdirectory with more files
        subdir = Path(tmpdir) / 'subdir'
        subdir.mkdir()
        (subdir / 'file5.py').touch()
        (subdir / 'file6.java').touch()
        
        # Analyze extensions
        extensions = analyze_directory_extensions(Path(tmpdir))
        
        # Verify counts
        assert extensions.get('.py', 0) == 3
        assert extensions.get('.js', 0) == 1
        assert extensions.get('.java', 0) == 1
        assert extensions.get('.txt', 0) == 1


def test_detect_languages():
    """Test language detection based on file extensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / 'file1.py').touch()
        (Path(tmpdir) / 'file2.py').touch()
        (Path(tmpdir) / 'file3.js').touch()
        (Path(tmpdir) / 'file4.java').touch()
        
        # Create a dependency file (should not count in language percentages)
        (Path(tmpdir) / 'requirements.txt').touch()
        
        # Detect languages
        languages = detect_languages(Path(tmpdir))
        
        # Verify percentages (4 source files total)
        assert languages.get('Python', 0) == 50.0  # 2/4 = 50%
        assert languages.get('JavaScript', 0) == 25.0  # 1/4 = 25%
        assert languages.get('Java', 0) == 25.0  # 1/4 = 25%
        
        # Dependency file should not be included
        assert 'Python-Dependencies' not in languages


def test_detect_languages_empty_directory():
    """Test language detection on an empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        languages = detect_languages(Path(tmpdir))
        assert languages == {}


def test_detect_dependency_files():
    """Test detection of dependency files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / 'file1.py').touch()
        (Path(tmpdir) / 'requirements.txt').touch()
        (Path(tmpdir) / 'package.json').touch()
        
        # Create a subdirectory with more files
        subdir = Path(tmpdir) / 'subdir'
        subdir.mkdir()
        (subdir / 'pyproject.toml').touch()
        
        # Detect dependency files
        dep_files = detect_dependency_files(Path(tmpdir))
        
        # Verify results
        assert len(dep_files) == 3
        assert any('requirements.txt' in str(f) for f in dep_files)
        assert any('package.json' in str(f) for f in dep_files)
        assert any('pyproject.toml' in str(f) for f in dep_files)


def test_detect_dependency_files_with_ignore():
    """Test dependency file detection with ignore patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / 'requirements.txt').touch()
        (Path(tmpdir) / 'package.json').touch()
        
        # Create a subdirectory to be ignored
        subdir = Path(tmpdir) / 'node_modules'
        subdir.mkdir()
        (subdir / 'package.json').touch()
        
        # Detect dependency files with ignore pattern
        dep_files = detect_dependency_files(Path(tmpdir), ignore_patterns=['node_modules/'])
        
        # Verify results
        assert len(dep_files) == 2
        assert all('node_modules' not in str(f) for f in dep_files)
