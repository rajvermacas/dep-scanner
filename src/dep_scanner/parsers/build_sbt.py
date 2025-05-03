"""Parser for Scala build.sbt files."""

import logging
import re
from pathlib import Path
from typing import List, Set

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency, DependencyType


class BuildSbtParser(DependencyParser):
    """Parser for Scala build.sbt files."""
    
    # Define supported file extensions and filenames
    supported_extensions: Set[str] = {".sbt"}
    supported_filenames: Set[str] = {"build.sbt"}
    
    # Regular expressions for dependency extraction
    # Match patterns like: "org.example" %% "library" % "1.0.0"
    # or "org.example" % "library" % "1.0.0"
    DEP_REGEX = re.compile(
        r'[\"\']([^\"\']+)[\"\'][\s\n]*%%?[\s\n]*[\"\']([^\"\']+)[\"\'][\s\n]*%[\s\n]*[\"\']([^\"\']+)[\"\']'
    )
    
    # Match libraryDependencies += ... pattern
    LIB_DEP_LINE_REGEX = re.compile(r'libraryDependencies\s*\+?=')
    
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a build.sbt file.
        
        Args:
            file_path: Path to the build.sbt file
            
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
                
                # Find all dependency declarations
                for match in self.DEP_REGEX.finditer(content):
                    organization, artifact, version = match.groups()
                    
                    # Create a dependency name in the format org:artifact
                    name = f"{organization}:{artifact}"
                    
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            source_file=str(file_path),
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
                
                # If we couldn't find any dependencies, check if this is actually a build.sbt file
                if not dependencies and not self._is_valid_build_sbt(content):
                    logging.warning(f"File {file_path} appears to be an invalid build.sbt file")
        
        except Exception as e:
            raise ParsingError(file_path, f"Error parsing build.sbt file: {str(e)}")
        
        return dependencies
    
    def _is_valid_build_sbt(self, content: str) -> bool:
        """Check if the content appears to be a valid build.sbt file.
        
        Args:
            content: File content to check
            
        Returns:
            True if the content appears to be a valid build.sbt file
        """
        # Check for common build.sbt patterns
        if "scalaVersion" in content:
            return True
        
        if "organization" in content:
            return True
        
        if "libraryDependencies" in content:
            return True
        
        if "sbt." in content:
            return True
        
        return False


# Register the parser
ParserRegistry.register("build_sbt", BuildSbtParser)
