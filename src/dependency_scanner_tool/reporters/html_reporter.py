"""HTML reporter for dependency scanner results."""

import json
import logging
import os
import yaml
from pathlib import Path
from typing import Optional, Union, Dict, List

import jinja2

from dependency_scanner_tool.scanner import ScanResult, Dependency
from dependency_scanner_tool.reporters.json_reporter import JSONReporter
from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiAuthType
from dependency_scanner_tool.file_util import get_config_path

logger = logging.getLogger(__name__)


class HTMLReporter:
    """Reporter for generating HTML reports from scan results."""

    def __init__(self, 
                 output_path: Optional[Path] = None,
                 template_path: Optional[Path] = None,
                 category_config: Optional[Path] = None):
        """Initialize the HTML reporter.
        
        Args:
            output_path: Optional path to write the HTML output to.
                         If None, the output will only be returned as a string.
            template_path: Optional path to a custom Jinja2 template.
                           If None, the default template will be used.
            category_config: Optional path to a JSON file containing category definitions.
                             If provided, dependencies will be categorized accordingly.
        """
        self.output_path = output_path
        self.template_path = template_path
        self.category_config = category_config
        self.json_reporter = JSONReporter(category_config=category_config)
        
        # Load category status from config.yaml
        self.allowed_categories = []
        self.restricted_categories = []
        self._load_category_status()
        
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

    def _load_category_status(self):
        """Load category statuses from config.yaml."""
        config_path = Path(get_config_path())
        self.category_statuses = {}

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    
                    # Handle new unified structure
                    if 'categories' in config_data:
                        for category_name, category_data in config_data['categories'].items():
                            if isinstance(category_data, dict):
                                status = category_data.get('status', 'cannot_determine')
                                self.category_statuses[category_name] = status
                        
                        allowed_count = sum(1 for status in self.category_statuses.values() if status == 'allowed')
                        restricted_count = sum(1 for status in self.category_statuses.values() if status == 'restricted')
                        logger.info(f"Loaded category status: {allowed_count} allowed, {restricted_count} restricted")
                    
                    # Handle legacy structure for backward compatibility
                    else:
                        self.allowed_categories = config_data.get('allowed_categories', [])
                        self.restricted_categories = config_data.get('restricted_categories', [])
                        
                        # Convert to new format
                        for category in self.allowed_categories:
                            self.category_statuses[category] = 'allowed'
                        for category in self.restricted_categories:
                            self.category_statuses[category] = 'restricted'
                        
                        logger.info(f"Loaded legacy category status: {len(self.allowed_categories)} allowed, {len(self.restricted_categories)} restricted")
                        
            except (yaml.YAMLError, IOError, OSError) as e:
                logger.error(f"Failed to load configuration from {config_path}: {e}")

    def _get_category_status(self, category_name: str) -> str:
        """Determine the status of a category.
        
        Args:
            category_name: Name of the category
            
        Returns:
            Status string: 'allowed', 'restricted', or 'cannot_determine'
        """
        return self.category_statuses.get(category_name, 'cannot_determine')

    def generate_report(self, 
                        result: Union[ScanResult, str, Path],
                        title: str = "Dependency Scanner Report") -> str:
        """Generate an HTML report from scan results.
        
        Args:
            result: Either a ScanResult object, a JSON string, or a Path to a JSON file
            title: Optional title for the HTML report
            
        Returns:
            HTML string representation of the scan results
            
        Raises:
            ValueError: If the input result is invalid
        """
        # Get data from the scan result
        if isinstance(result, ScanResult):
            data = self.json_reporter._convert_to_dict(result)
        elif isinstance(result, str) and (result.startswith('{') or result.startswith('[')):
            # Assume it's a JSON string
            data = json.loads(result)
        elif isinstance(result, (str, Path)) and os.path.isfile(str(result)):
            # Assume it's a path to a JSON file
            with open(result, 'r') as f:
                data = json.load(f)
                
                # If we're loading from a file and have a category config,
                # but the data doesn't have categorized_dependencies,
                # we need to regenerate the data with categorization
                logger.debug(f"Category config: {self.category_config}")
                logger.debug(f"Has categorized_dependencies: {'categorized_dependencies' in data}")
                logger.debug(f"Condition result: {self.category_config and 'categorized_dependencies' not in data}")
                if self.category_config and 'categorized_dependencies' not in data:
                    logger.info("Re-generating report data with categorization")
                    # Create a temporary ScanResult to apply categorization
                    
                    # Convert the JSON dependencies back to Dependency objects
                    dependencies = []
                    for dep_dict in data.get('dependencies', []):
                        dependencies.append(
                            Dependency(
                                name=dep_dict.get('name', ''),
                                version=dep_dict.get('version'),
                                source_file=dep_dict.get('source_file')
                            )
                        )
                    
                    # Create a minimal ScanResult with just the dependencies
                    scan_result = ScanResult(
                        languages=data.get('scan_summary', {}).get('languages', {}),
                        package_managers=set(data.get('scan_summary', {}).get('package_managers', [])),
                        dependency_files=[Path(df) for df in data.get('dependency_files', [])],
                        dependencies=dependencies,
                        api_calls=[],  # Empty list for API calls
                        errors=data.get('errors', [])
                    )
                    
                    # Get the categorized data
                    data = self.json_reporter._convert_to_dict(scan_result)
        else:
            raise ValueError("Invalid result type. Expected ScanResult, JSON string, or path to JSON file.")
        
        # Extract unified categories for the template
        unified_categories = data.get('unified_categories', {})
        logger.debug(f"Found {len(unified_categories)} unified categories: {list(unified_categories.keys())}")
        
        # Extract separate categorized dependencies and API calls for backward compatibility
        categorized_deps = data.get('categorized_dependencies', {})
        categorized_api_calls = data.get('categorized_api_calls', {})
        logger.debug(f"Found {len(categorized_deps)} dependency categories: {list(categorized_deps.keys())}")
        logger.debug(f"Found {len(categorized_api_calls)} API categories: {list(categorized_api_calls.keys())}")
        
        # Create a dictionary of category statuses (unified approach)
        all_categories = set(unified_categories.keys()) | set(categorized_deps.keys()) | set(categorized_api_calls.keys())
        category_statuses = {}
        for category in all_categories:
            category_statuses[category] = self._get_category_status(category)
        
        # Create separate status dictionaries for backward compatibility
        dep_category_statuses = {}
        for category in categorized_deps.keys():
            dep_category_statuses[category] = self._get_category_status(category)
        
        api_category_statuses = {}
        for category in categorized_api_calls.keys():
            api_category_statuses[category] = self._get_category_status(category)
        
        # Load the template
        template = self._get_template()
        
        # Debug unified_categories before passing to template
        logger.debug(f"Unified categories being passed to template: {list(unified_categories.keys())}")
        for cat_name, cat_data in unified_categories.items():
            deps = cat_data.get('dependencies', [])
            apis = cat_data.get('api_calls', [])
            logger.debug(f"  {cat_name}: {len(deps)} deps, {len(apis)} APIs")
            if deps:
                logger.debug(f"    First dep: {deps[0].get('name', 'unknown')} (type: {type(deps[0]).__name__})")
        
        # Calculate total allowed categories (not individual dependencies)
        total_allowed_dependencies = 0
        for category, items in unified_categories.items():
            if self._get_category_status(category) == 'allowed':
                total_allowed_dependencies += 1
        
        # If no unified categories, fall back to categorized_deps
        if not unified_categories and categorized_deps:
            for category, deps in categorized_deps.items():
                if self._get_category_status(category) == 'allowed':
                    total_allowed_dependencies += 1
        
        # Render the template
        html_output = template.render(
            title=title,
            data=data,
            dependency_count=len(data.get('dependencies', [])),
            api_call_count=len(data.get('api_calls', [])),
            error_count=len(data.get('errors', [])),
            total_allowed_dependencies=total_allowed_dependencies,
            languages=data.get('scan_summary', {}).get('languages', {}),
            package_managers=data.get('scan_summary', {}).get('package_managers', []),
            infrastructure_usage=data.get('scan_summary', {}).get('infrastructure_usage', {}),
            api_calls=data.get('api_calls', []),
            unified_categories=unified_categories,
            categorized_dependencies=categorized_deps,
            categorized_api_calls=categorized_api_calls,
            category_statuses=category_statuses,
            dep_category_statuses=dep_category_statuses,
            api_category_statuses=api_category_statuses
        )
        
        # Write to file if output path is specified
        if self.output_path:
            try:
                with open(self.output_path, 'w') as f:
                    f.write(html_output)
                logger.info(f"HTML report written to {self.output_path}")
            except (IOError, OSError, FileNotFoundError) as e:
                logger.error(f"Failed to write HTML report to {self.output_path}: {e}")
                # Don't re-raise the exception, just log it and continue
        
        return html_output

    def _get_template(self) -> jinja2.Template:
        """Get the Jinja2 template for the HTML report.
        
        Returns:
            Jinja2 Template object
        """
        if self.template_path and os.path.isfile(self.template_path):
            # Use custom template
            try:
                with open(self.template_path, 'r') as f:
                    template_str = f.read()
                return self.jinja_env.from_string(template_str)
            except (IOError, OSError, FileNotFoundError) as e:
                logger.warning(f"Failed to read custom template {self.template_path}: {e}")
                # Fall back to default template
        
        # Use default template
        try:
            return self.jinja_env.get_template('report.html')
        except jinja2.exceptions.TemplateNotFound:
            # Create a basic template if the default is not found
            logger.warning("Default template not found, using basic template")
            return self.jinja_env.from_string(self._get_basic_template())

    def _get_basic_template(self) -> str:
        """Get a basic HTML template as a fallback.
        
        Returns:
            Basic HTML template string
        """
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1, h2, h3 {
            margin-top: 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    
    <h2>Summary</h2>
    <p>Dependencies: {{ dependency_count }}</p>
    <p>Languages: {{ languages|length }}</p>
    <p>Package Managers: {{ package_managers|length }}</p>
    <p>Errors: {{ error_count }}</p>
    
    <h2>Dependencies</h2>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Version</th>
                <th>Source</th>
            </tr>
        </thead>
        <tbody>
            {% for dep in data.dependencies %}
            <tr>
                <td>{{ dep.name }}</td>
                <td>{{ dep.version or 'N/A' }}</td>
                <td>{{ dep.source_file or 'N/A' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    {% if categorized_dependencies %}
    <h2>Categorized Dependencies</h2>
    {% for category, deps in categorized_dependencies.items() %}
    <h3>{{ category }} (Status: {{ category_statuses[category] }})</h3>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Version</th>
                <th>Source</th>
            </tr>
        </thead>
        <tbody>
            {% for dep in deps %}
            <tr>
                <td>{{ dep.name }}</td>
                <td>{{ dep.version or 'N/A' }}</td>
                <td>{{ dep.source_file or 'N/A' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endfor %}
    {% endif %}
    
    {% if data.errors %}
    <h2>Errors</h2>
    <ul>
        {% for error in data.errors %}
        <li>{{ error }}</li>
        {% endfor %}
    </ul>
    {% endif %}
    
    <footer>
        <p>Generated by Dependency Scanner Tool</p>
    </footer>
</body>
</html>"""
