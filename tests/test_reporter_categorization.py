"""Tests for the integration of dependency categorization with reporters."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from dependency_scanner_tool.scanner import ScanResult, Dependency, DependencyType
from dependency_scanner_tool.categorization import DependencyCategorizer
from dependency_scanner_tool.reporters.json_reporter import JSONReporter
from dependency_scanner_tool.reporters.html_reporter import HTMLReporter


@pytest.fixture
def sample_dependencies():
    """Create a sample list of dependencies for testing."""
    return [
        Dependency(name="flask", version="2.0.1", source_file="requirements.txt", 
                  dependency_type=DependencyType.ALLOWED),
        Dependency(name="django", version="3.2.0", source_file="requirements.txt", 
                  dependency_type=DependencyType.RESTRICTED),
        Dependency(name="numpy", version="1.21.0", source_file="requirements.txt", 
                  dependency_type=DependencyType.UNKNOWN),
        Dependency(name="pandas", version="1.3.0", source_file="requirements.txt", 
                  dependency_type=DependencyType.ALLOWED),
        Dependency(name="tensorflow", version="2.5.0", source_file="requirements.txt", 
                  dependency_type=DependencyType.RESTRICTED),
    ]


@pytest.fixture
def sample_scan_result(sample_dependencies):
    """Create a sample scan result for testing."""
    return ScanResult(
        dependencies=sample_dependencies,
        dependency_files=[Path("requirements.txt")],
        languages={"Python": 100.0},
        package_managers={"pip"},
        api_calls=[],
        errors=[]
    )


@pytest.fixture
def category_config_file():
    """Create a temporary category configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "categories": {
                "Web Frameworks": ["flask", "django"],
                "Data Science": ["numpy", "pandas", "tensorflow"],
                "Machine Learning": ["tensorflow"]
            }
        }, f)
    
    yield Path(f.name)
    
    # Clean up the temporary file
    os.unlink(f.name)


class TestJSONReporterCategorization:
    """Tests for the JSONReporter with categorization."""
    
    def test_json_reporter_with_categorization(self, sample_scan_result, category_config_file):
        """Test that the JSONReporter correctly includes categorized dependencies."""
        # Create a reporter with the category config
        reporter = JSONReporter(category_config=category_config_file)
        
        # Generate the report
        report_str = reporter.generate_report(sample_scan_result)
        report = json.loads(report_str)
        
        # Check that the categorized_dependencies key exists
        assert "categorized_dependencies" in report
        
        # Check that all expected categories are present
        categories = report["categorized_dependencies"]
        assert "Web Frameworks" in categories
        assert "Data Science" in categories
        assert "Machine Learning" in categories
        assert "Uncategorized" not in categories  # All dependencies are categorized
        
        # Check the contents of each category
        assert len(categories["Web Frameworks"]) == 2
        assert len(categories["Data Science"]) == 3
        assert len(categories["Machine Learning"]) == 1
        
        # Check that dependencies are correctly assigned to categories
        web_frameworks = {dep["name"] for dep in categories["Web Frameworks"]}
        assert web_frameworks == {"flask", "django"}
        
        data_science = {dep["name"] for dep in categories["Data Science"]}
        assert data_science == {"numpy", "pandas", "tensorflow"}
        
        machine_learning = {dep["name"] for dep in categories["Machine Learning"]}
        assert machine_learning == {"tensorflow"}
    
    def test_json_reporter_without_categorization(self, sample_scan_result):
        """Test that the JSONReporter works correctly without categorization."""
        # Create a reporter without the category config
        reporter = JSONReporter()
        
        # Generate the report
        report_str = reporter.generate_report(sample_scan_result)
        report = json.loads(report_str)
        
        # Check that the categorized_dependencies key does not exist
        assert "categorized_dependencies" not in report


