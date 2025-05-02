"""File type detection system for the dependency scanner."""

import logging
import mimetypes
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

from dep_scanner.exceptions import FileAccessError

# Initialize mimetypes
mimetypes.init()


class FileCategory(Enum):
    """Categories for different file types."""
    SOURCE_CODE = "source_code"
    DEPENDENCY_FILE = "dependency_file"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    BINARY = "binary"
    IMAGE = "image"
    DATA = "data"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


@dataclass
class FileType:
    """Represents a file type with its associated metadata."""
    name: str
    extensions: List[str]
    category: FileCategory
    mime_types: List[str] = None
    patterns: List[Pattern] = None
    shebang: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values for optional fields."""
        if self.mime_types is None:
            self.mime_types = []
        if self.patterns is None:
            self.patterns = []


# File signatures (magic numbers) for binary file detection
# Format: (offset, signature bytes, description)
FILE_SIGNATURES = [
    (0, b'\x7FELF', 'ELF executable'),
    (0, b'MZ', 'Windows executable'),
    (0, b'PK\x03\x04', 'ZIP archive'),
    (0, b'\x1F\x8B\x08', 'GZIP archive'),
    (0, b'BZh', 'BZIP2 archive'),
    (0, b'\x89PNG\r\n\x1A\n', 'PNG image'),
    (0, b'\xFF\xD8\xFF', 'JPEG image'),
    (0, b'GIF8', 'GIF image'),
    (0, b'%PDF', 'PDF document'),
]

# Shebang patterns for script detection
SHEBANG_PATTERNS = {
    r'^#!/usr/bin/env\s+python': 'Python',
    r'^#!/usr/bin/python': 'Python',
    r'^#!/bin/bash': 'Bash',
    r'^#!/bin/sh': 'Shell',
    r'^#!/usr/bin/env\s+node': 'JavaScript',
    r'^#!/usr/bin/node': 'JavaScript',
    r'^#!/usr/bin/env\s+ruby': 'Ruby',
    r'^#!/usr/bin/ruby': 'Ruby',
    r'^#!/usr/bin/env\s+perl': 'Perl',
    r'^#!/usr/bin/perl': 'Perl',
}

# Content patterns for language detection
CONTENT_PATTERNS = {
    # Python patterns
    'Python': [
        re.compile(r'^\s*import\s+[a-zA-Z0-9_]+', re.MULTILINE),
        re.compile(r'^\s*from\s+[a-zA-Z0-9_.]+\s+import\s+', re.MULTILINE),
        re.compile(r'^\s*def\s+[a-zA-Z0-9_]+\s*\(', re.MULTILINE),
        re.compile(r'^\s*class\s+[a-zA-Z0-9_]+\s*(\(.*\))?:', re.MULTILINE),
    ],
    # JavaScript patterns
    'JavaScript': [
        re.compile(r'^\s*import\s+.*\s+from\s+[\'"]', re.MULTILINE),
        re.compile(r'^\s*const\s+[a-zA-Z0-9_]+\s*=', re.MULTILINE),
        re.compile(r'^\s*let\s+[a-zA-Z0-9_]+\s*=', re.MULTILINE),
        re.compile(r'^\s*var\s+[a-zA-Z0-9_]+\s*=', re.MULTILINE),
        re.compile(r'^\s*function\s+[a-zA-Z0-9_]+\s*\(', re.MULTILINE),
    ],
    # Java patterns
    'Java': [
        re.compile(r'^\s*package\s+[a-zA-Z0-9_.]+;', re.MULTILINE),
        re.compile(r'^\s*import\s+[a-zA-Z0-9_.]+;', re.MULTILINE),
        re.compile(r'^\s*public\s+(class|interface|enum)\s+[a-zA-Z0-9_]+', re.MULTILINE),
        re.compile(r'^\s*private\s+(class|interface|enum)\s+[a-zA-Z0-9_]+', re.MULTILINE),
    ],
    # XML patterns
    'XML': [
        re.compile(r'^\s*<\?xml\s+version=', re.MULTILINE),
    ],
    # HTML patterns
    'HTML': [
        re.compile(r'<!DOCTYPE\s+html>', re.IGNORECASE),
        re.compile(r'<html[^>]*>.*</html>', re.DOTALL | re.IGNORECASE),
    ],
    # JSON patterns
    'JSON': [
        re.compile(r'^\s*\{\s*"[^"]+"\s*:', re.MULTILINE),
    ],
    # YAML patterns
    'YAML': [
        re.compile(r'^\s*[a-zA-Z0-9_]+:\s*[^\s]', re.MULTILINE),
    ],
    # Markdown patterns
    'Markdown': [
        re.compile(r'^#\s+.*$', re.MULTILINE),
        re.compile(r'^\s*[-*]\s+.*$', re.MULTILINE),
    ],
}

# File encodings to try when reading files
ENCODINGS_TO_TRY = [
    'utf-8',
    'latin-1',
    'utf-16',
    'utf-32',
    'ascii',
    'cp1252',
]


def read_file_with_encoding(file_path: Path, max_read_size: int = 8192) -> Tuple[str, str]:
    """Read a file with proper encoding detection.
    
    Args:
        file_path: Path to the file to read
        max_read_size: Maximum number of bytes to read
        
    Returns:
        Tuple of (file_content, encoding_used)
        
    Raises:
        FileAccessError: If the file cannot be read
    """
    if not file_path.exists():
        raise FileAccessError(file_path, f"File does not exist: {file_path}")
    
    if not os.access(file_path, os.R_OK):
        raise FileAccessError(file_path, f"Permission denied: {file_path}")
    
    # First, try to detect if it's a binary file
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(max_read_size)
            
            # Check for null bytes which often indicate binary data
            if b'\x00' in raw_data:
                return None, "binary"
            
            # Check for file signatures
            for offset, signature, description in FILE_SIGNATURES:
                if raw_data[offset:offset+len(signature)] == signature:
                    return None, "binary"
    except Exception as e:
        raise FileAccessError(file_path, f"Error reading file: {str(e)}")
    
    # Try different encodings
    for encoding in ENCODINGS_TO_TRY:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read(max_read_size)
                return content, encoding
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise FileAccessError(file_path, f"Error reading file with encoding {encoding}: {str(e)}")
    
    # If all encodings fail, try binary mode and decode with latin-1 as a fallback
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(max_read_size)
            return raw_data.decode('latin-1'), 'latin-1'
    except Exception as e:
        raise FileAccessError(file_path, f"Error reading file in binary mode: {str(e)}")


def detect_shebang(content: str) -> Optional[str]:
    """Detect programming language from shebang line.
    
    Args:
        content: File content to analyze
        
    Returns:
        Detected language or None if no shebang is found
    """
    if not content or not content.startswith('#!'):
        return None
    
    first_line = content.split('\n', 1)[0]
    
    for pattern, language in SHEBANG_PATTERNS.items():
        if re.match(pattern, first_line):
            return language
    
    return None


def detect_language_from_content(content: str) -> Optional[str]:
    """Detect programming language from file content patterns.
    
    Args:
        content: File content to analyze
        
    Returns:
        Detected language or None if no patterns match
    """
    if not content:
        return None
    
    # Check for shebang first
    shebang_language = detect_shebang(content)
    if shebang_language:
        return shebang_language
    
    # Check content patterns
    matches = {}
    
    for language, patterns in CONTENT_PATTERNS.items():
        match_count = 0
        for pattern in patterns:
            if pattern.search(content):
                match_count += 1
        
        if match_count > 0:
            matches[language] = match_count
    
    if matches:
        # Return the language with the most matches
        return max(matches.items(), key=lambda x: x[1])[0]
    
    return None


def get_mime_type(file_path: Path) -> str:
    """Get the MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


