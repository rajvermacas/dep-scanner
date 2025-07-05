"""Base classes for infrastructure scanners."""

import fnmatch
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent
)


class BaseInfrastructureScanner(ABC):
    """Base class for all infrastructure scanners."""
    
    @abstractmethod
    def get_supported_file_patterns(self) -> List[str]:
        """Return list of file patterns this scanner can handle."""
        pass
    
    @abstractmethod
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        pass
    
    @abstractmethod
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file for infrastructure components."""
        pass
    
    def can_handle_file(self, file_path: Path) -> bool:
        """Check if this scanner can handle the given file."""
        filename = file_path.name
        patterns = self.get_supported_file_patterns()
        
        return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


class InfrastructureScannerRegistry:
    """Registry for infrastructure scanners."""
    
    def __init__(self):
        self._scanners: Dict[str, BaseInfrastructureScanner] = {}
    
    def register(self, name: str, scanner: BaseInfrastructureScanner):
        """Register a scanner with the given name."""
        self._scanners[name] = scanner
    
    def get(self, name: str) -> BaseInfrastructureScanner:
        """Get a scanner by name."""
        if name not in self._scanners:
            raise KeyError(f"Scanner '{name}' not found")
        return self._scanners[name]
    
    def get_all(self) -> Dict[str, BaseInfrastructureScanner]:
        """Get all registered scanners."""
        return self._scanners.copy()
    
    def get_scanners_for_file(self, file_path: Path) -> List[BaseInfrastructureScanner]:
        """Get all scanners that can handle the given file."""
        return [
            scanner for scanner in self._scanners.values()
            if scanner.can_handle_file(file_path)
        ]