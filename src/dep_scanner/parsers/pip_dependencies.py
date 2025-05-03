"""Parser for Python pip dependencies."""

import json
import logging
import subprocess
from pathlib import Path
from typing import List, Set

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency, DependencyType


class PipDependencyParser(DependencyParser):
    """Parser for Python pip dependencies.
    
    This parser extracts installed packages from pip's internal database.
    It can work in two modes:
    1. Global mode: Extracts all packages installed in the current Python environment
    2. Virtual environment mode: Extracts packages from a specified virtual environment
    """
    
    # Define supported file extensions and filenames
    # Note: This parser doesn't parse files directly, but we need these for the registry
    supported_extensions: Set[str] = set()
    supported_filenames: Set[str] = set()
    
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from pip's internal database.
        
        Args:
            file_path: Path to the project directory (not used directly)
            
        Returns:
            List of dependencies found in the pip database
            
        Raises:
            ParsingError: If the pip database cannot be parsed
        """
        dependencies = []
        
        try:
            # Get installed packages using pip list in JSON format
            result = self._run_pip_list()
            
            # Parse the JSON output
            packages = json.loads(result)
            
            # Convert to dependencies
            for package in packages:
                name = package.get('name')
                version = package.get('version')
                
                if name:
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            source_file="pip_database",
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
        except Exception as e:
            raise ParsingError(file_path, f"Error parsing pip dependencies: {str(e)}")
        
        return dependencies
    
    def parse_venv(self, venv_path: Path) -> List[Dependency]:
        """Parse dependencies from a virtual environment.
        
        Args:
            venv_path: Path to the virtual environment
            
        Returns:
            List of dependencies found in the virtual environment
            
        Raises:
            ParsingError: If the virtual environment cannot be parsed
        """
        dependencies = []
        
        try:
            # Get installed packages using pip list in JSON format from the venv
            result = self._run_pip_list_in_venv(venv_path)
            
            # Parse the JSON output
            packages = json.loads(result)
            
            # Convert to dependencies
            for package in packages:
                name = package.get('name')
                version = package.get('version')
                
                if name:
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            source_file=f"venv:{venv_path}",
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
        except Exception as e:
            raise ParsingError(venv_path, f"Error parsing pip dependencies in virtual environment: {str(e)}")
        
        return dependencies
    
    def _run_pip_list(self) -> str:
        """Run pip list command and return the output.
        
        Returns:
            JSON string with installed packages
            
        Raises:
            RuntimeError: If pip list command fails
        """
        try:
            # Run pip list with JSON output format
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running pip list: {e}")
            logging.error(f"Stderr: {e.stderr}")
            raise RuntimeError(f"Failed to run pip list: {e.stderr}")
    
    def _run_pip_list_in_venv(self, venv_path: Path) -> str:
        """Run pip list command in a virtual environment and return the output.
        
        Args:
            venv_path: Path to the virtual environment
            
        Returns:
            JSON string with installed packages
            
        Raises:
            RuntimeError: If pip list command fails
        """
        # Determine the pip executable path in the virtual environment
        if Path(venv_path / "bin" / "pip").exists():
            # Unix-like systems
            pip_path = Path(venv_path / "bin" / "pip")
        elif Path(venv_path / "Scripts" / "pip.exe").exists():
            # Windows
            pip_path = Path(venv_path / "Scripts" / "pip.exe")
        else:
            raise RuntimeError(f"Could not find pip executable in virtual environment: {venv_path}")
        
        try:
            # Run pip list with JSON output format
            result = subprocess.run(
                [str(pip_path), "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running pip list in venv: {e}")
            logging.error(f"Stderr: {e.stderr}")
            raise RuntimeError(f"Failed to run pip list in venv: {e.stderr}")


# Register the parser
ParserRegistry.register("pip_dependencies", PipDependencyParser)