class TestHTMLReporterCategorization:
    """Tests for the HTMLReporter with categorization."""
    
    def test_html_reporter_with_categorization(self, sample_scan_result, category_config_file):
        """Test that the HTMLReporter correctly includes categorized dependencies."""
        # Create a reporter with the category config
        with tempfile.NamedTemporaryFile(suffix=".html") as output_file:
            reporter = HTMLReporter(
                output_path=Path(output_file.name),
                category_config=category_config_file
            )
            
            # Generate the report
            reporter.generate_report(sample_scan_result)
            
            # Read the generated HTML
            output_file.seek(0)
            html_content = output_file.read().decode('utf-8')
            
            # Check that the categorized dependencies section exists
            assert "Categorized Dependencies" in html_content
            assert "Web Frameworks" in html_content
            assert "Data Science" in html_content
            assert "Machine Learning" in html_content
            
            # Check that all dependencies are included
            assert "flask" in html_content
            assert "django" in html_content
            assert "numpy" in html_content
            assert "pandas" in html_content
            assert "tensorflow" in html_content
    
    def test_html_reporter_without_categorization(self, sample_scan_result):
        """Test that the HTMLReporter works correctly without categorization."""
        # Create a reporter without the category config
        with tempfile.NamedTemporaryFile(suffix=".html") as output_file:
            reporter = HTMLReporter(output_path=Path(output_file.name))
            
            # Generate the report
            reporter.generate_report(sample_scan_result)
            
            # Read the generated HTML
            output_file.seek(0)
            html_content = output_file.read().decode('utf-8')
            
            # Check that the categorized dependencies section does not exist
            assert "Categorized Dependencies" not in html_content


class TestCLICategorization:
    """Tests for the CLI with categorization."""
    
    def test_json_reporter_with_category_config(self, sample_scan_result, category_config_file):
        """Test that the JSONReporter correctly handles category config."""
        from dependency_scanner_tool.reporters.json_reporter import JSONReporter
        
        # Create a reporter with the category config
        reporter = JSONReporter(category_config=category_config_file)
        
        # Generate the report
        report_str = reporter.generate_report(sample_scan_result)
        report_data = json.loads(report_str)
        
        # Verify categorized dependencies are included
        assert "categorized_dependencies" in report_data
        
        # Verify categories
        categories = report_data["categorized_dependencies"]
        assert "Web Frameworks" in categories
        assert "Data Science" in categories
        assert "Machine Learning" in categories
        
    def test_html_reporter_with_category_config_integration(self, sample_scan_result, category_config_file):
        """Test that the HTMLReporter correctly integrates with JSONReporter for categorization."""
        from dependency_scanner_tool.reporters.html_reporter import HTMLReporter
        import jinja2
        
        # Mock the jinja2 template to verify context variables
        original_get_template = HTMLReporter._get_template
        mock_template = MagicMock(spec=jinja2.Template)
        mock_template.render.return_value = "<html>Mocked HTML</html>"
        
        try:
            # Replace the _get_template method to return our mock
            HTMLReporter._get_template = MagicMock(return_value=mock_template)
            
            # Create HTML reporter with category config
            reporter = HTMLReporter(
                output_path=Path("/tmp/test_report.html"),
                category_config=category_config_file
            )
            
            # Generate the report
            reporter.generate_report(sample_scan_result)
            
            # Verify that categorized_dependencies is passed to the template
            render_kwargs = mock_template.render.call_args[1]
            assert 'categorized_dependencies' in render_kwargs
            assert 'Web Frameworks' in render_kwargs['categorized_dependencies']
            assert 'Data Science' in render_kwargs['categorized_dependencies']
            assert 'Machine Learning' in render_kwargs['categorized_dependencies']
            # Note: The 'Uncategorized' category may not be present in the test data
            # depending on the sample dependencies
            
            # Also test with a real template to verify HTML output
            with tempfile.NamedTemporaryFile(suffix=".html") as output_file:
                # Restore original method for this part
                HTMLReporter._get_template = original_get_template
                
                # Create HTML reporter with category config
                reporter = HTMLReporter(
                    output_path=Path(output_file.name),
                    category_config=category_config_file
                )
                
                # Generate the report
                reporter.generate_report(sample_scan_result)
                
                # Read the generated HTML
                output_file.seek(0)
                html_content = output_file.read().decode('utf-8')
                
                # Verify the categorized section exists
                assert "Categorized Dependencies" in html_content
                assert "Web Frameworks" in html_content
                assert "Data Science" in html_content
                assert "Machine Learning" in html_content
        finally:
            # Restore the original method
            HTMLReporter._get_template = original_get_template
