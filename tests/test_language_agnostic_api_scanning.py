"""Tests for language-agnostic API scanning and regex pattern matching."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from dependency_scanner_tool.scanner import DependencyScanner
from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiAuthType
from dependency_scanner_tool.api_categorization import ApiDependencyClassifier


class TestLanguageAgnosticApiScanning(unittest.TestCase):
    """Test cases for language-agnostic API scanning."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test projects
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)

        # Create various file types with API URLs
        self._create_test_files()

        # Create scanner with mocked dependencies
        self.scanner = DependencyScanner(
            language_detector=MagicMock(),
            package_manager_detector=MagicMock(),
            ignore_patterns=[".git", "*.pyc"]
        )

        # Configure include patterns to test language-agnostic scanning
        # This allows scanning of files beyond just ImportAnalyzer extensions
        self.scanner.api_scan_include_patterns = ["*.js", "*.yml", "*.yaml", "*.sh"]

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def _create_test_files(self):
        """Create test files with various extensions containing API URLs."""
        # Python file
        (self.project_path / "test.py").write_text(
            'response = requests.get("https://api.example.com/users")\n'
        )

        # JavaScript file
        (self.project_path / "test.js").write_text(
            'fetch("https://api.github.com/repos").then(res => res.json())\n'
        )

        # Config file (YAML)
        (self.project_path / "config.yml").write_text(
            'api_url: "https://api.internal.example.com/data"\n'
        )

        # Text file (README)
        (self.project_path / "README.txt").write_text(
            'The API endpoint is: https://api.docs.example.com/v1/reference\n'
        )

        # Markdown file
        (self.project_path / "README.md").write_text(
            'Check out our API: https://api.public.example.com/swagger\n'
        )

        # Shell script
        (self.project_path / "deploy.sh").write_text(
            'curl -X POST https://api.deploy.example.com/webhook\n'
        )

        # Binary file (should be skipped)
        (self.project_path / "image.png").write_bytes(b'\x89PNG\r\n\x1a\n')

    def test_find_api_scannable_files(self):
        """Test that _find_api_scannable_files returns text files (excluding configured patterns)."""
        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, [])

        # Should include production code files
        file_names = [f.name for f in api_scannable_files]

        self.assertIn("test.py", file_names)
        self.assertIn("test.js", file_names)
        self.assertIn("config.yml", file_names)
        self.assertIn("deploy.sh", file_names)

        # Files matching api_scan_exclude_patterns should be excluded (*.txt, *.md)
        self.assertNotIn("README.txt", file_names)
        self.assertNotIn("README.md", file_names)

        # Binary files should be excluded
        self.assertNotIn("image.png", file_names)

    def test_scan_all_file_types_for_api_calls(self):
        """Test that API calls are detected in production code file types (excluding configured patterns)."""
        result = self.scanner.scan_project(
            str(self.project_path),
            analyze_imports=False,
            analyze_api_calls=True
        )

        # Extract unique URLs from detected API calls
        detected_urls = {api_call.url for api_call in result.api_calls}

        # Verify API calls from production code files are detected
        self.assertIn("https://api.example.com/users", detected_urls)  # Python
        self.assertIn("https://api.github.com/repos", detected_urls)  # JavaScript
        self.assertIn("https://api.internal.example.com/data", detected_urls)  # YAML
        self.assertIn("https://api.deploy.example.com/webhook", detected_urls)  # Shell

        # API calls from excluded files (.txt, .md) should NOT be detected
        self.assertNotIn("https://api.docs.example.com/v1/reference", detected_urls)  # TXT (excluded)
        self.assertNotIn("https://api.public.example.com/swagger", detected_urls)  # Markdown (excluded)

    def test_scan_ignores_binary_files(self):
        """Test that binary files are properly ignored."""
        result = self.scanner.scan_project(
            str(self.project_path),
            analyze_imports=False,
            analyze_api_calls=True
        )

        # No API calls should come from binary files
        for api_call in result.api_calls:
            self.assertNotIn("image.png", api_call.source_file)

    def test_scan_respects_ignore_patterns(self):
        """Test that ignore patterns are respected in API scanning."""
        # Create a .git directory with a file containing API URL
        git_dir = self.project_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text(
            'url = https://api.ignored.example.com/git\n'
        )

        result = self.scanner.scan_project(
            str(self.project_path),
            analyze_imports=False,
            analyze_api_calls=True
        )

        # API calls from ignored files should not be detected
        detected_urls = {api_call.url for api_call in result.api_calls}
        self.assertNotIn("https://api.ignored.example.com/git", detected_urls)

    def test_api_scan_exclude_patterns_markdown(self):
        """Test that markdown files are excluded from API scanning when configured."""
        # Create scanner with API scan exclusion patterns
        scanner = DependencyScanner(
            language_detector=MagicMock(),
            package_manager_detector=MagicMock(),
            ignore_patterns=[".git"]
        )
        # Manually set exclusion patterns (normally loaded from config)
        scanner.api_scan_exclude_patterns = ["*.md", "*.markdown"]

        api_scannable_files = scanner._find_api_scannable_files(self.project_path, [])
        file_names = [f.name for f in api_scannable_files]

        # Markdown files should be excluded
        self.assertNotIn("README.md", file_names)

    def test_api_scan_exclude_patterns_tests(self):
        """Test that test files are excluded from API scanning when configured."""
        # Create test directory with test files
        test_dir = self.project_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_api.py").write_text(
            'response = requests.get("https://api.test.example.com/mock")\n'
        )
        (self.project_path / "test_utils.py").write_text(
            'url = "https://api.test2.example.com/helper"\n'
        )

        # Create scanner with test file exclusions
        scanner = DependencyScanner(
            language_detector=MagicMock(),
            package_manager_detector=MagicMock(),
            ignore_patterns=[".git"]
        )
        scanner.api_scan_exclude_patterns = ["test_*", "tests/", "**/tests/"]

        result = scanner.scan_project(
            str(self.project_path),
            analyze_imports=False,
            analyze_api_calls=True
        )

        # API calls from test files should not be detected
        detected_urls = {api_call.url for api_call in result.api_calls}
        self.assertNotIn("https://api.test.example.com/mock", detected_urls)
        self.assertNotIn("https://api.test2.example.com/helper", detected_urls)

    def test_api_scan_exclude_patterns_txt_files(self):
        """Test that .txt files are excluded from API scanning when configured."""
        # Scanner should have already created test.txt in setUp
        scanner = DependencyScanner(
            language_detector=MagicMock(),
            package_manager_detector=MagicMock(),
            ignore_patterns=[".git"]
        )
        scanner.api_scan_exclude_patterns = ["*.txt"]

        result = scanner.scan_project(
            str(self.project_path),
            analyze_imports=False,
            analyze_api_calls=True
        )

        # API calls from .txt files should not be detected
        detected_urls = {api_call.url for api_call in result.api_calls}
        self.assertNotIn("https://api.docs.example.com/v1/reference", detected_urls)


