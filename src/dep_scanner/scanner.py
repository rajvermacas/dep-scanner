"""Core scanner module for analyzing project dependencies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


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