def detect_file_type(file_path: Path, use_content_detection: bool = True) -> Tuple[str, FileCategory, str]:
    """Detect the type of a file using multiple methods.
    
    Args:
        file_path: Path to the file
        use_content_detection: Whether to analyze file content for more accurate detection
        
    Returns:
        Tuple of (file_type_name, file_category, detection_method)
        
    Raises:
        FileAccessError: If the file cannot be accessed
    """
    from dep_scanner.file_utils import get_file_language, get_file_type
    
    # First try extension-based detection
    language = get_file_language(file_path)
    file_type = get_file_type(file_path)
    detection_method = "extension"
    
    # Map file_type to FileCategory
    category_mapping = {
        "source_file": FileCategory.SOURCE_CODE,
        "dependency_file": FileCategory.DEPENDENCY_FILE,
        "binary_file": FileCategory.BINARY,
        "image_file": FileCategory.IMAGE,
        "document_file": FileCategory.DOCUMENTATION,
        "unknown_file": FileCategory.UNKNOWN,
    }
    
    category = category_mapping.get(file_type, FileCategory.UNKNOWN)
    
    # If extension-based detection was inconclusive and content detection is enabled
    if (language is None or category == FileCategory.UNKNOWN) and use_content_detection:
        try:
            content, encoding = read_file_with_encoding(file_path)
            
            # If it's a binary file, we can't do content-based detection
            if encoding == "binary":
                return "Binary File", FileCategory.BINARY, "binary_signature"
            
            # Try content-based language detection
            content_language = detect_language_from_content(content)
            if content_language:
                language = content_language
                category = FileCategory.SOURCE_CODE
                detection_method = "content_pattern"
            
            # Check for specific file types based on content
            if content and not content_language:
                # Check for XML
                if content.lstrip().startswith('<?xml') or content.lstrip().startswith('<'):
                    language = "XML"
                    category = FileCategory.DATA
                    detection_method = "content_pattern"
                
                # Check for JSON
                elif content.lstrip().startswith('{') or content.lstrip().startswith('['):
                    try:
                        import json
                        json.loads(content)
                        language = "JSON"
                        category = FileCategory.DATA
                        detection_method = "content_pattern"
                    except json.JSONDecodeError:
                        pass
                
                # Check for YAML
                elif re.search(r'^\s*[a-zA-Z0-9_]+:\s*[^\s]', content, re.MULTILINE):
                    language = "YAML"
                    category = FileCategory.DATA
                    detection_method = "content_pattern"
        except FileAccessError:
            # If we can't read the file, stick with extension-based detection
            pass
        except Exception as e:
            logging.warning(f"Error during content-based detection for {file_path}: {e}")
    
    # If we still don't know the type, try MIME type detection
    if language is None and category == FileCategory.UNKNOWN and use_content_detection:
        mime_type = get_mime_type(file_path)
        
        if mime_type.startswith("text/"):
            category = FileCategory.DOCUMENTATION
            language = mime_type.split('/')[-1].capitalize()
            detection_method = "mime_type"
        elif mime_type.startswith("image/"):
            category = FileCategory.IMAGE
            language = mime_type.split('/')[-1].upper()
            detection_method = "mime_type"
        elif mime_type.startswith("application/"):
            subtype = mime_type.split('/')[-1]
            if subtype in ["zip", "x-tar", "x-gzip", "x-bzip2"]:
                category = FileCategory.ARCHIVE
                language = subtype.upper()
                detection_method = "mime_type"
            else:
                category = FileCategory.BINARY
                language = subtype.capitalize()
                detection_method = "mime_type"
    
    # Default values if all detection methods fail
    if language is None:
        language = "Unknown"
    
    return language, category, detection_method


