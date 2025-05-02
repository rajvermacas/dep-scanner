"""Core scanner module for analyzing project dependencies."""

import fnmatch
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from dep_scanner.exceptions import (
    DirectoryAccessError,
    FileAccessError,
    LanguageDetectionError,
    PackageManagerDetectionError,
    ParsingError,
    DependencyScannerError,
)


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
    """Base class for dependency file parsers.
    
    Note: This is a legacy interface. New code should use the parsers in the parsers module.
    """
    
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
        
    Raises:
        ValueError: If the file_path is not relative to root_dir
    """
    if not ignore_patterns:
        return False
    
    try:    
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
    except ValueError as e:
        # If the file_path is not relative to root_dir, log a warning and re-raise
        logging.warning(f"Error checking ignore pattern: {e}")
        raise ValueError(f"File path {file_path} is not relative to root directory {root_dir}")
            
    return False


def scan_directory(directory: str, ignore_patterns: List[str] = None) -> Iterator[Path]:
    """Scan a directory recursively and yield file paths.
    
    Args:
        directory: Path to the directory to scan
        ignore_patterns: Optional list of patterns to ignore
        
    Returns:
        Iterator of Path objects for each file found
        
    Raises:
        DirectoryAccessError: If the directory cannot be accessed
    """
    if ignore_patterns is None:
        ignore_patterns = []
    
    try:    
        directory_path = Path(directory)
        if not directory_path.exists():
            raise DirectoryAccessError(directory, f"Directory not found: {directory}")
        
        if not directory_path.is_dir():
            raise DirectoryAccessError(directory, f"Not a directory: {directory}")
        
        if not os.access(directory_path, os.R_OK):
            raise DirectoryAccessError(directory, f"Permission denied: {directory}")
            
        root_dir = directory_path
        
        for root, dirs, files in os.walk(directory_path, topdown=True):
            root_path = Path(root)
            
            # Process files
            for file in files:
                file_path = root_path / file
                
                try:
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
                            logging.debug(f"Skipping file with no read permissions: {file_path}")
                            continue
                            
                        # Double-check with a direct file open attempt
                        try:
                            with open(file_path, 'rb') as f:
                                f.read(1)
                            yield file_path
                        except (PermissionError, OSError) as e:
                            logging.debug(f"Cannot open file {file_path}: {e}")
                            continue
                    except (PermissionError, OSError) as e:
                        logging.debug(f"Permission error for file {file_path}: {e}")
                        continue
                except ValueError as e:
                    # If _should_ignore raises ValueError, log and skip the file
                    logging.warning(f"Error checking ignore pattern for {file_path}: {e}")
                    continue
                except Exception as e:
                    # Catch any other exceptions, log them, and skip the file
                    logging.warning(f"Unexpected error processing file {file_path}: {e}")
                    continue
                    
            # Filter out directories that should be ignored
            dirs_to_remove = []
            for i, dir_name in enumerate(dirs):
                dir_path = root_path / dir_name
                try:
                    if _should_ignore(dir_path, root_dir, ignore_patterns):
                        dirs_to_remove.append(i)
                        continue
                    
                    # Check directory permissions
                    try:
                        if not os.access(dir_path, os.R_OK | os.X_OK):
                            logging.debug(f"Skipping directory with no access: {dir_path}")
                            dirs_to_remove.append(i)
                    except (PermissionError, OSError) as e:
                        logging.debug(f"Permission error for directory {dir_path}: {e}")
                        dirs_to_remove.append(i)
                except ValueError as e:
                    # If _should_ignore raises ValueError, log and skip the directory
                    logging.warning(f"Error checking ignore pattern for {dir_path}: {e}")
                    dirs_to_remove.append(i)
                except Exception as e:
                    # Catch any other exceptions, log them, and skip the directory
                    logging.warning(f"Unexpected error processing directory {dir_path}: {e}")
                    dirs_to_remove.append(i)
                    
            # Remove directories from bottom to top to avoid index issues
            for i in sorted(dirs_to_remove, reverse=True):
                del dirs[i]
    except DirectoryAccessError:
        # Re-raise DirectoryAccessError as is
        raise
    except Exception as e:
        # Convert any other exceptions to our custom exception
        error_msg = f"Error scanning directory {directory}: {str(e)}"
        logging.error(error_msg)
        raise DirectoryAccessError(directory, error_msg)


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
        
        # Initialize the parser manager for the new parser system
        from dep_scanner.parsers.parser_manager import ParserManager
        self.parser_manager = ParserManager()
    
    def scan_project(self, project_path: Path) -> ScanResult:
        """Perform a complete scan of the project.
        
        Args:
            project_path: Root directory of the project
            
        Returns:
            ScanResult containing all analysis results
            
        Raises:
            DirectoryAccessError: If the project directory cannot be accessed
        """
        # Validate project path
        if not project_path.exists():
            raise DirectoryAccessError(project_path, f"Project directory not found: {project_path}")
        
        if not project_path.is_dir():
            raise DirectoryAccessError(project_path, f"Not a directory: {project_path}")
        
        if not os.access(project_path, os.R_OK):
            raise DirectoryAccessError(project_path, f"Permission denied: {project_path}")
        
        errors: List[str] = []
        languages: Dict[str, float] = {}
        package_managers: Set[str] = set()
        dependency_files: List[Path] = []
        dependencies: List[Dependency] = []
        
        # Detect languages
        try:
            logging.info(f"Detecting languages in {project_path}")
            languages = self.language_detector.detect_languages(project_path)
            logging.info(f"Detected languages: {languages}")
        except LanguageDetectionError as e:
            error_msg = f"Language detection failed: {str(e)}"
            logging.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during language detection: {str(e)}"
            logging.error(error_msg)
            errors.append(error_msg)
        
        # Detect package managers
        try:
            logging.info(f"Detecting package managers in {project_path}")
            package_managers = self.package_manager_detector.detect_package_managers(project_path)
            logging.info(f"Detected package managers: {package_managers}")
        except PackageManagerDetectionError as e:
            error_msg = f"Package manager detection failed: {str(e)}"
            logging.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during package manager detection: {str(e)}"
            logging.error(error_msg)
            errors.append(error_msg)
        
        # Find and parse dependency files
        try:
            logging.info(f"Finding dependency files in {project_path}")
            dependency_files = self._find_dependency_files(project_path)
            logging.info(f"Found {len(dependency_files)} dependency files")
            
            # Parse each dependency file
            for file_path in dependency_files:
                try:
                    file_dependencies = self.parser_manager.parse_file(file_path)
                    dependencies.extend(file_dependencies)
                    logging.info(f"Parsed {len(file_dependencies)} dependencies from {file_path}")
                except ParsingError as e:
                    error_msg = f"Error parsing dependency file {file_path}: {str(e)}"
                    logging.error(error_msg)
                    errors.append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during dependency file scanning: {str(e)}"
            logging.error(error_msg)
            errors.append(error_msg)
            
        # TODO: Implement import analysis
        
        # Create and return the scan result
        result = ScanResult(
            languages=languages,
            package_managers=package_managers,
            dependency_files=dependency_files,
            dependencies=dependencies,
            errors=errors,
        )
        
        # Log a summary of the scan results
        self._log_scan_summary(result)
        
        return result
    
    def _log_scan_summary(self, result: ScanResult) -> None:
        """Log a summary of the scan results.
        
        Args:
            result: The scan result to summarize
        """
        logging.info("=== Scan Summary ===")
        logging.info(f"Languages detected: {len(result.languages)}")
        logging.info(f"Package managers detected: {len(result.package_managers)}")
        logging.info(f"Dependency files found: {len(result.dependency_files)}")
        logging.info(f"Dependencies identified: {len(result.dependencies)}")
        
        if result.errors:
            logging.warning(f"Scan completed with {len(result.errors)} errors")
        else:
            logging.info("Scan completed successfully with no errors")
    
    def _find_dependency_files(self, project_path: Path) -> List[Path]:
        """Find dependency files in the project.
        
        Args:
            project_path: Root directory of the project
            
        Returns:
            List of paths to dependency files
        """
        dependency_files = []
        supported_extensions = self.parser_manager.get_supported_extensions()
        supported_filenames = self.parser_manager.get_supported_filenames()
        
        logging.debug(f"Looking for dependency files with extensions: {supported_extensions}")
        logging.debug(f"Looking for dependency files with names: {supported_filenames}")
        
        # Scan the project directory for dependency files
        for file_path in scan_directory(str(project_path)):
            # Check if the file is a known dependency file by name
            if file_path.name in supported_filenames:
                dependency_files.append(file_path)
                continue
                
            # Check if the file has a supported extension
            if file_path.suffix.lower() in supported_extensions:
                # Verify that a parser can actually handle this file
                parser = self.parser_manager.get_parser_for_file(file_path)
                if parser:
                    dependency_files.append(file_path)
        
        return dependency_files