#!/usr/bin/env python3
"""Script to generate an HTML report with categorized dependencies."""

import logging
import sys
import os
import json
from pathlib import Path
import argparse

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from dependency_scanner_tool.reporters.html_reporter import HTMLReporter
from dependency_scanner_tool.categorization import DependencyCategorizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the report generator."""
    parser = argparse.ArgumentParser(description="Generate HTML report from scan results")
    parser.add_argument("json_file", help="Path to JSON scan results file")
    parser.add_argument("-o", "--output", default="dependency-report.html",
                      help="Output HTML file path (default: dependency-report.html)")
    parser.add_argument("-t", "--title", default="Dependency Scanner Report",
                      help="Report title")
    parser.add_argument("-c", "--categories", help="Path to dependency categories JSON file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--debug", action="store_true", help="Debug mode - print additional information")
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    json_path = Path(args.json_file)
    if not json_path.exists():
        logger.error(f"Error: JSON file not found: {json_path}")
        sys.exit(1)
    
    output_path = Path(args.output)
    
    # Check if categories file exists and log its contents
    category_config = None
    if args.categories:
        category_path = Path(args.categories)
        if not category_path.exists():
            logger.error(f"Categories file not found: {category_path}")
            sys.exit(1)
        
        category_config = category_path
        logger.info(f"Using categories file: {category_path}")
        
        # Log the contents of the categories file
        try:
            with open(category_path, 'r') as f:
                categories_data = json.load(f)
                logger.info(f"Categories loaded: {list(categories_data.get('categories', {}).keys())}")
                
                # Debug: Process the dependencies directly with the categorizer
                if args.debug:
                    # Load the scan results
                    with open(json_path, 'r') as scan_file:
                        scan_data = json.load(scan_file)
                    
                    # Create a categorizer
                    categorizer = DependencyCategorizer(categories_data)
                    
                    # Convert JSON dependencies to Dependency objects
                    from dependency_scanner_tool.scanner import Dependency, DependencyType
                    dependencies = []
                    for dep_dict in scan_data.get('dependencies', []):
                        dep_type = DependencyType.ALLOWED
                        if dep_dict.get('type') == 'restricted':
                            dep_type = DependencyType.RESTRICTED
                        elif dep_dict.get('type') == 'cannot_determine':
                            dep_type = DependencyType.CANNOT_DETERMINE
                            
                        dependencies.append(
                            Dependency(
                                name=dep_dict.get('name', ''),
                                version=dep_dict.get('version'),
                                source_file=dep_dict.get('source_file'),
                                dependency_type=dep_type
                            )
                        )
                    
                    # Categorize the dependencies
                    categorized = categorizer.categorize_dependencies(dependencies)
                    print("\n=== DEBUG: Categorized Dependencies ===")
                    for category, deps in categorized.items():
                        print(f"Category '{category}': {len(deps)} dependencies")
                        for dep in deps:
                            print(f"  - {dep.name}")
                    print("=======================================\n")
                    
                    # Create a new JSON file with categorized dependencies
                    scan_data['categorized_dependencies'] = {
                        category: [
                            {
                                'name': dep.name,
                                'version': dep.version,
                                'source_file': dep.source_file,
                                'type': dep.dependency_type.value
                            } for dep in deps
                        ] for category, deps in categorized.items()
                    }
                    
                    # Write the enhanced JSON file
                    debug_json_path = Path('debug-scan-results.json')
                    with open(debug_json_path, 'w') as f:
                        json.dump(scan_data, f, indent=2)
                    print(f"Debug JSON file written to {debug_json_path}")
                    
        except Exception as e:
            logger.error(f"Error reading categories file: {e}")
    
    # Create the HTML reporter with category config if provided
    reporter = HTMLReporter(output_path=output_path, category_config=category_config)
    
    # Generate the report
    try:
        html_output = reporter.generate_report(json_path, title=args.title)
        
        # Check if categorized_dependencies is in the rendered template
        if 'categorized_dependencies' in html_output:
            logger.info("Categorized dependencies section found in HTML output")
        else:
            logger.warning("Categorized dependencies section NOT found in HTML output")
        
        logger.info(f"Report generated: {output_path}")
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 