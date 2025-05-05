"""JSON reporter for dependency scanner results."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from dependency_scanner_tool.scanner import ScanResult

logger = logging.getLogger(__name__)


class JSONReporter:
    """Reporter for generating JSON output from scan results."""

    def __init__(self, output_path: Optional[Path] = None):
        """Initialize the JSON reporter.
        
        Args:
            output_path: Optional path to write the JSON output to.
                         If None, the output will only be returned as a string.
        """
        self.output_path = output_path

    def generate_report(self, result: ScanResult) -> str:
        """Generate a JSON report from scan results.
        
        Args:
            result: ScanResult object containing the scan results
            
        Returns:
            JSON string representation of the scan results
            
        Raises:
            IOError: If the output file cannot be written
        """
        # Convert scan result to a dictionary
        result_dict = self._convert_to_dict(result)
        
        # Convert to JSON string
        json_output = json.dumps(result_dict, indent=2)
        
        # Write to file if output path is specified
        if self.output_path:
            try:
                with open(self.output_path, 'w') as f:
                    f.write(json_output)
                logger.info(f"JSON report written to {self.output_path}")
            except (IOError, OSError, FileNotFoundError) as e:
                logger.error(f"Failed to write JSON report to {self.output_path}: {e}")
                # Don't re-raise the exception, just log it and continue
        
        return json_output

    def _convert_to_dict(self, result: ScanResult) -> Dict[str, Any]:
        """Convert a ScanResult object to a dictionary.
        
        Args:
            result: ScanResult object to convert
            
        Returns:
            Dictionary representation of the scan result
        """
        return {
            "scan_summary": {
                "languages": {k: float(v) for k, v in result.languages.items()},
                "package_managers": list(result.package_managers),
                "dependency_count": len(result.dependencies),
                "error_count": len(result.errors)
            },
            "dependency_files": [str(df) for df in result.dependency_files],
            "dependencies": [
                {
                    "name": dep.name,
                    "version": dep.version,
                    "source_file": dep.source_file,
                    "type": dep.dependency_type.value
                } for dep in result.dependencies
            ],
            "errors": result.errors
        }
