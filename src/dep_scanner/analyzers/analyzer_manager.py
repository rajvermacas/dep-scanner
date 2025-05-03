"""Manager for source code import analyzers."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from dep_scanner.analyzers.base import ImportAnalyzer, ImportAnalyzerRegistry
from dep_scanner.exceptions import ParsingError
from dep_scanner.scanner import Dependency

# Import all analyzers to register them
# These imports are needed to register analyzers with the ImportAnalyzerRegistry
# even though they're not directly used in this file
import dep_scanner.analyzers.python_analyzer  # noqa: F401
import dep_scanner.analyzers.java_analyzer  # noqa: F401

class AnalyzerManager:
    """Manager for source code import analyzers."""
    
    def __init__(self):
        """Initialize the analyzer manager."""
        self.analyzers: Dict[str, ImportAnalyzer] = {}
        
        # Initialize all registered analyzers
        for name, analyzer_class in ImportAnalyzerRegistry.get_all_analyzers().items():
            self.analyzers[name] = analyzer_class()
    
    def get_analyzer_for_file(self, file_path: Path) -> Optional[ImportAnalyzer]:
        """Get an analyzer that can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Analyzer instance or None if no analyzer can handle the file
        """
        analyzer_class = ImportAnalyzerRegistry.find_analyzer_for_file(file_path)
        if analyzer_class:
            analyzer_name = next(
                name for name, cls in ImportAnalyzerRegistry.get_all_analyzers().items() 
                if cls == analyzer_class
            )
            return self.analyzers[analyzer_name]
        
        return None
    
    def analyze_file(self, file_path: Path) -> List[Dependency]:
        """Analyze imports from a file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be analyzed
        """
        analyzer = self.get_analyzer_for_file(file_path)
        if not analyzer:
            raise ParsingError(file_path, f"No analyzer found for file: {file_path}")
        
        return analyzer.analyze(file_path)
    
    def analyze_files(self, file_paths: List[Path]) -> Dict[Path, List[Dependency]]:
        """Analyze imports from multiple files.
        
        Args:
            file_paths: List of paths to files to analyze
            
        Returns:
            Dictionary mapping file paths to lists of dependencies
        """
        results: Dict[Path, List[Dependency]] = {}
        errors: List[str] = []
        
        for file_path in file_paths:
            try:
                dependencies = self.analyze_file(file_path)
                results[file_path] = dependencies
            except ParsingError as e:
                logging.warning(f"Error analyzing file {file_path}: {e}")
                errors.append(str(e))
                results[file_path] = []
        
        if errors:
            logging.warning(f"Encountered {len(errors)} errors while analyzing files")
        
        return results
    
    def get_supported_extensions(self) -> Set[str]:
        """Get all file extensions supported by registered analyzers.
        
        Returns:
            Set of supported file extensions
        """
        extensions = set()
        for analyzer in self.analyzers.values():
            extensions.update(analyzer.supported_extensions)
        
        return extensions
