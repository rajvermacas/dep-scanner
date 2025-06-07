"""Main entry point for the dependency scanner tool."""

import argparse
import logging
import os
from pathlib import Path

from dependency_scanner_tool.scanner import DependencyScanner
from dependency_scanner_tool.reporters.json_reporter import JSONReporter
from dependency_scanner_tool.reporters.html_reporter import HTMLReporter

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Scan project dependencies and API usage")
    parser.add_argument("project_path", help="Path to project directory")
    parser.add_argument("--exclude", action="append", help="Patterns to exclude")
    parser.add_argument("--json-output", help="Output JSON report to file")
    parser.add_argument("--html-output", help="Output HTML report to file")
    parser.add_argument("--category-config", help="Path to dependency category configuration")
    parser.add_argument("--config", help="Path to main configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load config for API dependency classification
    config_file = args.config or args.category_config or 'config.yaml'
    
    # Import and setup API dependency classifier
    from dependency_scanner_tool.api_categorization import ApiDependencyClassifier
    import yaml
    
    config = {}
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            logging.info(f"Loaded configuration from {config_file}")
    except Exception as e:
        logging.warning(f"Failed to load config file {config_file}: {e}")
    
    # Create API dependency classifier with config
    api_classifier = ApiDependencyClassifier(config)
    
    # Run the scanner with the proper API classifier
    scanner = DependencyScanner(
        ignore_patterns=args.exclude,
        api_dependency_classifier=api_classifier
    )
    result = scanner.scan_project(args.project_path)
    
    # Generate reports
    if args.json_output:
        json_reporter = JSONReporter(
            output_path=Path(args.json_output),
            category_config=Path(args.category_config) if args.category_config else None
        )
        json_reporter.generate_report(result)
    
    if args.html_output:
        html_reporter = HTMLReporter(
            output_path=Path(args.html_output),
            category_config=Path(args.category_config) if args.category_config else None
        )
        html_reporter.generate_report(result)

if __name__ == "__main__":
    main()
