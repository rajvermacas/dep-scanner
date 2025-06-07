"""Base classes for API call analyzers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set

class ApiAuthType(Enum):
    """Classification of API authentication types."""
    NONE = "none"
    BASIC = "basic"
    TOKEN = "token"
    OAUTH = "oauth"
    API_KEY = "api_key"
    UNKNOWN = "unknown"

@dataclass
class ApiCall:
    """Represents a single REST API call."""
    url: str
    http_method: Optional[str] = None
    auth_type: ApiAuthType = ApiAuthType.UNKNOWN
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    status: str = "cannot_determine"

class ApiCallAnalyzer(ABC):
    """Base class for API call analyzers."""
    
    # Define supported file extensions for each analyzer
    supported_extensions: Set[str] = set()
    
    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this analyzer can handle the file, False otherwise
        """
        return file_path.suffix.lower() in self.supported_extensions
    
    @abstractmethod
    def analyze(self, file_path: Path) -> List[ApiCall]:
        """Analyze a file for API calls.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of API calls found in the file
        """
        pass
