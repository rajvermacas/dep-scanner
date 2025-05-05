"""Command-line interface for generating HTML reports from JSON scan results."""

import argparse
import logging
import sys
from pathlib import Path

from dependency_scanner_tool.reporters.html_reporter import HTMLReporter

logger = logging.getLogger(__name__)


def main():
    """Entry point for the HTML report generator."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Generate HTML reports from dependency scanner JSON results"
    )
    parser.add_argument(
        "json_file",
        type=str,
        help="Path to the JSON file containing scan results"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="dependency-report.html",
        help="Path to the output HTML file (default: dependency-report.html)"
    )
    parser.add_argument(
        "-t", "--title",
        type=str,
        default="Dependency Scanner Report",
        help="Title for the HTML report (default: Dependency Scanner Report)"
    )
    parser.add_argument(
        "--template",
        type=str,
        help="Path to a custom Jinja2 template file"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    json_path = Path(args.json_file)
    if not json_path.exists():
        logger.error(f"JSON file not found: {json_path}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize the HTML reporter
    template_path = Path(args.template) if args.template else None
    reporter = HTMLReporter(output_path=output_path, template_path=template_path)
    
    # Generate the HTML report
    try:
        reporter.generate_report(json_path, title=args.title)
        logger.info(f"HTML report generated: {output_path}")
    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
