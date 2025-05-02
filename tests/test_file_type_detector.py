"""Test cases for file_type_detector.py functionality."""
import os
import tempfile
from pathlib import Path

import pytest

from dep_scanner.exceptions import FileAccessError
from dep_scanner.file_type_detector import (
    FileCategory,
    detect_file_type,
    detect_language_from_content,
    detect_shebang,
    read_file_with_encoding,
    analyze_file_types,
)


def test_read_file_with_encoding():
    """Test reading files with different encodings."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("Hello, world!")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Test reading a text file
        content, encoding = read_file_with_encoding(tmp_path)
        assert content == "Hello, world!"
        assert encoding in ('utf-8', 'latin-1', 'ascii')
        
        # Test with non-existent file
        with pytest.raises(FileAccessError):
            read_file_with_encoding(Path("/nonexistent/file.txt"))
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_detect_shebang():
    """Test shebang detection."""
    # Python shebang
    assert detect_shebang("#!/usr/bin/env python\nimport sys") == "Python"
    assert detect_shebang("#!/usr/bin/python\nimport sys") == "Python"
    
    # Bash shebang
    assert detect_shebang("#!/bin/bash\necho 'Hello'") == "Bash"
    
    # No shebang
    assert detect_shebang("import sys\nprint('Hello')") is None
    assert detect_shebang("") is None
    assert detect_shebang(None) is None


def test_detect_language_from_content():
    """Test language detection from content patterns."""
    # Python content
    python_content = """
import sys
from os import path

def hello():
    print('Hello, world!')

class MyClass:
    def __init__(self):
        pass
"""
    assert detect_language_from_content(python_content) == "Python"
    
    # JavaScript content
    js_content = """
import React from 'react';
const hello = 'world';
let x = 5;
var y = 10;

function doSomething() {
    return x + y;
}
"""
    assert detect_language_from_content(js_content) == "JavaScript"
    
    # Java content
    java_content = """
package com.example;

import java.util.List;
import java.util.ArrayList;

public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, world!");
    }
}
"""
    assert detect_language_from_content(java_content) == "Java"
    
    # Empty content
    assert detect_language_from_content("") is None
    assert detect_language_from_content(None) is None


def test_detect_file_type():
    """Test file type detection."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
        tmp_file.write("""#!/usr/bin/env python
import sys

def hello():
    print('Hello, world!')
""")
        py_path = Path(tmp_file.name)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("Hello, world!")
        txt_path = Path(tmp_file.name)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        tmp_file.write('{"hello": "world"}')
        json_path = Path(tmp_file.name)
    
    try:
        # Test Python file detection
        file_type, category, method = detect_file_type(py_path)
        assert file_type == "Python"
        assert category == FileCategory.SOURCE_CODE
        
        # Test text file detection
        file_type, category, method = detect_file_type(txt_path)
        assert category != FileCategory.SOURCE_CODE
        
        # Test JSON file detection
        file_type, category, method = detect_file_type(json_path)
        assert file_type == "JSON"
        assert category in (FileCategory.DATA, FileCategory.SOURCE_CODE)
        
        # Test with non-existent file (should not raise exception when use_content_detection=False)
        file_type, category, method = detect_file_type(Path("/nonexistent/file.py"), use_content_detection=False)
        assert file_type == "Python"  # Based on extension only
        assert category == FileCategory.SOURCE_CODE
    finally:
        # Clean up
        os.unlink(py_path)
        os.unlink(txt_path)
        os.unlink(json_path)


def test_analyze_file_types():
    """Test analyzing file types in a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / 'file1.py').write_text("""
import sys

def hello():
    print('Hello, world!')
""")
        (Path(tmpdir) / 'file2.js').write_text("""
const hello = 'world';
function greet() {
    console.log('Hello!');
}
""")
        (Path(tmpdir) / 'file3.txt').write_text("Hello, world!")
        (Path(tmpdir) / 'file4.json').write_text('{"hello": "world"}')
        
        # Create a subdirectory with more files
        subdir = Path(tmpdir) / 'subdir'
        subdir.mkdir()
        (subdir / 'file5.py').write_text("print('Hello from subdir')")
        
        # Analyze file types
        result = analyze_file_types(Path(tmpdir))
        
        # Verify results
        assert FileCategory.SOURCE_CODE.value in result
        assert "Python" in result[FileCategory.SOURCE_CODE.value]
        assert result[FileCategory.SOURCE_CODE.value]["Python"] == 2
        assert "JavaScript" in result[FileCategory.SOURCE_CODE.value]
        assert result[FileCategory.SOURCE_CODE.value]["JavaScript"] == 1
        
        # There should be at least one data file (JSON)
        data_files = result.get(FileCategory.DATA.value, {})
        documentation_files = result.get(FileCategory.DOCUMENTATION.value, {})
        assert "JSON" in data_files or "JSON" in documentation_files or "JSON" in result[FileCategory.SOURCE_CODE.value]


def test_file_type_detection_with_content():
    """Test file type detection with content analysis."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        # File with Python content but no extension
        tmp_file.write("""
import sys
from os import path

def hello():
    print('Hello, world!')
""")
        no_ext_path = Path(tmp_file.name)
    
    try:
        # Test detection with content analysis
        file_type, category, method = detect_file_type(no_ext_path, use_content_detection=True)
        assert file_type == "Python"
        assert category == FileCategory.SOURCE_CODE
        assert method == "content_pattern"
        
        # Test detection without content analysis
        file_type, category, method = detect_file_type(no_ext_path, use_content_detection=False)
        assert file_type == "Unknown"
        assert category == FileCategory.UNKNOWN
        assert method == "extension"
    finally:
        # Clean up
        os.unlink(no_ext_path)


def test_detect_file_type_with_shebang():
    """Test file type detection with shebang."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        # File with shebang but no extension
        tmp_file.write("""#!/usr/bin/env python
import sys
print('Hello, world!')
""")
        shebang_path = Path(tmp_file.name)
    
    try:
        # Test detection with content analysis
        file_type, category, method = detect_file_type(shebang_path, use_content_detection=True)
        assert file_type == "Python"
        assert category == FileCategory.SOURCE_CODE
        assert method == "content_pattern"
    finally:
        # Clean up
        os.unlink(shebang_path)
