"""Infrastructure scanner manager for coordinating all infrastructure scanners."""

import fnmatch
import logging
from pathlib import Path
from typing import List, Set

from dependency_scanner_tool.infrastructure_scanners.base import (
    BaseInfrastructureScanner,
    InfrastructureScannerRegistry
)
from dependency_scanner_tool.infrastructure_scanners.terraform import TerraformScanner
from dependency_scanner_tool.infrastructure_scanners.docker import DockerScanner
from dependency_scanner_tool.infrastructure_scanners.kubernetes import KubernetesScanner
from dependency_scanner_tool.infrastructure_scanners.cloud_sdk import CloudSDKDetector
from dependency_scanner_tool.infrastructure_scanners.jenkins import JenkinsScanner
from dependency_scanner_tool.infrastructure_scanners.github_actions import GitHubActionsScanner
from dependency_scanner_tool.infrastructure_scanners.gitlab_ci import GitLabCIScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent


logger = logging.getLogger(__name__)


class InfrastructureScannerManager:
    """Manager for coordinating infrastructure scanners."""
    
    def __init__(self):
        self._registry = InfrastructureScannerRegistry()
        self._register_default_scanners()
    
    def _register_default_scanners(self):
        """Register default infrastructure scanners."""
        self._registry.register("terraform", TerraformScanner())
        self._registry.register("docker", DockerScanner())
        self._registry.register("kubernetes", KubernetesScanner())
        self._registry.register("cloud_sdk", CloudSDKDetector())
        self._registry.register("jenkins", JenkinsScanner())
        self._registry.register("github_actions", GitHubActionsScanner())
        self._registry.register("gitlab_ci", GitLabCIScanner())
    
    def get_registry(self) -> InfrastructureScannerRegistry:
        """Get the scanner registry."""
        return self._registry
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file using appropriate scanners."""
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []
        
        components = []
        scanners = self._registry.get_scanners_for_file(file_path)
        
        for scanner in scanners:
            try:
                scanner_components = scanner.scan_file(file_path)
                components.extend(scanner_components)
            except Exception as e:
                logger.error(f"Error scanning {file_path} with {scanner.__class__.__name__}: {e}")
        
        return components
    
    def scan_directory(
        self, 
        directory_path: Path, 
        ignore_patterns: List[str] = None
    ) -> List[InfrastructureComponent]:
        """Scan a directory recursively for infrastructure files."""
        if not directory_path.exists() or not directory_path.is_dir():
            logger.warning(f"Directory does not exist: {directory_path}")
            return []
        
        ignore_patterns = ignore_patterns or []
        components = []
        
        for file_path in self._scan_directory_recursive(directory_path, ignore_patterns):
            file_components = self.scan_file(file_path)
            components.extend(file_components)
        
        return components
    
    def _scan_directory_recursive(
        self, 
        directory_path: Path, 
        ignore_patterns: List[str]
    ) -> List[Path]:
        """Recursively find all supported files in directory."""
        files = []
        
        try:
            for item in directory_path.iterdir():
                # Check if item should be ignored
                if self._should_ignore(item, ignore_patterns):
                    continue
                
                if item.is_file():
                    # Check if any scanner can handle this file
                    if self._registry.get_scanners_for_file(item):
                        files.append(item)
                elif item.is_dir():
                    # Recurse into subdirectory
                    files.extend(self._scan_directory_recursive(item, ignore_patterns))
        
        except PermissionError:
            logger.warning(f"Permission denied accessing directory: {directory_path}")
        
        return files
    
    def _should_ignore(self, path: Path, ignore_patterns: List[str]) -> bool:
        """Check if a path should be ignored based on patterns."""
        path_str = str(path)
        name = path.name
        
        for pattern in ignore_patterns:
            # Check against full path
            if fnmatch.fnmatch(path_str, pattern):
                return True
            # Check against name only
            if fnmatch.fnmatch(name, pattern):
                return True
            # Check if path starts with pattern (for directories like .git)
            if path_str.endswith(pattern) or f"/{pattern}/" in path_str:
                return True
        
        return False
    
    def get_supported_extensions(self) -> Set[str]:
        """Get all supported file extensions/patterns."""
        extensions = set()
        
        for scanner in self._registry.get_all().values():
            patterns = scanner.get_supported_file_patterns()
            for pattern in patterns:
                if pattern.startswith("*."):
                    # Extract extension from pattern like "*.tf"
                    extensions.add(pattern[1:])  # Remove the *
                else:
                    # Add literal filename patterns like "Dockerfile"
                    extensions.add(pattern)
        
        return extensions
    
    def register_scanner(self, name: str, scanner: BaseInfrastructureScanner):
        """Register a custom scanner."""
        self._registry.register(name, scanner)
    
    def get_scanner(self, name: str) -> BaseInfrastructureScanner:
        """Get a scanner by name."""
        return self._registry.get(name)