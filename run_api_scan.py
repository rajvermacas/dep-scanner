#!/usr/bin/env python3
"""Script to perform a dependency scan with API call detection."""

import logging
import sys
import os
import json
from pathlib import Path
import argparse

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from dependency_scanner_tool.scanner import DependencyScanner
from dependency_scanner_tool.reporters.html_reporter import HTMLReporter
from dependency_scanner_tool.reporters.json_reporter import JSONReporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class SimpleLanguageDetector:
    """Simple language detector for testing."""
    
    def detect_languages(self, project_path):
        """Return dummy language percentages."""
        return {"Python": 80.0, "JavaScript": 20.0}


class SimplePackageManagerDetector:
    """Simple package manager detector for testing."""
    
    def detect_package_managers(self, project_path):
        """Return dummy package managers."""
        return {"pip", "npm"}


def main():
    """Main entry point for the API scan tool."""
    parser = argparse.ArgumentParser(description="Run dependency scan with API call detection")
    parser.add_argument("directory", help="Directory to scan")
    parser.add_argument("-o", "--output", default="api-scan-report.html",
                      help="Output HTML file path (default: api-scan-report.html)")
    parser.add_argument("-j", "--json", default="api-scan-results.json",
                      help="Output JSON file path (default: api-scan-results.json)")
    parser.add_argument("-t", "--title", default="Dependency Scanner Report with API Calls",
                      help="Report title")
    parser.add_argument("-c", "--categories", help="Path to dependency categories JSON file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--exclude", action="append", default=[],
                       help="Exclude pattern (can be used multiple times)")
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    directory_path = Path(args.directory)
    if not directory_path.exists() or not directory_path.is_dir():
        logger.error(f"Error: Directory not found: {directory_path}")
        sys.exit(1)
    
    # Add default exclude patterns
    exclude_patterns = args.exclude + [".git", "__pycache__", ".pytest_cache", ".venv*", "venv*"]
    
    # Create a scanner with simple detectors
    scanner = DependencyScanner(
        language_detector=SimpleLanguageDetector(),
        package_manager_detector=SimplePackageManagerDetector(),
        ignore_patterns=exclude_patterns
    )
    
    # Run the scan with API call detection enabled
    logger.info(f"Scanning directory: {directory_path}")
    scan_result = scanner.scan_project(
        project_path=str(directory_path),
        analyze_imports=True,
        extract_pip_deps=False,
        analyze_api_calls=True
    )
    
    # Generate JSON output
    json_path = Path(args.json)
    json_reporter = JSONReporter(output_path=json_path)
    json_reporter.generate_report(scan_result)
    logger.info(f"JSON report written to: {json_path}")
    
    # Generate HTML report
    output_path = Path(args.output)
    category_config = Path(args.categories) if args.categories else None
    
    reporter = HTMLReporter(
        output_path=output_path, 
        category_config=category_config
    )
    
    # Generate the report
    try:
        reporter.generate_report(scan_result, title=args.title)
        logger.info(f"HTML report generated: {output_path}")
        
        # Print summary
        print("\n=== Scan Summary ===")
        print(f"Dependencies detected: {len(scan_result.dependencies)}")
        print(f"API calls detected: {len(scan_result.api_calls)}")
        print(f"Errors encountered: {len(scan_result.errors)}")
        print(f"HTML report: {output_path}")
        print(f"JSON report: {json_path}")
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 