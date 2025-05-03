"""Tests for the Python import analyzer."""

import tempfile
from pathlib import Path
from unittest import TestCase

from dep_scanner.analyzers.python_analyzer import PythonImportAnalyzer


class TestPythonImportAnalyzer(TestCase):
    """Test cases for the Python import analyzer."""

    def setUp(self):
        """Set up the test environment."""
        self.analyzer = PythonImportAnalyzer()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()

    def test_can_analyze(self):
        """Test that the analyzer can identify Python files."""
        # Test with a Python file
        py_file = self.temp_path / "test.py"
        py_file.touch()
        self.assertTrue(self.analyzer.can_analyze(py_file))

        # Test with a non-Python file
        other_file = self.temp_path / "test.txt"
        other_file.touch()
        self.assertFalse(self.analyzer.can_analyze(other_file))

    def test_analyze_simple_imports(self):
        """Test analyzing simple import statements."""
        content = '''
        import os
        import sys
        import numpy
        import pandas as pd
        '''

        py_file = self.temp_path / "simple_imports.py"
        with open(py_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(py_file)
        
        # Should only include numpy and pandas, not stdlib modules
        self.assertEqual(len(dependencies), 2)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("numpy", dep_names)
        self.assertIn("pandas", dep_names)
        
        # Standard library modules should be excluded
        self.assertNotIn("os", dep_names)
        self.assertNotIn("sys", dep_names)

    def test_analyze_from_imports(self):
        """Test analyzing from-import statements."""
        content = '''
        from os import path
        from sys import argv
        from numpy import array
        from pandas import DataFrame
        from sklearn.model_selection import train_test_split
        '''

        py_file = self.temp_path / "from_imports.py"
        with open(py_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(py_file)
        
        # Should include numpy, pandas, and scikit-learn, not stdlib modules
        self.assertEqual(len(dependencies), 3)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("numpy", dep_names)
        self.assertIn("pandas", dep_names)
        self.assertIn("scikit-learn", dep_names)  # sklearn should map to scikit-learn
        
        # Standard library modules should be excluded
        self.assertNotIn("os", dep_names)
        self.assertNotIn("sys", dep_names)

    def test_analyze_complex_imports(self):
        """Test analyzing complex import patterns."""
        content = '''
        import os, sys, json
        import numpy as np, pandas as pd
        from matplotlib import pyplot as plt
        from tensorflow.keras import layers
        import torch.nn as nn
        from cv2 import resize
        '''

        py_file = self.temp_path / "complex_imports.py"
        with open(py_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(py_file)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("numpy", dep_names)
        self.assertIn("pandas", dep_names)
        self.assertIn("matplotlib", dep_names)
        self.assertIn("tensorflow", dep_names)
        self.assertIn("torch", dep_names)
        self.assertIn("opencv-python", dep_names)  # cv2 should map to opencv-python
        
        # Standard library modules should be excluded
        self.assertNotIn("os", dep_names)
        self.assertNotIn("sys", dep_names)
        self.assertNotIn("json", dep_names)

    def test_analyze_syntax_error(self):
        """Test analyzing a file with syntax errors."""
        content = '''
        import numpy
        import pandas
        
        # This line has a syntax error
        if True
            print("Missing colon")
        '''

        py_file = self.temp_path / "syntax_error.py"
        with open(py_file, "w") as f:
            f.write(content)

        # Should still extract imports using regex fallback
        dependencies = self.analyzer.analyze(py_file)
        
        # Check dependency names
        dep_names = {dep.name for dep in dependencies}
        self.assertIn("numpy", dep_names)
        self.assertIn("pandas", dep_names)

    def test_analyze_empty_file(self):
        """Test analyzing an empty file."""
        py_file = self.temp_path / "empty.py"
        py_file.touch()

        dependencies = self.analyzer.analyze(py_file)
        self.assertEqual(len(dependencies), 0)

    def test_analyze_no_imports(self):
        """Test analyzing a file with no imports."""
        content = '''
        # This file has no imports
        def hello():
            print("Hello, world!")
            
        if __name__ == "__main__":
            hello()
        '''

        py_file = self.temp_path / "no_imports.py"
        with open(py_file, "w") as f:
            f.write(content)

        dependencies = self.analyzer.analyze(py_file)
        self.assertEqual(len(dependencies), 0)