def analyze_file_types(directory_path: Path, ignore_patterns: List[str] = None) -> Dict[str, Dict[str, int]]:
    """Analyze file types in a directory.
    
    Args:
        directory_path: Path to the directory to analyze
        ignore_patterns: Optional list of patterns to ignore
        
    Returns:
        Dictionary mapping file categories to counts of file types
        
    Raises:
        DirectoryAccessError: If the directory cannot be accessed
    """
    from dep_scanner.scanner import scan_directory
    from dep_scanner.exceptions import DirectoryAccessError
    
    if not directory_path.exists():
        raise DirectoryAccessError(directory_path, f"Directory does not exist: {directory_path}")
    
    if not directory_path.is_dir():
        raise DirectoryAccessError(directory_path, f"Not a directory: {directory_path}")
    
    if not os.access(directory_path, os.R_OK):
        raise DirectoryAccessError(directory_path, f"Permission denied: {directory_path}")
    
    result: Dict[str, Dict[str, int]] = {}
    
    for category in FileCategory:
        result[category.value] = {}
    
    try:
        for file_path in scan_directory(str(directory_path), ignore_patterns):
            try:
                file_type, category, _ = detect_file_type(file_path)
                
                if file_type:
                    category_dict = result[category.value]
                    category_dict[file_type] = category_dict.get(file_type, 0) + 1
            except Exception as e:
                logging.warning(f"Error detecting file type for {file_path}: {e}")
    except Exception as e:
        logging.error(f"Error scanning directory for file types: {e}")
        raise DirectoryAccessError(directory_path, f"Error scanning directory: {str(e)}")
    
    # Remove empty categories
    result = {k: v for k, v in result.items() if v}
    
    return result
