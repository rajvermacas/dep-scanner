"""Utilities for file operations and detection."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from dep_scanner.exceptions import (
    DirectoryAccessError,
    LanguageDetectionError,
)

# Mapping of file extensions to programming languages
LANGUAGE_EXTENSIONS = {
    # Python
    ".py": "Python",
    ".pyi": "Python",
    ".pyx": "Python",
    ".pyd": "Python",
    ".pyw": "Python",
    
    # Java
    ".java": "Java",
    ".class": "Java",
    ".jar": "Java",
    
    # JavaScript/TypeScript
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    
    # Scala
    ".scala": "Scala",
    ".sc": "Scala",
    
    # Go
    ".go": "Go",
    
    # Ruby
    ".rb": "Ruby",
    ".rake": "Ruby",
    ".gemspec": "Ruby",
    
    # PHP
    ".php": "PHP",
    ".phtml": "PHP",
    ".php5": "PHP",
    ".php7": "PHP",
    
    # Other common languages
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".cs": "C#",
    ".rs": "Rust",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".groovy": "Groovy",
    ".pl": "Perl",
    ".pm": "Perl",
    ".r": "R",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    ".less": "LESS",
    ".xml": "XML",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".sql": "SQL",
}

# Mapping of file names to languages or file types
SPECIAL_FILES = {
    "Dockerfile": "Docker",
    "Makefile": "Make",
    "CMakeLists.txt": "CMake",
    "Jenkinsfile": "Jenkins",
    ".gitignore": "Git",
    "requirements.txt": "Python-Dependencies",
    "pyproject.toml": "Python-Dependencies",
    "setup.py": "Python-Dependencies",
    "package.json": "Node-Dependencies",
    "yarn.lock": "Node-Dependencies",
    "pom.xml": "Maven-Dependencies",
    "build.gradle": "Gradle-Dependencies",
    "build.sbt": "SBT-Dependencies",
    "go.mod": "Go-Dependencies",
    "Gemfile": "Ruby-Dependencies",
    "composer.json": "PHP-Dependencies",
}


def get_file_language(file_path: Path) -> Optional[str]:
    """Determine the programming language of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Language name or None if the language cannot be determined
    """
    # Check if it's a special file first
    if file_path.name in SPECIAL_FILES:
        return SPECIAL_FILES[file_path.name]
    
    # Check by extension
    extension = file_path.suffix.lower()
    return LANGUAGE_EXTENSIONS.get(extension)


def get_file_type(file_path: Path) -> str:
    """Get a more general file type classification.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File type classification
    """
    language = get_file_language(file_path)
    
    if language:
        # If it's a dependency file, return that classification
        if language.endswith("-Dependencies"):
            return "dependency_file"
        
        # Otherwise it's a source file
        return "source_file"
    
    # Binary files
    binary_extensions = {".exe", ".dll", ".so", ".dylib", ".bin", ".dat", ".o"}
    if file_path.suffix.lower() in binary_extensions:
        return "binary_file"
    
    # Image files
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp"}
    if file_path.suffix.lower() in image_extensions:
        return "image_file"
    
    # Document files
    doc_extensions = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"}
    if file_path.suffix.lower() in doc_extensions:
        return "document_file"
    
    # Default to unknown
    return "unknown_file"


def analyze_directory_extensions(directory_path: Path, ignore_patterns: List[str] = None) -> Dict[str, int]:
    """Analyze a directory and count file extensions.
    
    Args:
        directory_path: Path to the directory to analyze
        ignore_patterns: Optional list of patterns to ignore
        
    Returns:
        Dictionary mapping file extensions to their count
        
    Raises:
        DirectoryAccessError: If the directory cannot be accessed
    """
    from dep_scanner.scanner import scan_directory
    
    if not directory_path.exists():
        raise DirectoryAccessError(directory_path, f"Directory does not exist: {directory_path}")
    
    if not directory_path.is_dir():
        raise DirectoryAccessError(directory_path, f"Not a directory: {directory_path}")
    
    if not os.access(directory_path, os.R_OK):
        raise DirectoryAccessError(directory_path, f"Permission denied: {directory_path}")
    
    extension_counts: Dict[str, int] = {}
    
    try:
        for file_path in scan_directory(str(directory_path), ignore_patterns):
            extension = file_path.suffix.lower()
            if extension:
                extension_counts[extension] = extension_counts.get(extension, 0) + 1
    except Exception as e:
        logging.error(f"Error analyzing directory extensions: {e}")
        # Re-raise as our custom exception
        raise DirectoryAccessError(directory_path, f"Error analyzing directory: {str(e)}")
    
    return extension_counts


def detect_languages(directory_path: Path, ignore_patterns: List[str] = None) -> Dict[str, float]:
    """Detect programming languages used in a directory based on file extensions.
    
    Args:
        directory_path: Path to the directory to analyze
        ignore_patterns: Optional list of patterns to ignore
        
    Returns:
        Dictionary mapping language names to their usage percentage
        
    Raises:
        DirectoryAccessError: If the directory cannot be accessed
        LanguageDetectionError: If language detection fails
    """
    from dep_scanner.scanner import scan_directory
    
    if not directory_path.exists():
        raise DirectoryAccessError(directory_path, f"Directory does not exist: {directory_path}")
    
    if not directory_path.is_dir():
        raise DirectoryAccessError(directory_path, f"Not a directory: {directory_path}")
    
    if not os.access(directory_path, os.R_OK):
        raise DirectoryAccessError(directory_path, f"Permission denied: {directory_path}")
    
    language_counts: Dict[str, int] = {}
    total_files = 0
    errors = []
    
    try:
        for file_path in scan_directory(str(directory_path), ignore_patterns):
            try:
                language = get_file_language(file_path)
                if language and not language.endswith("-Dependencies"):
                    language_counts[language] = language_counts.get(language, 0) + 1
                    total_files += 1
            except Exception as e:
                # Log the error but continue processing other files
                logging.warning(f"Error detecting language for {file_path}: {e}")
                errors.append(f"{file_path}: {str(e)}")
    except Exception as e:
        logging.error(f"Error scanning directory for language detection: {e}")
        raise DirectoryAccessError(directory_path, f"Error scanning directory: {str(e)}")
    
    # Calculate percentages
    language_percentages: Dict[str, float] = {}
    if total_files > 0:
        for language, count in language_counts.items():
            language_percentages[language] = (count / total_files) * 100
    
    # If we encountered errors but were able to process some files, log a warning
    if errors and language_percentages:
        logging.warning(f"Completed language detection with {len(errors)} errors")
    
    # If we couldn't detect any languages and had errors, raise an exception
    if not language_percentages and errors:
        error_msg = f"Failed to detect languages in {directory_path}. Errors: {'; '.join(errors[:5])}"
        if len(errors) > 5:
            error_msg += f" and {len(errors) - 5} more"
        raise LanguageDetectionError(None, error_msg)
    
    return language_percentages


def detect_dependency_files(directory_path: Path, ignore_patterns: List[str] = None) -> List[Path]:
    """Detect dependency definition files in a directory.
    
    Args:
        directory_path: Path to the directory to analyze
        ignore_patterns: Optional list of patterns to ignore
        
    Returns:
        List of paths to dependency files
        
    Raises:
        DirectoryAccessError: If the directory cannot be accessed
    """
    from dep_scanner.scanner import scan_directory
    
    if not directory_path.exists():
        raise DirectoryAccessError(directory_path, f"Directory does not exist: {directory_path}")
    
    if not directory_path.is_dir():
        raise DirectoryAccessError(directory_path, f"Not a directory: {directory_path}")
    
    if not os.access(directory_path, os.R_OK):
        raise DirectoryAccessError(directory_path, f"Permission denied: {directory_path}")
    
    dependency_files: List[Path] = []
    
    try:
        for file_path in scan_directory(str(directory_path), ignore_patterns):
            try:
                language = get_file_language(file_path)
                if language and language.endswith("-Dependencies"):
                    dependency_files.append(file_path)
            except Exception as e:
                # Log the error but continue processing other files
                logging.warning(f"Error processing dependency file {file_path}: {e}")
    except Exception as e:
        logging.error(f"Error scanning directory for dependency files: {e}")
        raise DirectoryAccessError(directory_path, f"Error scanning directory: {str(e)}")
    
    return dependency_files
