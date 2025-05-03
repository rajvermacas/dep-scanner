"""Parser for conda environment files."""

import logging
from pathlib import Path
from typing import List, Optional, Set, Any

import yaml

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency, DependencyType


class CondaEnvironmentParser(DependencyParser):
    """Parser for conda environment.yml files.
    
    This parser extracts dependencies from conda environment files,
    which typically have the following structure:
    
    ```yaml
    name: myenv
    channels:
      - conda-forge
      - defaults
    dependencies:
      - python=3.9
      - numpy=1.21.0
      - pandas>=1.3.0
      - matplotlib
      - pip
      - pip:
        - requests>=2.25.0
        - flask
    ```
    """
    
    # Define supported file extensions and filenames
    supported_extensions: Set[str] = {".yml", ".yaml"}
    supported_filenames: Set[str] = {"environment.yml", "environment.yaml"}
    
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a conda environment file.
        
        Args:
            file_path: Path to the conda environment file
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        dependencies = []
        
        try:
            # Read the file content
            with open(file_path, "r") as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                return []
            
            # Parse YAML content
            try:
                env_data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ParsingError(file_path, f"Invalid YAML format: {str(e)}")
            
            # Check if the file has a dependencies section
            if not env_data or not isinstance(env_data, dict) or "dependencies" not in env_data:
                logging.warning(f"No dependencies found in {file_path}")
                return []
            
            # Extract dependencies
            deps_list = env_data["dependencies"]
            if not deps_list or not isinstance(deps_list, list):
                logging.warning(f"Dependencies section is empty or not a list in {file_path}")
                return []
            
            # Process conda dependencies
            for dep_item in deps_list:
                # Skip pip section (we'll handle it separately)
                if isinstance(dep_item, dict) and "pip" in dep_item:
                    continue
                
                # Skip the pip package itself
                if isinstance(dep_item, str) and dep_item == "pip":
                    dependencies.append(
                        Dependency(
                            name="pip",
                            version=None,
                            source_file=str(file_path),
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
                    continue
                
                # Process regular conda dependency
                if isinstance(dep_item, str):
                    name, version = self._parse_dependency_spec(dep_item)
                    if name:
                        dependencies.append(
                            Dependency(
                                name=name,
                                version=version,
                                source_file=str(file_path),
                                dependency_type=DependencyType.UNKNOWN
                            )
                        )
            
            # Process pip dependencies if present
            pip_deps = self._extract_pip_dependencies(deps_list, file_path)
            dependencies.extend(pip_deps)
            
            return dependencies
        
        except Exception as e:
            if not isinstance(e, ParsingError):
                raise ParsingError(file_path, f"Error parsing conda environment file: {str(e)}")
            raise
    
    def _parse_dependency_spec(self, spec: str) -> tuple[str, Optional[str]]:
        """Parse a conda dependency specification.
        
        Args:
            spec: Dependency specification (e.g., "numpy=1.21.0", "pandas>=1.3.0")
            
        Returns:
            Tuple of (name, version)
        """
        # Handle empty or invalid specs
        if not spec or not isinstance(spec, str):
            return "", None
        
        # Split by version operators
        for operator in ["==", ">=", "<=", ">", "<", "~="]:
            if operator in spec:
                parts = spec.split(operator, 1)
                return parts[0].strip(), f"{operator}{parts[1].strip()}"
        
        # Handle the simple equals operator (=) separately
        if "=" in spec:
            parts = spec.split("=", 1)
            return parts[0].strip(), parts[1].strip()
        
        # No version specified
        return spec.strip(), None
    
    def _extract_pip_dependencies(self, deps_list: List[Any], file_path: Path) -> List[Dependency]:
        """Extract pip dependencies from the conda environment file.
        
        Args:
            deps_list: List of dependencies from the conda environment file
            file_path: Path to the conda environment file
            
        Returns:
            List of pip dependencies
        """
        pip_deps = []
        
        # Find the pip section
        for item in deps_list:
            if isinstance(item, dict) and "pip" in item:
                pip_items = item.get("pip", [])
                if not isinstance(pip_items, list):
                    logging.warning(f"Pip section is not a list in {file_path}")
                    continue
                
                # Process each pip dependency
                for pip_dep in pip_items:
                    if isinstance(pip_dep, str):
                        name, version = self._parse_dependency_spec(pip_dep)
                        if name:
                            pip_deps.append(
                                Dependency(
                                    name=name,
                                    version=version,
                                    source_file=str(file_path),
                                    dependency_type=DependencyType.UNKNOWN
                                )
                            )
        
        return pip_deps

# Register the parser
ParserRegistry.register("conda_environment", CondaEnvironmentParser)
