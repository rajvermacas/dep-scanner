"""Base analyzer interface for source code import analysis."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from dep_scanner.scanner import Dependency


class ImportAnalyzerRegistry:
    """Registry for import analyzers."""
    
    _analyzers: Dict[str, Type["ImportAnalyzer"]] = {}
    
    @classmethod
    def register(cls, analyzer_name: str, analyzer_class: Type["ImportAnalyzer"]) -> None:
        """Register an analyzer.
        
        Args:
            analyzer_name: Name of the analyzer
            analyzer_class: Analyzer class
        """
        cls._analyzers[analyzer_name] = analyzer_class
        logging.debug(f"Registered import analyzer: {analyzer_name}")
    
    @classmethod
    def get_analyzer(cls, analyzer_name: str) -> Optional[Type["ImportAnalyzer"]]:
        """Get an analyzer by name.
        
        Args:
            analyzer_name: Name of the analyzer
            
        Returns:
            Analyzer class or None if not found
        """
        return cls._analyzers.get(analyzer_name)
    
    @classmethod
    def get_all_analyzers(cls) -> Dict[str, Type["ImportAnalyzer"]]:
        """Get all registered analyzers.
        
        Returns:
            Dictionary of analyzer names to analyzer classes
        """
        return cls._analyzers.copy()
    
    @classmethod
    def find_analyzer_for_file(cls, file_path: Path) -> Optional[Type["ImportAnalyzer"]]:
        """Find an analyzer that can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Analyzer class or None if no analyzer can handle the file
        """
        for analyzer_class in cls._analyzers.values():
            if analyzer_class.can_analyze(file_path):
                return analyzer_class
        
        return None


class ImportAnalyzer(ABC):
    """Base class for source code import analysis."""
    
    # Class variable to store file extensions this analyzer can handle
    supported_extensions: Set[str] = set()
    
    @classmethod
    def can_analyze(cls, file_path: Path) -> bool:
        """Check if this analyzer can handle the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this analyzer can handle the file, False otherwise
        """
        # Check if the file extension is supported
        return file_path.suffix.lower() in cls.supported_extensions
    
    @abstractmethod
    def analyze(self, file_path: Path) -> List[Dependency]:
        """Analyze source file for import statements.
        
        Args:
            file_path: Path to the source file
            
        Returns:
            List of detected dependencies from imports
        """
        pass
