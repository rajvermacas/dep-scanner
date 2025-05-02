"""Base parser interface for dependency files."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from dep_scanner.scanner import Dependency


class DependencyParser(ABC):
    """Base class for all dependency file parsers."""
    
    # Class variable to store file extensions this parser can handle
    supported_extensions: Set[str] = set()
    
    # Class variable to store specific filenames this parser can handle
    supported_filenames: Set[str] = set()
    
    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Check if this parser can handle the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this parser can handle the file, False otherwise
        """
        # Check if the file extension is supported
        if file_path.suffix.lower() in cls.supported_extensions:
            return True
        
        # Check if the filename is supported
        if file_path.name in cls.supported_filenames:
            return True
        
        return False
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a file.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        pass


class ParserRegistry:
    """Registry for dependency file parsers."""
    
    _parsers: Dict[str, Type[DependencyParser]] = {}
    
    @classmethod
    def register(cls, parser_name: str, parser_class: Type[DependencyParser]) -> None:
        """Register a parser.
        
        Args:
            parser_name: Name of the parser
            parser_class: Parser class
        """
        cls._parsers[parser_name] = parser_class
        logging.debug(f"Registered parser: {parser_name}")
    
    @classmethod
    def get_parser(cls, parser_name: str) -> Optional[Type[DependencyParser]]:
        """Get a parser by name.
        
        Args:
            parser_name: Name of the parser
            
        Returns:
            Parser class or None if not found
        """
        return cls._parsers.get(parser_name)
    
    @classmethod
    def get_all_parsers(cls) -> Dict[str, Type[DependencyParser]]:
        """Get all registered parsers.
        
        Returns:
            Dictionary of parser names to parser classes
        """
        return cls._parsers.copy()
    
    @classmethod
    def find_parser_for_file(cls, file_path: Path) -> Optional[Type[DependencyParser]]:
        """Find a parser that can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Parser class or None if no parser can handle the file
        """
        for parser_class in cls._parsers.values():
            if parser_class.can_parse(file_path):
                return parser_class
        
        return None
