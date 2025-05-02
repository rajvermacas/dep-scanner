"""Core scanner module for analyzing project dependencies."""

import fnmatch
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set


class DependencyType(Enum):
    """Classification of dependencies."""
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    UNKNOWN = "cannot_determine"


@dataclass
class Dependency:
    """Represents a single project dependency."""
    name: str
    version: Optional[str] = None
    source_file: Optional[str] = None
    dependency_type: DependencyType = DependencyType.UNKNOWN


@dataclass
class ScanResult:
    """Contains the results of a project scan."""
    languages: Dict[str, float]  # language -> usage percentage
    package_managers: Set[str]
    dependency_files: List[Path]
    dependencies: List[Dependency]
    errors: List[str]


class LanguageDetector(ABC):
    """Base class for language detection strategies."""
    
    @abstractmethod
    def detect_languages(self, project_path: Path) -> Dict[str, float]:
        """Detect programming languages used in the project.
        
        Args:
            project_path: Root directory of the project
            
        Returns:
            Dictionary mapping language names to their usage percentage
        """
        pass


class PackageManagerDetector(ABC):
    """Base class for package manager detection strategies."""
    
    @abstractmethod
    def detect_package_managers(self, project_path: Path) -> Set[str]:
        """Detect package managers used in the project.
        
        Args:
            project_path: Root directory of the project
            
        Returns:
            Set of detected package manager names
        """
        pass


class DependencyFileParser(ABC):
    """Base class for dependency file parsers."""
    
    @abstractmethod
    def parse_dependencies(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a dependency definition file.
        
        Args:
            file_path: Path to the dependency file
            
        Returns:
            List of detected dependencies
        """
        pass


class ImportAnalyzer(ABC):
    """Base class for source code import analysis."""
    
    @abstractmethod
    def analyze_imports(self, file_path: Path) -> List[Dependency]:
        """Analyze source file for import statements.
        
        Args:
            file_path: Path to the source file
            
        Returns:
            List of detected dependencies from imports
        """
        pass


class DependencyClassifier:
    """Classifies dependencies based on allowed and restricted lists."""
    
    def __init__(self, allowed_list: Set[str], restricted_list: Set[str]):
        self.allowed_list = allowed_list
        self.restricted_list = restricted_list
    
    def classify_dependency(self, dependency: Dependency) -> DependencyType:
        """Classify a dependency based on the configured lists.
        
        Args:
            dependency: Dependency to classify
            
        Returns:
            Classification of the dependency
        """
        if dependency.name in self.allowed_list:
            return DependencyType.ALLOWED
        elif dependency.name in self.restricted_list:
            return DependencyType.RESTRICTED
        return DependencyType.UNKNOWN


def _should_ignore(file_path: Path, root_dir: Path, ignore_patterns: List[str]) -> bool:
    """Check if a file should be ignored based on patterns.
    
    Args:
        file_path: Path to the file to check
        root_dir: Root directory of the scan
        ignore_patterns: List of patterns to ignore
        
    Returns:
        True if the file should be ignored, False otherwise
    """
    if not ignore_patterns:
        return False
        
    # Get the relative path from the root directory
    rel_path = file_path.relative_to(root_dir)
    rel_path_str = str(rel_path)
    
    for pattern in ignore_patterns:
        # Check for directory pattern (ending with '/')
        if pattern.endswith('/'):
            dir_pattern = pattern[:-1]
            # Check if any parent directory matches the pattern
            parent_dirs = [str(p) for p in rel_path.parents]
            if any(fnmatch.fnmatch(d, dir_pattern) for d in parent_dirs):
                return True
        
        # Check for direct file match
        if fnmatch.fnmatch(rel_path_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
            return True
            
    return False


def scan_directory(directory: str, ignore_patterns: List[str] = None) -> Iterator[Path]:
    """Scan a directory recursively and yield file paths.
    
    Args:
        directory: Path to the directory to scan
        ignore_patterns: Optional list of patterns to ignore
        
    Returns:
        Iterator of Path objects for each file found
        
    Raises:
        FileNotFoundError: If the directory does not exist
    """
    if ignore_patterns is None:
        ignore_patterns = []
        
    directory_path = Path(directory)
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not directory_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")
        
    root_dir = directory_path
    
    for root, dirs, files in os.walk(directory_path, topdown=True):
        root_path = Path(root)
        
        # Process files
        for file in files:
            file_path = root_path / file
            
            # Skip files that should be ignored
            if _should_ignore(file_path, root_dir, ignore_patterns):
                continue
            
            # Check file permissions
            try:
                # Check if file has read permissions using stat
                # This is more reliable than os.access in some environments
                stat_result = os.stat(file_path)
                mode = stat_result.st_mode
                
                # If file has no read permissions for owner, skip it
                # 0o400 is the read permission bit for owner
                if not (mode & 0o400):
                    continue
                    
                # Double-check with a direct file open attempt
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1)
                except (PermissionError, OSError):
                    continue
                    
                yield file_path
            except (PermissionError, OSError):
                # Skip files with permission issues
                continue
                
        # Filter out directories that should be ignored
        dirs_to_remove = []
        for i, dir_name in enumerate(dirs):
            dir_path = root_path / dir_name
            if _should_ignore(dir_path, root_dir, ignore_patterns):
                dirs_to_remove.append(i)
                continue
                
            # Check directory permissions
            try:
                if not os.access(dir_path, os.R_OK | os.X_OK):
                    dirs_to_remove.append(i)
            except (PermissionError, OSError):
                dirs_to_remove.append(i)
                
        # Remove directories from bottom to top to avoid index issues
        for i in sorted(dirs_to_remove, reverse=True):
            del dirs[i]


class ProjectScanner:
    """Main scanner class that orchestrates the dependency analysis process."""
    
    def __init__(
        self,
        language_detector: LanguageDetector,
        package_manager_detector: PackageManagerDetector,
        dependency_parsers: Dict[str, DependencyFileParser],
        import_analyzers: Dict[str, ImportAnalyzer],
        dependency_classifier: DependencyClassifier,
    ):
        self.language_detector = language_detector
        self.package_manager_detector = package_manager_detector
        self.dependency_parsers = dependency_parsers
        self.import_analyzers = import_analyzers
        self.dependency_classifier = dependency_classifier
    
    def scan_project(self, project_path: Path) -> ScanResult:
        """Perform a complete scan of the project.
        
        Args:
            project_path: Root directory of the project
            
        Returns:
            ScanResult containing all analysis results
        """
        errors: List[str] = []
        
        try:
            languages = self.language_detector.detect_languages(project_path)
        except Exception as e:
            languages = {}
            errors.append(f"Language detection failed: {str(e)}")
        
        try:
            package_managers = self.package_manager_detector.detect_package_managers(project_path)
        except Exception as e:
            package_managers = set()
            errors.append(f"Package manager detection failed: {str(e)}")
        
        # TODO: Implement dependency file scanning and import analysis
        dependency_files: List[Path] = []
        dependencies: List[Dependency] = []
        
        return ScanResult(
            languages=languages,
            package_managers=package_managers,
            dependency_files=dependency_files,
            dependencies=dependencies,
            errors=errors,
        )