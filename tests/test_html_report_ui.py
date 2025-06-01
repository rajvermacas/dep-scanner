"""Tests for the HTML report UI using Playwright."""

import json
import os
import subprocess
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from playwright.sync_api import sync_playwright

from dependency_scanner_tool.cli import main
from dependency_scanner_tool.reporters.html_reporter import HTMLReporter


class TestHTMLReportUI(unittest.TestCase):
    """Test the HTML report UI using Playwright."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment."""
        # Create a temporary directory for test files
        cls.temp_dir = TemporaryDirectory()
        cls.temp_path = Path(cls.temp_dir.name)
        
        # Create a sample requirements.txt file
        cls.requirements_path = cls.temp_path / "requirements.txt"
        with open(cls.requirements_path, "w") as f:
            f.write("\n".join([
                "django==3.2.0",
                "numpy==1.21.0",
                "pandas==1.3.0",
                "tensorflow==2.5.0",
                "requests==2.26.0",
                "tomli==2.0.1"
            ]))
        
        # Create a sample categories.json file
        cls.categories_path = cls.temp_path / "categories.json"
        with open(cls.categories_path, "w") as f:
            json.dump({
                "Web Frameworks": ["django", "tomli"],
                "Data Science": ["numpy", "pandas"],
                "Machine Learning": ["tensorflow"]
            }, f)
        
        # Generate the HTML report
        cls.html_report_path = cls.temp_path / "report.html"
        main([
            str(cls.temp_path),
            "--category-config", str(cls.categories_path),
            "--html-output", str(cls.html_report_path)
        ])
        
        # Start a web server to serve the HTML report
        cls.server_port = 8999
        cls.server_process = subprocess.Popen(
            ["python", "-m", "http.server", str(cls.server_port)],
            cwd=str(cls.temp_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for the server to start
        time.sleep(1)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up the test environment."""
        # Stop the web server
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.wait()
        
        # Clean up the temporary directory
        cls.temp_dir.cleanup()
    
    def test_categorized_dependencies_section_exists(self):
        """Test that the categorized dependencies section exists in the HTML report."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Navigate to the HTML report
                page.goto(f"http://localhost:{self.server_port}/report.html")
                
                # Check if the categorized dependencies section exists
                section_header = page.locator("text=Categorized Dependencies").first
                self.assertTrue(section_header.is_visible(), 
                                "Categorized Dependencies section is not visible")
                
                # Check if all categories are present
                categories = ["Web Frameworks", "Data Science", "Machine Learning", "Uncategorized"]
                for category in categories:
                    category_header = page.locator(f"text={category}").first
                    self.assertTrue(category_header.is_visible(), 
                                    f"{category} category is not visible")
            finally:
                browser.close()
    
    def test_categorized_dependencies_content(self):
        """Test that the categorized dependencies content is correct."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Navigate to the HTML report
                page.goto(f"http://localhost:{self.server_port}/report.html")
                
                # Check Web Frameworks category
                web_frameworks = self._get_dependencies_in_category(page, "Web Frameworks")
                self.assertIn("django", web_frameworks)
                self.assertIn("tomli", web_frameworks)
                
                # Check Data Science category
                data_science = self._get_dependencies_in_category(page, "Data Science")
                self.assertIn("numpy", data_science)
                self.assertIn("pandas", data_science)
                
                # Check Machine Learning category
                machine_learning = self._get_dependencies_in_category(page, "Machine Learning")
                self.assertIn("tensorflow", machine_learning)
                
                # Check Uncategorized category
                uncategorized = self._get_dependencies_in_category(page, "Uncategorized")
                self.assertIn("requests", uncategorized)
            finally:
                browser.close()
    
    def test_categorized_dependencies_with_empty_config(self):
        """Test that the categorized dependencies section is not shown with empty config."""
        # Generate a new HTML report without categories
        html_report_path = self.temp_path / "report_no_categories.html"
        main([
            str(self.temp_path),
            "--html-output", str(html_report_path)
        ])
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Navigate to the HTML report
                page.goto(f"http://localhost:{self.server_port}/report_no_categories.html")
                
                # Check if the categorized dependencies section exists (should not)
                section_header = page.locator("text=Categorized Dependencies").first
                self.assertFalse(section_header.is_visible(), 
                                "Categorized Dependencies section should not be visible")
            finally:
                browser.close()
    
    def _get_dependencies_in_category(self, page, category):
        """Helper method to get dependencies in a category."""
        # Find the category section
        category_section = page.locator(f"h3:text('{category}')").first
        
        # Get the table that follows the category header
        table = category_section.locator("xpath=following::table[1]")
        
        # Get all dependency names from the first column
        rows = table.locator("tbody tr")
        dependencies = []
        
        for i in range(rows.count()):
            row = rows.nth(i)
            name_cell = row.locator("td").first
            dependencies.append(name_cell.inner_text())
        
        return dependencies
