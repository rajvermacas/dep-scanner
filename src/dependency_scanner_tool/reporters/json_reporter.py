"""JSON reporter for dependency scanner results."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import defaultdict

from dependency_scanner_tool.scanner import ScanResult, Dependency
from dependency_scanner_tool.categorization import DependencyCategorizer
from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiAuthType

logger = logging.getLogger(__name__)


class JSONReporter:
    """Reporter for generating JSON output from scan results."""

    def __init__(self, output_path: Optional[Path] = None, category_config: Optional[Path] = None):
        """Initialize the JSON reporter.
        
        Args:
            output_path: Optional path to write the JSON output to.
                         If None, the output will only be returned as a string.
            category_config: Optional path to a JSON file containing category definitions.
                             If provided, dependencies will be categorized accordingly.
        """
        self.output_path = output_path
        self.categorizer = None
        
        if category_config and category_config.exists():
            try:
                self.categorizer = DependencyCategorizer.from_json(category_config)
                logger.info(f"Loaded dependency categorization config from {category_config}")
            except Exception as e:
                logger.error(f"Failed to load category config: {e}")
                # Don't re-raise, just continue without categorization

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
    
    def _deduplicate_dependencies(self, dependencies: List[Dependency]) -> List[Dict[str, Any]]:
        """Deduplicate dependencies by name while preserving usage information.
        
        Args:
            dependencies: List of dependencies to deduplicate
            
        Returns:
            List of deduplicated dependency dictionaries with usage information
        """
        # Group dependencies by name
        grouped_deps = defaultdict(list)
        for dep in dependencies:
            grouped_deps[dep.name].append(dep)
        
        # Create deduplicated list with usage information
        deduplicated = []
        for name, deps in grouped_deps.items():
            # Find the most specific version (prefer non-None versions)
            versions = [d.version for d in deps if d.version]
            version = versions[0] if versions else None
            
            # Get unique source files
            source_files = [d.source_file for d in deps if d.source_file]
            unique_sources = list(set(source_files))
            
            # Get the most restrictive dependency type
            dep_types = [d.dependency_type for d in deps]
            dep_type = min(dep_types, key=lambda x: x.value)
            
            deduplicated.append({
                "name": name,
                "version": version,
                "source_files": unique_sources,
                "occurrence_count": len(deps),
                "type": dep_type.value
            })
        
        # Sort by name for consistent output
        return sorted(deduplicated, key=lambda x: x["name"])

    def _convert_to_dict(self, result: ScanResult) -> Dict[str, Any]:
        """Convert a ScanResult object to a dictionary.
        
        Args:
            result: ScanResult object to convert
            
        Returns:
            Dictionary representation of the scan result
        """
        # Deduplicate dependencies
        deduplicated_deps = self._deduplicate_dependencies(result.dependencies)
        unique_dep_count = len(deduplicated_deps)
        
        output_dict = {
            "scan_summary": {
                "languages": {k: float(v) for k, v in result.languages.items()},
                "package_managers": list(result.package_managers),
                "total_dependency_occurrences": len(result.dependencies),
                "unique_dependency_count": unique_dep_count,
                "api_call_count": len(result.api_calls),
                "error_count": len(result.errors)
            },
            "dependency_files": [str(df) for df in result.dependency_files],
            "dependencies": deduplicated_deps,
            "raw_dependencies": [
                {
                    "name": dep.name,
                    "version": dep.version,
                    "source_file": dep.source_file,
                    "type": dep.dependency_type.value
                } for dep in result.dependencies
            ],
            "api_calls": [
                {
                    "url": api_call.url,
                    "http_method": api_call.http_method,
                    "auth_type": api_call.auth_type.value,
                    "source_file": api_call.source_file,
                    "line_number": api_call.line_number
                } for api_call in result.api_calls
            ],
            "errors": result.errors
        }
        
        # Add categorized dependencies if a categorizer is available
        if self.categorizer:
            logger.debug(f"Categorizing {len(result.dependencies)} dependencies")
            categorized = self.categorizer.categorize_dependencies(result.dependencies)
            logger.debug(f"Found {len(categorized)} categories: {list(categorized.keys())}")
            
            # Deduplicate dependencies within each category
            deduplicated_categorized = {}
            for category, deps in categorized.items():
                deduplicated_categorized[category] = self._deduplicate_dependencies(deps)
            
            output_dict["categorized_dependencies"] = deduplicated_categorized
            
            # Log the categorized dependencies
            for category, deps in categorized.items():
                logger.debug(f"Category '{category}': {len(deps)} dependencies")
                for dep in deps:
                    logger.debug(f"  - {dep.name}")
            
        return output_dict
