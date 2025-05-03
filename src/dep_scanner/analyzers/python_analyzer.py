"""Analyzer for Python import statements."""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Set

from dep_scanner.analyzers.base import ImportAnalyzer, ImportAnalyzerRegistry
from dep_scanner.exceptions import ParsingError
from dep_scanner.scanner import Dependency, DependencyType


class PythonImportAnalyzer(ImportAnalyzer):
    """Analyzer for Python import statements."""
    
    # Define supported file extensions
    supported_extensions: Set[str] = {".py"}
    
    # Standard library modules (common ones, not exhaustive)
    STDLIB_MODULES = {
        "abc", "argparse", "asyncio", "collections", "concurrent", "contextlib",
        "copy", "csv", "datetime", "decimal", "email", "enum", "functools",
        "glob", "gzip", "hashlib", "http", "importlib", "inspect", "io", "itertools",
        "json", "logging", "math", "multiprocessing", "os", "pathlib", "pickle",
        "platform", "queue", "random", "re", "shutil", "signal", "socket",
        "sqlite3", "statistics", "string", "subprocess", "sys", "tempfile",
        "threading", "time", "typing", "unittest", "urllib", "uuid", "warnings",
        "xml", "zipfile"
    }
    
    # Mapping of common package imports to their PyPI package names
    PACKAGE_MAPPING: Dict[str, str] = {
        "numpy": "numpy",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "sklearn": "scikit-learn",
        "tensorflow": "tensorflow",
        "torch": "torch",
        "requests": "requests",
        "flask": "flask",
        "django": "django",
        "sqlalchemy": "sqlalchemy",
        "pytest": "pytest",
        "bs4": "beautifulsoup4",
        "PIL": "pillow",
        "cv2": "opencv-python",
        "yaml": "pyyaml",
        "pydantic": "pydantic",
        "fastapi": "fastapi",
        "boto3": "boto3",
        "click": "click",
        "tqdm": "tqdm",
    }
    
    def analyze(self, file_path: Path) -> List[Dependency]:
        """Analyze Python file for import statements.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        if not file_path.exists():
            raise ParsingError(file_path, f"File does not exist: {file_path}")
        
        dependencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Try to normalize indentation to fix common syntax errors in test files
                normalized_content = self._normalize_indentation(content)
                
                # Parse the Python file
                try:
                    tree = ast.parse(normalized_content)
                    
                    # Extract imports using AST
                    imports = self._extract_imports_from_ast(tree)
                except SyntaxError as e:
                    logging.warning(f"Syntax error in {file_path}: {e}")
                    
                    # Fall back to regex-based extraction for files with syntax errors
                    imports = self._extract_imports_with_regex(content)
                
                # Convert imports to dependencies
                for module_name in imports:
                    # Skip standard library modules
                    if module_name in self.STDLIB_MODULES:
                        continue
                        
                    # Get the top-level package name
                    top_level_package = module_name.split('.')[0]
                    
                    # Map to PyPI package name if known
                    package_name = self.PACKAGE_MAPPING.get(top_level_package, top_level_package)
                    
                    dependencies.append(
                        Dependency(
                            name=package_name,
                            version=None,  # We can't determine version from imports
                            source_file=str(file_path),
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
        except Exception as e:
            raise ParsingError(file_path, f"Error analyzing Python imports: {str(e)}")
        
        # Remove duplicates while preserving order
        unique_dependencies = []
        seen_names = set()
        
        for dep in dependencies:
            if dep.name not in seen_names:
                seen_names.add(dep.name)
                unique_dependencies.append(dep)
        
        return unique_dependencies
    
    def _extract_imports_from_ast(self, tree: ast.Module) -> Set[str]:
        """Extract import statements from an AST.
        
        Args:
            tree: AST of the Python file
            
        Returns:
            Set of imported module names
        """
        imports = set()
        
        for node in ast.walk(tree):
            # Handle 'import x' and 'import x as y'
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name)
            
            # Handle 'from x import y' and 'from x import y as z'
            elif isinstance(node, ast.ImportFrom):
                if node.module:  # Handles 'from x import y'
                    imports.add(node.module)
        
        return imports
    
    def _extract_imports_with_regex(self, content: str) -> Set[str]:
        """Extract import statements using regex (fallback method).
        
        Args:
            content: Content of the Python file
            
        Returns:
            Set of imported module names
        """
        imports = set()
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Process line by line to handle imports more reliably
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            # Match 'import x' and 'import x as y'
            if line.startswith('import '):
                # Extract everything after 'import '
                import_part = line[7:].strip()
                
                # Handle multiple imports on one line (import x, y, z)
                modules = import_part.split(',')
                for module in modules:
                    module = module.strip()
                    
                    # Remove 'as y' if present
                    if ' as ' in module:
                        module_name = module.split(' as ')[0].strip()
                    else:
                        module_name = module
                    
                    # Handle potential nested modules (e.g., torch.nn)
                    base_module = module_name.split('.')[0].strip()
                    if base_module:
                        imports.add(base_module)
            
            # Match 'from x import y'
            elif line.startswith('from '):
                # Extract the module part between 'from ' and ' import'
                parts = line.split(' import ')
                if len(parts) >= 2:
                    module_part = parts[0][5:].strip()  # Remove 'from ' prefix
                    if module_part:
                        # For nested imports, we only care about the top-level package
                        base_module = module_part.split('.')[0].strip()
                        imports.add(base_module)
        
        return imports


    def _normalize_indentation(self, content: str) -> str:
        """Attempt to normalize indentation to fix common syntax errors.
        
        Args:
            content: Original file content
            
        Returns:
            Normalized content with consistent indentation
        """
        # Split into lines and remove leading/trailing whitespace
        lines = content.splitlines()
        
        # Remove any leading blank lines
        while lines and not lines[0].strip():
            lines.pop(0)
            
        if not lines:
            return ""
            
        # Find the minimum indentation of non-empty lines
        min_indent = float('inf')
        for line in lines:
            if line.strip():  # Skip empty lines
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
                
        if min_indent == float('inf'):
            min_indent = 0
            
        # Remove common indentation from all lines
        normalized_lines = []
        for line in lines:
            if not line.strip():  # Keep empty lines as is
                normalized_lines.append("")
            else:
                # Remove the common indentation
                normalized_lines.append(line[min_indent:] if len(line) >= min_indent else line)
                
        return "\n".join(normalized_lines)


# Register the analyzer
ImportAnalyzerRegistry.register("python", PythonImportAnalyzer)
