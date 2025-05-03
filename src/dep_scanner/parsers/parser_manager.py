"""Manager for dependency file parsers."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency

# Import all parsers to register them
# These imports are needed to register parsers with the ParserRegistry
# even though they're not directly used in this file
import dep_scanner.parsers.requirements_txt  # noqa: F401
import dep_scanner.parsers.pyproject_toml  # noqa: F401
import dep_scanner.parsers.build_sbt  # noqa: F401
import dep_scanner.parsers.pip_dependencies  # noqa: F401
import dep_scanner.parsers.conda_environment  # noqa: F401
import dep_scanner.parsers.maven_pom  # noqa: F401
import dep_scanner.parsers.gradle_build  # noqa: F401

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
        
    def extract_pip_dependencies(self, project_path: Path = None) -> List[Dependency]:
        """Extract dependencies from pip's internal database.
        
        Args:
            project_path: Path to the project directory (optional)
            
        Returns:
            List of dependencies found in pip database
            
        Raises:
            ParsingError: If the pip database cannot be parsed
        """
        pip_parser = self.parsers.get("pip_dependencies")
        if not pip_parser:
            logging.warning("Pip dependency parser not found")
            return []
        
        try:
            # Use an empty path as the pip parser doesn't need a specific file
            return pip_parser.parse(project_path or Path("."))
        except Exception as e:
            logging.warning(f"Error extracting pip dependencies: {e}")
            return []
    
    def extract_venv_dependencies(self, venv_path: Path) -> List[Dependency]:
        """Extract dependencies from a virtual environment.
        
        Args:
            venv_path: Path to the virtual environment
            
        Returns:
            List of dependencies found in the virtual environment
            
        Raises:
            ParsingError: If the virtual environment cannot be parsed
        """
        try:
            # Get the pip dependency parser
            parser = self.parsers.get("pip_dependencies")
            if not parser:
                raise ParsingError(venv_path, "Pip dependency parser not found")
            
            # Extract dependencies from the virtual environment
            return parser.parse_venv(venv_path)
        except Exception as e:
            # Re-raise ParsingError as is, wrap other exceptions
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(venv_path, f"Error extracting virtual environment dependencies: {str(e)}")
    
    def extract_conda_environment(self, env_file_path: Path) -> List[Dependency]:
        """Extract dependencies from a conda environment file.
        
        Args:
            env_file_path: Path to the conda environment file
            
        Returns:
            List of dependencies found in the conda environment file
            
        Raises:
            ParsingError: If the conda environment file cannot be parsed
        """
        try:
            # Get the conda environment parser
            parser = self.parsers.get("conda_environment")
            if not parser:
                raise ParsingError(env_file_path, "Conda environment parser not found")
            
            # Extract dependencies from the conda environment file
            return parser.parse(env_file_path)
        except Exception as e:
            # Re-raise ParsingError as is, wrap other exceptions
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(env_file_path, f"Error extracting conda environment dependencies: {str(e)}")
