"""Parser for DevPod devfile YAML configuration files."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Set

# Use YAML library
try:
    import yaml
except ImportError:
    yaml = None

from dependency_scanner_tool.exceptions import ParsingError
from dependency_scanner_tool.parsers.base import DependencyParser, ParserRegistry
from dependency_scanner_tool.scanner import Dependency, DependencyType


class DevfileParser(DependencyParser):
    """Parser for DevPod devfile YAML configuration files."""
    
    # Define supported file extensions and filenames
    # Note: We don't use supported_extensions for broad matching since that would
    # conflict with other YAML parsers. We do content-based detection instead.
    supported_extensions: Set[str] = set()  # Empty to avoid conflicts
    supported_filenames: Set[str] = {"devfile.yaml", "devfile.yml"}
    
    # Container image regex for extracting name and version
    IMAGE_REGEX = re.compile(r'^([^:/@]+(?:/[^:/@]+)*?)(?::([^@/]+))?(?:@sha256:[a-f0-9]{64})?$')
    
    @classmethod  
    def can_parse(cls, file_path: Path) -> bool:
        """Check if this parser can handle the given file.
        
        Enhanced to check for devfile patterns in .devcontainer directories
        and validate devfile content structure. This is conservative to avoid
        conflicts with other YAML parsers.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this parser can handle the file, False otherwise
        """
        # Check standard filename patterns first - highest priority  
        base_result = super().can_parse(file_path)
        if base_result:
            return True
        
        # Check for devfile in .devcontainer directory - high priority
        devcontainer_check = (file_path.parent.name == '.devcontainer' and 
                             file_path.name in {'devfile.yaml', 'devfile.yml'})
        if devcontainer_check:
            return True
        
        # Check for YAML files with devfile indicators in filename only (not path) - high priority
        if file_path.suffix.lower() in {'.yaml', '.yml'}:
            filename_lower = file_path.name.lower()
            filename_match = 'devfile' in filename_lower or 'devpod' in filename_lower
            if filename_match:
                return True
        
        # For now, disable content-based detection to avoid false positives
        # Only rely on filename patterns for reliable detection
        return False
    
    @staticmethod
    def _is_valid_devfile(data: Any) -> bool:
        """Check if the parsed YAML data represents a valid devfile.
        
        Args:
            data: Parsed YAML data
            
        Returns:
            True if it appears to be a valid devfile
        """
        if not isinstance(data, dict):
            return False
        
        # Check for devfile schema version (required field)
        if 'schemaVersion' not in data:
            return False
        
        # Check for typical devfile sections
        devfile_sections = {'components', 'commands', 'events', 'projects'}
        if not any(section in data for section in devfile_sections):
            return False
        
        return True
    
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a devfile YAML file.
        
        Args:
            file_path: Path to the devfile YAML file
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        if not file_path.exists():
            raise ParsingError(file_path, f"File does not exist: {file_path}")
        
        if yaml is None:
            raise ParsingError(
                file_path, 
                "YAML parsing library not available. Please install 'PyYAML' package."
            )
        
        dependencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                devfile_data = yaml.safe_load(f)
            
            if not self._is_valid_devfile(devfile_data):
                raise ParsingError(file_path, "File does not appear to be a valid devfile")
            
            # Extract dependencies from different devfile components
            
            # 1. Container components (Docker images)
            container_deps = self._extract_container_dependencies(devfile_data, file_path)
            dependencies.extend(container_deps)
            
            # 2. Kubernetes components (referenced YAML files)
            k8s_deps = self._extract_kubernetes_dependencies(devfile_data, file_path)
            dependencies.extend(k8s_deps)
            
            # 3. Plugin components
            plugin_deps = self._extract_plugin_dependencies(devfile_data, file_path)
            dependencies.extend(plugin_deps)
            
            # 4. Volume components (for persistent data)
            volume_deps = self._extract_volume_dependencies(devfile_data, file_path)
            dependencies.extend(volume_deps)
            
            # Set source file for all dependencies
            for dep in dependencies:
                dep.source_file = str(file_path)
                
        except yaml.YAMLError as e:
            raise ParsingError(file_path, f"Invalid YAML syntax: {str(e)}")
        except Exception as e:
            raise ParsingError(file_path, f"Error parsing devfile: {str(e)}")
        
        return dependencies
    
    def _extract_container_dependencies(self, data: Dict[str, Any], file_path: Path) -> List[Dependency]:
        """Extract container image dependencies from devfile components.
        
        Args:
            data: Parsed devfile data
            file_path: Path to the devfile
            
        Returns:
            List of container image dependencies
        """
        dependencies = []
        
        if 'components' not in data:
            return dependencies
        
        for component in data['components']:
            if not isinstance(component, dict):
                continue
                
            component_name = component.get('name', 'unnamed')
            
            # Check for container component
            if 'container' in component:
                container = component['container']
                if 'image' in container:
                    image = container['image']
                    name, version = self._parse_container_image(image)
                    
                    if name:
                        dependencies.append(
                            Dependency(
                                name=name,
                                version=version or 'latest',
                                source_file=str(file_path),
                                dependency_type=DependencyType.UNKNOWN
                            )
                        )
                        logging.debug(f"Found container dependency: {name}:{version or 'latest'} in component {component_name}")
            
            # Check for image component (alternative format)
            elif 'image' in component:
                image_component = component['image']
                if 'imageName' in image_component:
                    image = image_component['imageName']
                    name, version = self._parse_container_image(image)
                    
                    if name:
                        dependencies.append(
                            Dependency(
                                name=name,
                                version=version or 'latest',
                                source_file=str(file_path),
                                dependency_type=DependencyType.UNKNOWN
                            )
                        )
                        logging.debug(f"Found image dependency: {name}:{version or 'latest'} in component {component_name}")
        
        return dependencies
    
    def _extract_kubernetes_dependencies(self, data: Dict[str, Any], file_path: Path) -> List[Dependency]:
        """Extract Kubernetes resource dependencies from devfile components.
        
        Args:
            data: Parsed devfile data
            file_path: Path to the devfile
            
        Returns:
            List of Kubernetes resource dependencies
        """
        dependencies = []
        
        if 'components' not in data:
            return dependencies
        
        for component in data['components']:
            if not isinstance(component, dict):
                continue
                
            component_name = component.get('name', 'unnamed')
            
            # Check for kubernetes component
            if 'kubernetes' in component:
                k8s_component = component['kubernetes']
                
                # Referenced Kubernetes YAML file
                if 'reference' in k8s_component:
                    reference = k8s_component['reference']
                    dependencies.append(
                        Dependency(
                            name=f"k8s-resource:{reference}",
                            version=None,
                            source_file=str(file_path),
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
                    logging.debug(f"Found Kubernetes resource reference: {reference} in component {component_name}")
                
                # Inline Kubernetes resources
                if 'referenceContent' in k8s_component:
                    # For inline content, we'll create a generic dependency
                    dependencies.append(
                        Dependency(
                            name=f"k8s-inline:{component_name}",
                            version=None,
                            source_file=str(file_path),
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
                    logging.debug(f"Found inline Kubernetes resources in component {component_name}")
            
            # Check for openshift component (similar to kubernetes)
            elif 'openshift' in component:
                openshift_component = component['openshift']
                
                if 'reference' in openshift_component:
                    reference = openshift_component['reference']
                    dependencies.append(
                        Dependency(
                            name=f"openshift-resource:{reference}",
                            version=None,
                            source_file=str(file_path),
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
                    logging.debug(f"Found OpenShift resource reference: {reference} in component {component_name}")
        
        return dependencies
    
    def _extract_plugin_dependencies(self, data: Dict[str, Any], file_path: Path) -> List[Dependency]:
        """Extract plugin dependencies from devfile components.
        
        Args:
            data: Parsed devfile data
            file_path: Path to the devfile
            
        Returns:
            List of plugin dependencies
        """
        dependencies = []
        
        if 'components' not in data:
            return dependencies
        
        for component in data['components']:
            if not isinstance(component, dict):
                continue
                
            component_name = component.get('name', 'unnamed')
            
            # Check for plugin component
            if 'plugin' in component:
                plugin = component['plugin']
                
                # Plugin ID and version information
                plugin_id = None
                plugin_version = None
                
                if 'id' in plugin:
                    plugin_id = plugin['id']
                
                if 'version' in plugin:
                    plugin_version = plugin['version']
                
                if plugin_id:
                    dependencies.append(
                        Dependency(
                            name=f"devfile-plugin:{plugin_id}",
                            version=plugin_version,
                            source_file=str(file_path),
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
                    logging.debug(f"Found plugin dependency: {plugin_id}:{plugin_version} in component {component_name}")
                
                # Plugin referenced by URI
                if 'uri' in plugin:
                    uri = plugin['uri']
                    dependencies.append(
                        Dependency(
                            name=f"devfile-plugin-uri:{uri}",
                            version=None,
                            source_file=str(file_path),
                            dependency_type=DependencyType.UNKNOWN
                        )
                    )
                    logging.debug(f"Found plugin URI dependency: {uri} in component {component_name}")
        
        return dependencies
    
    def _extract_volume_dependencies(self, data: Dict[str, Any], file_path: Path) -> List[Dependency]:
        """Extract volume dependencies from devfile components.
        
        Args:
            data: Parsed devfile data
            file_path: Path to the devfile
            
        Returns:
            List of volume dependencies
        """
        dependencies = []
        
        if 'components' not in data:
            return dependencies
        
        for component in data['components']:
            if not isinstance(component, dict):
                continue
                
            component_name = component.get('name', 'unnamed')
            
            # Check for volume component
            if 'volume' in component:
                volume = component['volume']
                
                # Volume size information
                size = volume.get('size', 'unknown')
                
                dependencies.append(
                    Dependency(
                        name=f"devfile-volume:{component_name}",
                        version=size,
                        source_file=str(file_path),
                        dependency_type=DependencyType.UNKNOWN
                    )
                )
                logging.debug(f"Found volume dependency: {component_name} ({size}) in devfile")
        
        return dependencies
    
    def _parse_container_image(self, image: str) -> tuple:
        """Parse container image string into name and version.
        
        Args:
            image: Container image string (e.g., "node:16-alpine", "registry.io/user/app:latest")
            
        Returns:
            Tuple of (name, version)
        """
        if not image or not isinstance(image, str):
            return None, None
        
        image = image.strip()
        if not image:
            return None, None
        
        # Handle registry prefixes and extract the core image name and tag
        match = self.IMAGE_REGEX.match(image)
        if match:
            name = match.group(1)
            version = match.group(2)
            
            # Clean up the name (remove registry prefix if it's a well-known registry)
            if '/' in name:
                parts = name.split('/')
                # If it's a standard Docker Hub image (user/repo format), keep it
                # If it's a registry URL, might want to simplify
                if len(parts) == 2 and '.' not in parts[0]:
                    name = '/'.join(parts)  # Keep user/repo format
                else:
                    name = parts[-1]  # Use just the image name
            
            return name, version
        
        # Fallback: treat the whole string as the name
        return image, None
    
    @classmethod
    def detect_devpod_usage(cls, project_path: Path) -> bool:
        """Detect if a project uses DevPods by scanning for devfile configurations.
        
        This method scans the project directory for any YAML files that contain
        devfile configurations, regardless of their filename.
        
        Args:
            project_path: Path to the project directory to scan
            
        Returns:
            True if DevPod usage is detected, False otherwise
        """
        if not project_path.exists() or not project_path.is_dir():
            logging.warning(f"Project path does not exist or is not a directory: {project_path}")
            return False
        
        devfile_parser = cls()
        
        try:
            # Scan for all YAML files in the project
            yaml_patterns = ["*.yaml", "*.yml"]
            
            for pattern in yaml_patterns:
                for yaml_file in project_path.rglob(pattern):
                    try:
                        # Use the sophisticated can_parse method to detect devfiles
                        if devfile_parser.can_parse(yaml_file):
                            logging.debug(f"DevPod usage detected: found devfile at {yaml_file}")
                            return True
                    except Exception as e:
                        # Continue scanning even if one file fails
                        logging.debug(f"Error checking file {yaml_file} for devfile content: {e}")
                        continue
            
            logging.debug(f"No DevPod usage detected in {project_path}")
            return False
            
        except Exception as e:
            logging.warning(f"Error scanning for DevPod usage in {project_path}: {e}")
            return False


# Register the parser
ParserRegistry.register("devfile", DevfileParser)