"""Parser for Python requirements.txt files."""

import logging
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency, DependencyType


class RequirementsTxtParser(DependencyParser):
    """Parser for Python requirements.txt files."""
    
    # Define supported file extensions and filenames
    supported_extensions: Set[str] = {".txt"}
    supported_filenames: Set[str] = {"requirements.txt", "requirements-dev.txt", "requirements-test.txt"}
    
    # Regular expression for package name (PEP 508)
    NAME_REGEX = re.compile(r'^([A-Za-z0-9][-A-Za-z0-9_.]+[A-Za-z0-9])')
    
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a requirements.txt file.
        
        Args:
            file_path: Path to the requirements.txt file
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        if not file_path.exists():
            raise ParsingError(file_path, f"File does not exist: {file_path}")
        
        dependencies = []
        line_number = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_number += 1
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Skip options (lines starting with -)
                    if line.startswith('-'):
                        continue
                    
                    # Skip editable installs
                    if line.startswith('-e') or line.startswith('--editable'):
                        continue
                    
                    # Handle line continuations
                    if line.endswith('\\'):
                        # For requirements with line continuations, we'll skip them entirely
                        # as they often contain hashes or other complex options
                        line = ''
                        continue
                        
                        # The following code is kept for reference but not used
                        # line = line[:-1]
                        # try:
                        #     next_line = next(f, '').strip()
                        #     line_number += 1
                        #     
                        #     # Skip hash lines and other options in continuations
                        #     if next_line.startswith('--hash=') or next_line.startswith('-'):
                        #         continue
                        #         
                        #     line += next_line
                        # except StopIteration:
                        #     break
                    
                    try:
                        name, version = self._parse_requirement(line)
                        if name:  # Only add if we got a valid name
                            dependencies.append(
                                Dependency(
                                    name=name,
                                    version=version,
                                    source_file=str(file_path),
                                    dependency_type=DependencyType.UNKNOWN
                                )
                            )
                    except ValueError as e:
                        logging.warning(f"Error parsing line {line_number} in {file_path}: {e}")
                        # Continue parsing other lines
        except Exception as e:
            raise ParsingError(file_path, f"Error parsing requirements.txt file: {str(e)}")
        
        return dependencies
    
    def _parse_requirement(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse a requirement line into name and version.
        
        Args:
            line: Requirement line to parse
            
        Returns:
            Tuple of (name, version)
            
        Raises:
            ValueError: If the line cannot be parsed
        """
        # Remove any comments
        line = line.split('#')[0].strip()
        
        # Skip empty lines
        if not line:
            return None, None
        
        # Handle environment markers (e.g., "package; python_version < '3.8'")
        if ';' in line:
            line = line.split(';')[0].strip()
        
        # Handle extras (e.g., "package[extra]")
        base_package = line
        if '[' in line and ']' in line:
            parts = line.split('[', 1)
            base_package = parts[0].strip()
            # Remove the extras for version extraction later
            line = base_package + parts[1].split(']', 1)[1]
        
        # Extract the package name
        name_match = self.NAME_REGEX.match(base_package)
        if not name_match:
            raise ValueError(f"Invalid requirement format: {line}")
        
        name = name_match.group(1)
        
        # Extract version constraints
        version = None
        version_part = line[len(name):].strip()
        
        if version_part:
            # Look for common version specifiers
            if '==' in version_part:
                version = version_part.split('==', 1)[0] + '==' + version_part.split('==', 1)[1].split(',')[0].strip()
            elif '>=' in version_part:
                version = version_part.split('>=', 1)[0] + '>=' + version_part.split('>=', 1)[1].split(',')[0].strip()
            elif '<=' in version_part:
                version = version_part.split('<=', 1)[0] + '<=' + version_part.split('<=', 1)[1].split(',')[0].strip()
            elif '>' in version_part:
                version = version_part.split('>', 1)[0] + '>' + version_part.split('>', 1)[1].split(',')[0].strip()
            elif '<' in version_part:
                version = version_part.split('<', 1)[0] + '<' + version_part.split('<', 1)[1].split(',')[0].strip()
            elif '~=' in version_part:
                version = version_part.split('~=', 1)[0] + '~=' + version_part.split('~=', 1)[1].split(',')[0].strip()
            elif '!=' in version_part:
                version = version_part.split('!=', 1)[0] + '!=' + version_part.split('!=', 1)[1].split(',')[0].strip()
        
        return name, version


# Register the parser
ParserRegistry.register("requirements_txt", RequirementsTxtParser)