class TestRegexPatternMatching(unittest.TestCase):
    """Test cases for regex pattern matching in API categorization."""

    def test_regex_pattern_matching(self):
        """Test that regex patterns work correctly."""
        config = {
            "categories": {
                "GitHub APIs": {
                    "api_patterns": [
                        # Regex pattern with escaped dots and grouping
                        r"https://api\.github\.com/(users|repos|orgs)/.*"
                    ],
                    "status": "allowed"
                }
            }
        }
        classifier = ApiDependencyClassifier(config)

        # Should match URLs with /users/, /repos/, /orgs/
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.github.com/users/octocat", "GET", "test.py", 1)
            ),
            "allowed"
        )
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.github.com/repos/owner/repo", "GET", "test.py", 2)
            ),
            "allowed"
        )
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.github.com/orgs/myorg", "GET", "test.py", 3)
            ),
            "allowed"
        )

        # Should NOT match other paths
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.github.com/gists", "GET", "test.py", 4)
            ),
            "cannot_determine"
        )

    def test_regex_with_subdomain_wildcard(self):
        """Test regex patterns with subdomain wildcards."""
        config = {
            "categories": {
                "Internal APIs": {
                    "api_patterns": [
                        # Match any subdomain of example.com
                        r"https://.*\.example\.com/.*"
                    ],
                    "status": "restricted"
                }
            }
        }
        classifier = ApiDependencyClassifier(config)

        # Should match various subdomains
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.example.com/data", "GET", "test.py", 1)
            ),
            "restricted"
        )
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://internal.example.com/users", "GET", "test.py", 2)
            ),
            "restricted"
        )
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://v2.api.example.com/posts", "GET", "test.py", 3)
            ),
            "restricted"
        )

    def test_glob_pattern_backward_compatibility(self):
        """Test that glob patterns still work (backward compatibility)."""
        config = {
            "categories": {
                "Public APIs": {
                    "api_patterns": [
                        # Glob pattern (no escaping needed)
                        "https://api.public.com/*"
                    ],
                    "status": "allowed"
                }
            }
        }
        classifier = ApiDependencyClassifier(config)

        # Glob patterns should still work
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.public.com/users", "GET", "test.py", 1)
            ),
            "allowed"
        )
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.public.com/v1/data", "GET", "test.py", 2)
            ),
            "allowed"
        )

    def test_mixed_regex_and_glob_patterns(self):
        """Test that regex and glob patterns can coexist."""
        config = {
            "categories": {
                "Mixed Category": {
                    "api_patterns": [
                        # Regex pattern
                        r"https://api\.example\.com/(v1|v2)/.*",
                        # Glob pattern
                        "https://api.other.com/*"
                    ],
                    "status": "allowed"
                }
            }
        }
        classifier = ApiDependencyClassifier(config)

        # Regex pattern should work
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.example.com/v1/users", "GET", "test.py", 1)
            ),
            "allowed"
        )

        # Glob pattern should work
        self.assertEqual(
            classifier.classify_api_call(
                ApiCall("https://api.other.com/data", "GET", "test.py", 2)
            ),
            "allowed"
        )

    def test_regex_categorization(self):
        """Test that API calls are correctly categorized using regex patterns."""
        config = {
            "categories": {
                "Auth Services": {
                    "api_patterns": [
                        r"https://(auth|login|oauth)\..*\.com/.*"
                    ],
                    "status": "restricted"
                },
                "Data Services": {
                    "api_patterns": [
                        r"https://.*\.(data|storage)\.com/.*"
                    ],
                    "status": "allowed"
                }
            }
        }
        classifier = ApiDependencyClassifier(config)

        # Test categorization
        auth_call = ApiCall("https://auth.example.com/token", "POST", "test.py", 1)
        categories = classifier.categorize_api_call(auth_call)
        self.assertIn("Auth Services", categories)

        data_call = ApiCall("https://api.data.com/files", "GET", "test.py", 2)
        categories = classifier.categorize_api_call(data_call)
        self.assertIn("Data Services", categories)


