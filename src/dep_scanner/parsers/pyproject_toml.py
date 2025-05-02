"""Parser for Python pyproject.toml files."""

from pathlib import Path
from typing import Any, Dict, List, Set

# Use tomli for Python < 3.11, or tomllib for Python >= 3.11
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        # If tomli is not available, we'll handle this gracefully
        tomllib = None

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency, DependencyType


class PyprojectTomlParser(DependencyParser):
    """Parser for Python pyproject.toml files."""
    
    # Define supported file extensions and filenames
    supported_extensions: Set[str] = {".toml"}
    supported_filenames: Set[str] = {"pyproject.toml"}
    
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a pyproject.toml file.
        
        Args:
            file_path: Path to the pyproject.toml file
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        if not file_path.exists():
            raise ParsingError(file_path, f"File does not exist: {file_path}")
        
        if tomllib is None:
            raise ParsingError(
                file_path, 
                "TOML parsing library not available. Please install 'tomli' package for Python < 3.11."
            )
        
        dependencies = []
        
        try:
            with open(file_path, 'rb') as f:
                pyproject_data = tomllib.load(f)
            
            # Extract dependencies from different possible locations in pyproject.toml
            
            # 1. Poetry dependencies
            poetry_deps = self._extract_poetry_dependencies(pyproject_data)
            dependencies.extend(poetry_deps)
            
            # 2. PEP 621 dependencies (project.dependencies)
            pep621_deps = self._extract_pep621_dependencies(pyproject_data)
            dependencies.extend(pep621_deps)
            
            # 3. Setuptools dependencies (build-system.requires)
            setuptools_deps = self._extract_setuptools_dependencies(pyproject_data)
            dependencies.extend(setuptools_deps)
            
            # 4. Flit dependencies
            flit_deps = self._extract_flit_dependencies(pyproject_data)
            dependencies.extend(flit_deps)
            
            # Set source file for all dependencies
            for dep in dependencies:
                dep.source_file = str(file_path)
            
        except Exception as e:
            raise ParsingError(file_path, f"Error parsing pyproject.toml file: {str(e)}")
        
        return dependencies
    
    def _extract_poetry_dependencies(self, data: Dict[str, Any]) -> List[Dependency]:
        """Extract dependencies from Poetry section.
        
        Args:
            data: Parsed pyproject.toml data
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        # Check for poetry section
        if 'tool' in data and 'poetry' in data['tool']:
            poetry_data = data['tool']['poetry']
            
            # Main dependencies
            if 'dependencies' in poetry_data:
                for name, spec in poetry_data['dependencies'].items():
                    # Skip python dependency
                    if name.lower() == 'python':
                        continue
                    
                    version = self._parse_poetry_dependency_spec(spec)
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
            
            # Dev dependencies
            if 'dev-dependencies' in poetry_data:
                for name, spec in poetry_data['dev-dependencies'].items():
                    version = self._parse_poetry_dependency_spec(spec)
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
            
            # Group dependencies (Poetry >= 1.2.0)
            if 'group' in poetry_data:
                for group_name, group_data in poetry_data['group'].items():
                    if 'dependencies' in group_data:
                        for name, spec in group_data['dependencies'].items():
                            version = self._parse_poetry_dependency_spec(spec)
                            dependencies.append(
                                Dependency(
                                    name=name,
                                    version=version,
                                    dependency_type=DependencyType.UNKNOWN
                                )
                            )
        
        return dependencies
    
    def _parse_poetry_dependency_spec(self, spec: Any) -> str:
        """Parse Poetry dependency specification.
        
        Args:
            spec: Poetry dependency specification
            
        Returns:
            Version string
        """
        if isinstance(spec, str):
            return spec
        elif isinstance(spec, dict):
            if 'version' in spec:
                return spec['version']
        
        return None
    
    def _extract_pep621_dependencies(self, data: Dict[str, Any]) -> List[Dependency]:
        """Extract dependencies from PEP 621 section.
        
        Args:
            data: Parsed pyproject.toml data
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        # Check for project section (PEP 621)
        if 'project' in data:
            project_data = data['project']
            
            # Main dependencies
            if 'dependencies' in project_data:
                for dep_spec in project_data['dependencies']:
                    name, version = self._parse_pep621_dependency_spec(dep_spec)
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
            
            # Optional dependencies
            if 'optional-dependencies' in project_data:
                for group_name, deps in project_data['optional-dependencies'].items():
                    for dep_spec in deps:
                        name, version = self._parse_pep621_dependency_spec(dep_spec)
                        dependencies.append(
                            Dependency(
                                name=name,
                                version=version,
                                dependency_type=DependencyType.UNKNOWN
                            )
                        )
        
        return dependencies
    
    def _parse_pep621_dependency_spec(self, spec: str) -> tuple:
        """Parse PEP 621 dependency specification.
        
        Args:
            spec: PEP 621 dependency specification
            
        Returns:
            Tuple of (name, version)
        """
        # Handle extras and environment markers
        spec = spec.split(';')[0].strip()  # Remove environment markers
        
        if '[' in spec:
            spec = spec.split('[')[0].strip()  # Remove extras
        
        # Parse name and version
        if '>=' in spec:
            parts = spec.split('>=')
            return parts[0].strip(), f">={parts[1].strip()}"
        elif '==' in spec:
            parts = spec.split('==')
            return parts[0].strip(), f"=={parts[1].strip()}"
        elif '<=' in spec:
            parts = spec.split('<=')
            return parts[0].strip(), f"<={parts[1].strip()}"
        elif '>' in spec:
            parts = spec.split('>')
            return parts[0].strip(), f">{parts[1].strip()}"
        elif '<' in spec:
            parts = spec.split('<')
            return parts[0].strip(), f"<{parts[1].strip()}"
        elif '~=' in spec:
            parts = spec.split('~=')
            return parts[0].strip(), f"~={parts[1].strip()}"
        else:
            return spec.strip(), None
    
    def _extract_setuptools_dependencies(self, data: Dict[str, Any]) -> List[Dependency]:
        """Extract dependencies from setuptools section.
        
        Args:
            data: Parsed pyproject.toml data
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        # Check for build-system section
        if 'build-system' in data and 'requires' in data['build-system']:
            for dep_spec in data['build-system']['requires']:
                name, version = self._parse_pep621_dependency_spec(dep_spec)
                dependencies.append(
                    Dependency(
                        name=name,
                        version=version,
                        dependency_type=DependencyType.UNKNOWN
                    )
                )
        
        return dependencies
    
    def _extract_flit_dependencies(self, data: Dict[str, Any]) -> List[Dependency]:
        """Extract dependencies from Flit section.
        
        Args:
            data: Parsed pyproject.toml data
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        # Check for flit section
        if 'tool' in data and 'flit' in data['tool']:
            flit_data = data['tool']['flit']
            
            # Main dependencies
            if 'metadata' in flit_data and 'requires' in flit_data['metadata']:
                for dep_spec in flit_data['metadata']['requires']:
                    name, version = self._parse_pep621_dependency_spec(dep_spec)
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
            
            # Dev dependencies
            if 'metadata' in flit_data and 'requires-dev' in flit_data['metadata']:
                for dep_spec in flit_data['metadata']['requires-dev']:
                    name, version = self._parse_pep621_dependency_spec(dep_spec)
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
        
        return dependencies


# Register the parser
ParserRegistry.register("pyproject_toml", PyprojectTomlParser)
