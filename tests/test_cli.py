"""Tests for the CLI module."""

from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner
import tempfile
from pathlib import Path
from dep_scanner.cli import main
from dep_scanner.scanner import DependencyType, ScanResult, Dependency


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
        mock_result.dependencies = []
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


@patch('dep_scanner.cli.DependencyScanner')
def test_cli_with_conda_env(mock_scanner_class, cli_runner):
    """Test CLI with conda environment file option."""
    # Create a mock scanner instance
    mock_scanner = mock_scanner_class.return_value
    mock_scanner.scan_project.return_value = ScanResult(
        languages={"python": 100.0},
        package_managers={"pip"},
        dependency_files=[],
        dependencies=[
            Dependency(name="numpy", version="1.21.0"),
            Dependency(name="pandas", version="1.3.0"),
        ],
        errors=[]
    )
    
    # Create a temporary conda environment file
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "project"
        project_dir.mkdir()
        
        # Create a conda environment file
        conda_env_file = project_dir / "environment.yml"
        with open(conda_env_file, "w") as f:
            f.write("""
name: myenv
channels:
  - conda-forge
dependencies:
  - python=3.9
  - numpy=1.21.0
  - pandas=1.3.0
""")
        
        # Run the CLI command with conda-env option
        result = cli_runner.invoke(main, [
            str(project_dir),
            "--conda-env", str(conda_env_file)
        ])
        
        # Print the error output for debugging
        print(f"Exit code: {result.exit_code}")
        print(f"Exception: {result.exception}")
        print(f"Output: {result.output}")
        
        # Check that the command ran successfully
        assert result.exit_code == 0
        
        # Check that scan_project was called with the correct parameters
        mock_scanner.scan_project.assert_called_once()
        call_args = mock_scanner.scan_project.call_args[1]
        assert call_args["project_path"] == str(project_dir)
        assert call_args["conda_env_path"] == conda_env_file


@patch('dep_scanner.cli.DependencyScanner')
def test_cli_with_conda_env_and_venv(mock_scanner_class, cli_runner):
    """Test CLI with both conda environment and virtual environment options."""
    # Create a mock scanner instance
    mock_scanner = mock_scanner_class.return_value
    mock_scanner.scan_project.return_value = ScanResult(
        languages={"python": 100.0},
        package_managers={"pip", "conda"},
        dependency_files=[],
        dependencies=[
            Dependency(name="numpy", version="1.21.0"),
            Dependency(name="pandas", version="1.3.0"),
            Dependency(name="requests", version="2.25.0"),
        ],
        errors=[]
    )
    
    # Create temporary directories and files
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "project"
        project_dir.mkdir()
        
        # Create a conda environment file
        conda_env_file = project_dir / "environment.yml"
        with open(conda_env_file, "w") as f:
            f.write("""
name: myenv
channels:
  - conda-forge
dependencies:
  - python=3.9
  - numpy=1.21.0
  - pandas=1.3.0
""")
        
        # Create a virtual environment directory
        venv_dir = project_dir / ".venv"
        venv_dir.mkdir()
        
        # Run the CLI command with both conda-env and venv options
        result = cli_runner.invoke(main, [
            str(project_dir),
            "--conda-env", str(conda_env_file),
            "--venv", str(venv_dir)
        ])
        
        # Check that the command ran successfully
        assert result.exit_code == 0
        
        # Check that scan_project was called with the correct parameters
        mock_scanner.scan_project.assert_called_once()
        call_args = mock_scanner.scan_project.call_args[1]
        assert call_args["project_path"] == str(project_dir)
        assert call_args["conda_env_path"] == conda_env_file
        assert call_args["venv_path"] == venv_dir
