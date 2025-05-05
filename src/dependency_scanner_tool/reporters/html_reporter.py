"""HTML reporter for dependency scanner results."""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Union

import jinja2

from dependency_scanner_tool.scanner import ScanResult
from dependency_scanner_tool.reporters.json_reporter import JSONReporter

logger = logging.getLogger(__name__)


class HTMLReporter:
    """Reporter for generating HTML reports from scan results."""

    def __init__(self, 
                 output_path: Optional[Path] = None,
                 template_path: Optional[Path] = None):
        """Initialize the HTML reporter.
        
        Args:
            output_path: Optional path to write the HTML output to.
                         If None, the output will only be returned as a string.
            template_path: Optional path to a custom Jinja2 template.
                           If None, the default template will be used.
        """
        self.output_path = output_path
        self.template_path = template_path
        self.json_reporter = JSONReporter()
        
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

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
        else:
            raise ValueError("Invalid result type. Expected ScanResult, JSON string, or path to JSON file.")
        
        # Load the template
        template = self._get_template()
        
        # Render the template
        html_output = template.render(
            title=title,
            data=data,
            dependency_count=len(data.get('dependencies', [])),
            error_count=len(data.get('errors', [])),
            languages=data.get('scan_summary', {}).get('languages', {}),
            package_managers=data.get('scan_summary', {}).get('package_managers', [])
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
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for dep in data.dependencies %}
            <tr>
                <td>{{ dep.name }}</td>
                <td>{{ dep.version or 'N/A' }}</td>
                <td>{{ dep.source_file or 'N/A' }}</td>
                <td>{{ dep.type }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
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
