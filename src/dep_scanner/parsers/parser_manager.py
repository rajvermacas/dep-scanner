"""Manager for dependency file parsers."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency

# Import all parsers to register them
from dep_scanner.parsers.requirements_txt import RequirementsTxtParser
from dep_scanner.parsers.pyproject_toml import PyprojectTomlParser


class ParserManager:
    """Manager for dependency file parsers."""
    
    def __init__(self):
        """Initialize the parser manager."""
        self.parsers: Dict[str, DependencyParser] = {}
        
        # Initialize all registered parsers
        for name, parser_class in ParserRegistry.get_all_parsers().items():
            self.parsers[name] = parser_class()
    
    def get_parser_for_file(self, file_path: Path) -> Optional[DependencyParser]:
        """Get a parser that can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Parser instance or None if no parser can handle the file
        """
        parser_class = ParserRegistry.find_parser_for_file(file_path)
        if parser_class:
            parser_name = next(
                name for name, cls in ParserRegistry.get_all_parsers().items() 
                if cls == parser_class
            )
            return self.parsers[parser_name]
        
        return None
    
    def parse_file(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a file.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        parser = self.get_parser_for_file(file_path)
        if not parser:
            raise ParsingError(file_path, f"No parser found for file: {file_path}")
        
        return parser.parse(file_path)
    
    def parse_files(self, file_paths: List[Path]) -> Dict[Path, List[Dependency]]:
        """Parse dependencies from multiple files.
        
        Args:
            file_paths: List of paths to files to parse
            
        Returns:
            Dictionary mapping file paths to lists of dependencies
        """
        results: Dict[Path, List[Dependency]] = {}
        errors: List[str] = []
        
        for file_path in file_paths:
            try:
                dependencies = self.parse_file(file_path)
                results[file_path] = dependencies
            except ParsingError as e:
                logging.warning(f"Error parsing file {file_path}: {e}")
                errors.append(str(e))
                results[file_path] = []
        
        if errors:
            logging.warning(f"Encountered {len(errors)} errors while parsing files")
        
        return results
    
    def get_supported_extensions(self) -> Set[str]:
        """Get all file extensions supported by registered parsers.
        
        Returns:
            Set of supported file extensions
        """
        extensions = set()
        for parser in self.parsers.values():
            extensions.update(parser.supported_extensions)
        
        return extensions
    
    def get_supported_filenames(self) -> Set[str]:
        """Get all filenames supported by registered parsers.
        
        Returns:
            Set of supported filenames
        """
        filenames = set()
        for parser in self.parsers.values():
            filenames.update(parser.supported_filenames)
        
        return filenames
