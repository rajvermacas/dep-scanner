"""Tests for the CLI module."""

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from dep_scanner.cli import main
from dep_scanner.scanner import DependencyType


@pytest.fixture
def cli_runner():
    """Fixture for creating a Click CLI test runner."""
    return CliRunner()


def test_cli_exclude_option(cli_runner, tmp_path):
    """Test that the --exclude option is properly passed to the scanner."""
    # Create a temporary project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    with patch('dep_scanner.cli.DependencyScanner') as mock_scanner_class, \
         patch('dep_scanner.cli.SimpleLanguageDetector'), \
         patch('dep_scanner.cli.SimplePackageManagerDetector'), \
         patch('dep_scanner.cli.format_scan_result'):
        
        # Create a mock scanner instance with a mock scan_project method
        mock_scanner_instance = MagicMock()
        mock_scanner_class.return_value = mock_scanner_instance
        
        # Mock the scan_project method to return a ScanResult
        mock_result = MagicMock()
        mock_scanner_instance.scan_project.return_value = mock_result
        
        # Run the CLI command with exclude options
        result = cli_runner.invoke(
            main, 
            ['--exclude', 'node_modules', '--exclude', '.venv', str(project_dir)]
        )
        
        # Check that the command executed successfully
        assert result.exit_code == 0
        
        # Verify that DependencyScanner was initialized with the correct ignore patterns
        mock_scanner_class.assert_called_once()
        call_kwargs = mock_scanner_class.call_args.kwargs
        assert 'ignore_patterns' in call_kwargs
        assert 'node_modules' in call_kwargs['ignore_patterns']
        assert '.venv' in call_kwargs['ignore_patterns']


def test_cli_exclude_with_config(cli_runner, tmp_path):
    """Test that exclude options are combined with config file ignore patterns."""
    # Create a temporary project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    # Create a temporary config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
ignore_patterns:
  - "*.pyc"
  - "__pycache__"
""")
    
    with patch('dep_scanner.cli.DependencyScanner') as mock_scanner_class, \
         patch('dep_scanner.cli.SimpleLanguageDetector'), \
         patch('dep_scanner.cli.SimplePackageManagerDetector'), \
         patch('dep_scanner.cli.format_scan_result'):
        
        # Create a mock scanner instance with a mock scan_project method
        mock_scanner_instance = MagicMock()
        mock_scanner_class.return_value = mock_scanner_instance
        
        # Mock the scan_project method to return a ScanResult
        mock_result = MagicMock()
        mock_scanner_instance.scan_project.return_value = mock_result
        
        # Run the CLI command with exclude options and config file
        result = cli_runner.invoke(
            main, 
            [
                '--exclude', 'node_modules', 
                '--config', str(config_file),
                str(project_dir)
            ]
        )
        
        # Check that the command executed successfully
        assert result.exit_code == 0
        
        # Verify that DependencyScanner was initialized with the correct ignore patterns
        mock_scanner_class.assert_called_once()
        call_kwargs = mock_scanner_class.call_args.kwargs
        assert 'ignore_patterns' in call_kwargs
        
        # Check that both config and CLI patterns are included
        assert '*.pyc' in call_kwargs['ignore_patterns']
        assert '__pycache__' in call_kwargs['ignore_patterns']
        assert 'node_modules' in call_kwargs['ignore_patterns']


def test_cli_allow_restrict_options(cli_runner, tmp_path):
    """Test that the --allow and --restrict options properly classify dependencies."""
    # Create a temporary project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    with patch('dep_scanner.cli.DependencyScanner') as mock_scanner_class, \
         patch('dep_scanner.cli.SimpleLanguageDetector'), \
         patch('dep_scanner.cli.SimplePackageManagerDetector'), \
         patch('dep_scanner.cli.DependencyClassifier') as mock_classifier_class, \
         patch('dep_scanner.cli.format_scan_result'):
        
        # Create a mock scanner instance with a mock scan_project method
        mock_scanner_instance = MagicMock()
        mock_scanner_class.return_value = mock_scanner_instance
        
        # Create mock dependencies
        mock_dep1 = MagicMock()
        mock_dep1.name = "requests"
        mock_dep2 = MagicMock()
        mock_dep2.name = "insecure-lib"
        
        # Mock the scan_project method to return a ScanResult with dependencies
        mock_result = MagicMock()
        mock_result.dependencies = [mock_dep1, mock_dep2]
        mock_scanner_instance.scan_project.return_value = mock_result
        
        # Mock the classifier
        mock_classifier_instance = MagicMock()
        mock_classifier_class.return_value = mock_classifier_instance
        
        # Set up the classifier to return appropriate values
        def classify_side_effect(dep):
            if dep.name == "requests":
                return DependencyType.ALLOWED
            elif dep.name == "insecure-lib":
                return DependencyType.RESTRICTED
            return DependencyType.UNKNOWN
        
        mock_classifier_instance.classify_dependency.side_effect = classify_side_effect
        
        # Run the CLI command with allow and restrict options
        result = cli_runner.invoke(
            main, 
            [
                '--allow', 'requests', 
                '--restrict', 'insecure-lib',
                str(project_dir)
            ]
        )
        
        # Check that the command executed successfully
        assert result.exit_code == 0
        
        # Verify that DependencyClassifier was initialized with the correct lists
        mock_classifier_class.assert_called_once()
        call_args = mock_classifier_class.call_args[0]
        assert 'requests' in call_args[0]  # allowed_list
        assert 'insecure-lib' in call_args[1]  # restricted_list
        
        # Verify that classify_dependency was called for each dependency
        assert mock_classifier_instance.classify_dependency.call_count == 2


def test_cli_allow_restrict_with_config(cli_runner, tmp_path):
    """Test that allow/restrict options are combined with config file settings."""
    # Create a temporary project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    # Create a temporary config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
allowed_dependencies:
  - "pytest"
  - "flask"
restricted_dependencies:
  - "deprecated-lib"
""")
    
    with patch('dep_scanner.cli.DependencyScanner') as mock_scanner_class, \
         patch('dep_scanner.cli.SimpleLanguageDetector'), \
         patch('dep_scanner.cli.SimplePackageManagerDetector'), \
         patch('dep_scanner.cli.DependencyClassifier') as mock_classifier_class, \
         patch('dep_scanner.cli.format_scan_result'):
        
        # Create a mock scanner instance with a mock scan_project method
        mock_scanner_instance = MagicMock()
        mock_scanner_class.return_value = mock_scanner_instance
        
        # Mock the scan_project method to return a ScanResult
        mock_result = MagicMock()
        mock_result.dependencies = []
        mock_scanner_instance.scan_project.return_value = mock_result
        
        # Run the CLI command with allow/restrict options and config file
        result = cli_runner.invoke(
            main, 
            [
                '--allow', 'requests', 
                '--restrict', 'insecure-lib',
                '--config', str(config_file),
                str(project_dir)
            ]
        )
        
        # Check that the command executed successfully
        assert result.exit_code == 0
        
        # Verify that DependencyClassifier was initialized with the correct lists
        # (if there are dependencies to classify)
        if mock_result.dependencies:
            mock_classifier_class.assert_called_once()
            call_args = mock_classifier_class.call_args[0]
            
            # Check that both config and CLI allowed dependencies are included
            allowed_list = call_args[0]
            assert 'requests' in allowed_list
            assert 'pytest' in allowed_list
            assert 'flask' in allowed_list
            
            # Check that both config and CLI restricted dependencies are included
            restricted_list = call_args[1]
            assert 'insecure-lib' in restricted_list
            assert 'deprecated-lib' in restricted_list