class TestApiScanningUnionLogic(unittest.TestCase):
    """Test API scanning union logic (analyzers + includes + dependency files)."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test projects
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)

        # Create scanner with mocked dependencies
        self.scanner = DependencyScanner(
            language_detector=MagicMock(),
            package_manager_detector=MagicMock(),
            ignore_patterns=[".git", "*.pyc"]
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_union_includes_analyzer_extensions(self):
        """Test that files with ImportAnalyzer extensions are included."""
        # Create files with analyzer extensions
        (self.project_path / "main.py").write_text('print("hello")\n')
        (self.project_path / "app.java").write_text('public class App {}\n')
        (self.project_path / "script.scala").write_text('object Script {}\n')

        # Create a file without analyzer extension
        (self.project_path / "data.csv").write_text('a,b,c\n1,2,3\n')

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, [])
        file_names = [f.name for f in api_scannable_files]

        # Files with analyzer extensions should be included
        self.assertIn("main.py", file_names)
        self.assertIn("app.java", file_names)
        self.assertIn("script.scala", file_names)

        # CSV file should NOT be included (no analyzer extension, no include pattern)
        self.assertNotIn("data.csv", file_names)

    def test_union_includes_include_patterns(self):
        """Test that files matching api_scan_include_patterns are included."""
        # Create files matching include patterns
        (self.project_path / "config.json").write_text('{"key": "value"}\n')
        (self.project_path / "settings.yaml").write_text('setting: value\n')
        (self.project_path / "app.config").write_text('[section]\nkey=value\n')

        # Configure include patterns
        self.scanner.api_scan_include_patterns = ["*.json", "*.yaml", "*.config"]

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, [])
        file_names = [f.name for f in api_scannable_files]

        # Files matching include patterns should be included
        self.assertIn("config.json", file_names)
        self.assertIn("settings.yaml", file_names)
        self.assertIn("app.config", file_names)

    def test_union_includes_dependency_files(self):
        """Test that dependency files are always included (unless explicitly excluded)."""
        # Create dependency files
        requirements_txt = self.project_path / "requirements.txt"
        requirements_txt.write_text('requests==2.28.0\n')

        pom_xml = self.project_path / "pom.xml"
        pom_xml.write_text('<project></project>\n')

        build_gradle = self.project_path / "build.gradle"
        build_gradle.write_text('dependencies {}\n')

        # Create dependency file list
        dependency_files = [requirements_txt, pom_xml, build_gradle]

        # Clear exclusion patterns for this test
        self.scanner.api_scan_exclude_patterns = []

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, dependency_files)
        file_names = [f.name for f in api_scannable_files]

        # Dependency files should be included when no exclusions apply
        self.assertIn("requirements.txt", file_names)
        self.assertIn("pom.xml", file_names)
        self.assertIn("build.gradle", file_names)

    def test_union_all_three_sources(self):
        """Test that union includes files from all three sources."""
        # 1. Analyzer extension file
        (self.project_path / "main.py").write_text('print("hello")\n')

        # 2. Include pattern file
        (self.project_path / "config.json").write_text('{"key": "value"}\n')
        self.scanner.api_scan_include_patterns = ["*.json"]

        # 3. Dependency file (using .gradle to avoid .txt exclusion from default config)
        build_gradle = self.project_path / "build.gradle"
        build_gradle.write_text('dependencies {}\n')
        dependency_files = [build_gradle]

        # 4. File that doesn't match any criteria
        (self.project_path / "data.csv").write_text('a,b,c\n')

        # Clear exclusion patterns for this test
        self.scanner.api_scan_exclude_patterns = []

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, dependency_files)
        file_names = [f.name for f in api_scannable_files]

        # All three sources should be included
        self.assertIn("main.py", file_names)  # Analyzer extension
        self.assertIn("config.json", file_names)  # Include pattern
        self.assertIn("build.gradle", file_names)  # Dependency file

        # CSV should NOT be included
        self.assertNotIn("data.csv", file_names)

    def test_exclude_patterns_applied_after_union(self):
        """Test that exclude patterns are applied after union logic."""
        # Create files that would be included by union
        (self.project_path / "main.py").write_text('print("hello")\n')
        (self.project_path / "test_app.py").write_text('def test_something(): pass\n')
        (self.project_path / "config.json").write_text('{"key": "value"}\n')

        # Configure include patterns
        self.scanner.api_scan_include_patterns = ["*.json"]

        # Configure exclude patterns
        self.scanner.api_scan_exclude_patterns = ["test_*"]

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, [])
        file_names = [f.name for f in api_scannable_files]

        # main.py should be included (analyzer extension, not excluded)
        self.assertIn("main.py", file_names)

        # config.json should be included (include pattern, not excluded)
        self.assertIn("config.json", file_names)

        # test_app.py should be EXCLUDED (matches exclude pattern)
        self.assertNotIn("test_app.py", file_names)

    def test_dependency_files_can_be_excluded(self):
        """Test that dependency files can be excluded if they match exclude patterns."""
        # Create dependency file
        requirements_txt = self.project_path / "requirements.txt"
        requirements_txt.write_text('requests==2.28.0\n')
        dependency_files = [requirements_txt]

        # Configure exclude pattern for .txt files
        self.scanner.api_scan_exclude_patterns = ["*.txt"]

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, dependency_files)
        file_names = [f.name for f in api_scannable_files]

        # Dependency file should be EXCLUDED (matches exclude pattern)
        self.assertNotIn("requirements.txt", file_names)

    def test_union_with_nested_directories(self):
        """Test that union logic works with files in nested directories."""
        # Create nested directory structure
        (self.project_path / "src").mkdir()
        (self.project_path / "src" / "main.py").write_text('print("hello")\n')

        (self.project_path / "config").mkdir()
        (self.project_path / "config" / "settings.yaml").write_text('setting: value\n')

        # Configure include patterns
        self.scanner.api_scan_include_patterns = ["*.yaml"]

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, [])

        # Get full paths for comparison
        main_py_path = self.project_path / "src" / "main.py"
        settings_yaml_path = self.project_path / "config" / "settings.yaml"

        # Both files should be included
        self.assertIn(main_py_path, api_scannable_files)
        self.assertIn(settings_yaml_path, api_scannable_files)

    def test_binary_files_excluded_from_union(self):
        """Test that binary files are excluded even if they match union criteria."""
        # Create a binary file with .py extension (PNG magic bytes followed by null byte)
        binary_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        (self.project_path / "binary.py").write_bytes(binary_content)

        # Also create a real PNG file to ensure binary detection works
        (self.project_path / "image.png").write_bytes(binary_content)

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, [])
        file_names = [f.name for f in api_scannable_files]

        # Binary file should NOT be included even though it has .py extension
        self.assertNotIn("binary.py", file_names)
        # PNG file should also not be included (binary extension)
        self.assertNotIn("image.png", file_names)

    def test_empty_include_patterns_does_not_filter(self):
        """Test that empty include patterns doesn't filter out files."""
        # Create files with analyzer extensions
        (self.project_path / "main.py").write_text('print("hello")\n')
        (self.project_path / "app.java").write_text('public class App {}\n')

        # No include patterns configured
        self.scanner.api_scan_include_patterns = []

        api_scannable_files = self.scanner._find_api_scannable_files(self.project_path, [])
        file_names = [f.name for f in api_scannable_files]

        # Files with analyzer extensions should still be included
        self.assertIn("main.py", file_names)
        self.assertIn("app.java", file_names)


if __name__ == "__main__":
    unittest.main()
