"""Main entry point for the dependency scanner tool."""

import argparse
import logging
from pathlib import Path

from dependency_scanner_tool.scanner import DependencyScanner, DependencyClassifier
from dependency_scanner_tool.reporters.json_reporter import JSONReporter
from dependency_scanner_tool.reporters.html_reporter import HTMLReporter
from dependency_scanner_tool.cli import SimpleLanguageDetector, SimplePackageManagerDetector
from dependency_scanner_tool.file_util import get_config_path

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
    config_file = args.config or args.category_config or get_config_path()
    
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
    
    # Extract allowed and restricted dependencies from config categories
    allowed_list = set()
    restricted_list = set()
    
    categories = config.get('categories', {})
    for category_name, category_data in categories.items():
        status = category_data.get('status', 'unknown').lower()
        dependencies = category_data.get('dependencies', [])
        
        if status == 'allowed':
            allowed_list.update(dependencies)
        elif status == 'restricted':
            restricted_list.update(dependencies)
    
    # Also check for direct allowed_dependencies and restricted_dependencies in config
    allowed_list.update(config.get('allowed_dependencies', []))
    restricted_list.update(config.get('restricted_dependencies', []))
    
    logging.info(f"Loaded {len(allowed_list)} allowed dependencies: {sorted(allowed_list)}")
    logging.info(f"Loaded {len(restricted_list)} restricted dependencies: {sorted(restricted_list)}")
    
    # Create language and package manager detectors
    language_detector = SimpleLanguageDetector()
    package_manager_detector = SimplePackageManagerDetector()
    
    # Run the scanner with the proper API classifier
    scanner = DependencyScanner(
        language_detector=language_detector,
        package_manager_detector=package_manager_detector,
        ignore_patterns=args.exclude,
        api_dependency_classifier=api_classifier
    )
    result = scanner.scan_project(args.project_path)
    
    # Classify dependencies if we have classification lists
    if allowed_list or restricted_list:
        dependency_classifier = DependencyClassifier(allowed_list, restricted_list)
        logging.info(f"Classifying {len(result.dependencies)} dependencies")
        
        for dependency in result.dependencies:
            dependency.dependency_type = dependency_classifier.classify_dependency(dependency)
        
        # Log classification summary
        classified_counts = {}
        for dep in result.dependencies:
            dep_type = dep.dependency_type.value
            classified_counts[dep_type] = classified_counts.get(dep_type, 0) + 1
        
        logging.info(f"Classification summary: {classified_counts}")
    
    # Generate reports
    # Use the same config file for categorization as we loaded above
    category_config_path = None
    if args.category_config:
        category_config_path = Path(args.category_config)
    elif Path(config_file).exists():
        category_config_path = Path(config_file)
    
    if args.json_output:
        json_reporter = JSONReporter(
            output_path=Path(args.json_output),
            category_config=category_config_path
        )
        json_reporter.generate_report(result)
    
    if args.html_output:
        html_reporter = HTMLReporter(
            output_path=Path(args.html_output),
            category_config=category_config_path
        )
        html_reporter.generate_report(result)

if __name__ == "__main__":
    main()
