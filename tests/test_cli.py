"""Tests for the CLI module."""

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from dep_scanner.cli import main


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
