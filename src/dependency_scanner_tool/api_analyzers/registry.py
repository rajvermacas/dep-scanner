"""Registry for API call analyzers."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiCallAnalyzer


class ApiCallAnalyzerRegistry:
    """Registry for API call analyzers."""

    def __init__(self):
        self._analyzers: Dict[str, Type[ApiCallAnalyzer]] = {}
        self._fallback_analyzer: Optional[Type[ApiCallAnalyzer]] = None

    def register(self, analyzer_class: Type[ApiCallAnalyzer], is_fallback: bool = False) -> None:
        """Register an API call analyzer.

        Args:
            analyzer_class: Class of the analyzer to register
            is_fallback: If True, this analyzer will be used as a fallback for all file types
        """
        if is_fallback:
            self._fallback_analyzer = analyzer_class
        else:
            # Register the analyzer for each supported extension
            for ext in analyzer_class.supported_extensions:
                self._analyzers[ext] = analyzer_class

    def get_analyzer_for_file(self, file_path: Path) -> Optional[ApiCallAnalyzer]:
        """Get the appropriate analyzer for a file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            An instance of the appropriate analyzer, or fallback analyzer if no specific match
        """
        ext = file_path.suffix.lower()
        analyzer_class = self._analyzers.get(ext)

        if analyzer_class:
            return analyzer_class()

        # Use fallback analyzer if available
        if self._fallback_analyzer:
            return self._fallback_analyzer()

        return None


class ApiCallAnalyzerManager:
    """Manager for API call analyzers."""
    
    def __init__(self):
        self.registry = ApiCallAnalyzerRegistry()
        self._register_default_analyzers()
    
    def _register_default_analyzers(self) -> None:
        """Register the default set of analyzers."""
        # Import analyzers here to avoid circular imports
        from dependency_scanner_tool.api_analyzers.python_api_analyzer import PythonApiCallAnalyzer
        from dependency_scanner_tool.api_analyzers.scala_api_analyzer import ScalaApiCallAnalyzer
        from dependency_scanner_tool.api_analyzers.generic_api_analyzer import GenericApiCallAnalyzer

        # Register language-specific analyzers (these take priority)
        self.registry.register(PythonApiCallAnalyzer)
        self.registry.register(ScalaApiCallAnalyzer)

        # Register generic analyzer as fallback for all other file types
        self.registry.register(GenericApiCallAnalyzer, is_fallback=True)
    
    def register_analyzer(self, analyzer_class: Type[ApiCallAnalyzer]) -> None:
        """Register an API call analyzer.
        
        Args:
            analyzer_class: Class of the analyzer to register
        """
        self.registry.register(analyzer_class)
    
    def analyze_file(self, file_path: Path) -> List[ApiCall]:
        """Analyze a file for API calls.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of API calls found in the file
        """
        analyzer = self.registry.get_analyzer_for_file(file_path)
        
        if analyzer and analyzer.can_analyze(file_path):
            try:
                return analyzer.analyze(file_path)
            except Exception as e:
                logging.warning(f"Error analyzing {file_path} for API calls: {str(e)}")
        
        return [] 