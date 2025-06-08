"""Tests for the CLI module."""

from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner
import tempfile
from pathlib import Path
from dependency_scanner_tool.cli import main
from dependency_scanner_tool.scanner import DependencyType, ScanResult, Dependency


@pytest.fixture
def cli_runner():
    """Fixture for creating a Click CLI test runner."""
    return CliRunner()


def test_cli_exclude_option(cli_runner, tmp_path):
    """Test that the --exclude option is properly passed to the scanner."""
    # Create a temporary project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    with patch('dependency_scanner_tool.cli.DependencyScanner') as mock_scanner_class, \
         patch('dependency_scanner_tool.cli.SimpleLanguageDetector'), \
         patch('dependency_scanner_tool.cli.SimplePackageManagerDetector'), \
         patch('dependency_scanner_tool.cli.format_scan_result'):
        
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
    
    with patch('dependency_scanner_tool.cli.DependencyScanner') as mock_scanner_class, \
         patch('dependency_scanner_tool.cli.SimpleLanguageDetector'), \
         patch('dependency_scanner_tool.cli.SimplePackageManagerDetector'), \
         patch('dependency_scanner_tool.cli.format_scan_result'):
        
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
    
    with patch('dependency_scanner_tool.cli.DependencyScanner') as mock_scanner_class, \
         patch('dependency_scanner_tool.cli.SimpleLanguageDetector'), \
         patch('dependency_scanner_tool.cli.SimplePackageManagerDetector'), \
         patch('dependency_scanner_tool.cli.DependencyClassifier') as mock_classifier_class, \
         patch('dependency_scanner_tool.cli.format_scan_result'):
        
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
    
    with patch('dependency_scanner_tool.cli.DependencyScanner') as mock_scanner_class, \
         patch('dependency_scanner_tool.cli.SimpleLanguageDetector'), \
         patch('dependency_scanner_tool.cli.SimplePackageManagerDetector'), \
         patch('dependency_scanner_tool.cli.DependencyClassifier') as mock_classifier_class, \
         patch('dependency_scanner_tool.cli.format_scan_result'):
        
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


@patch('dependency_scanner_tool.cli.DependencyScanner')
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


@patch('dependency_scanner_tool.cli.DependencyScanner')
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


def test_cli_categorization_with_config_yaml(cli_runner, tmp_path):
    """Test dependency categorization using --config option with a YAML file."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create a dummy requirements.txt with a dependency to be categorized
    req_file = project_dir / "requirements.txt"
    req_file.write_text("dep-a==1.0.0\ncommon-util==2.1.0")

    # Create a temporary config.yaml for categorization
    config_yaml_content = """
categories:
  CategoryAlpha:
    dependencies:
      - "dep-a"
    description: "Alpha category dependencies"
  GeneralUtils:
    dependencies:
      - "common-util"
    description: "General utility libraries"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_yaml_content)

    output_json_file = tmp_path / "output.json"

    # We need to mock less now, as we are testing the actual categorization logic.
    # However, the actual scanning part (finding files, parsing them) can still be mocked
    # to simplify the test and focus on categorization via CLI options.

    # Mock ScanResult to control dependencies fed into categorization
    mock_scan_result = ScanResult(
        languages={"Python": 100.0},
        package_managers={"pip"},
        dependency_files=[Path("requirements.txt")],
        dependencies=[
            Dependency(name="dep-a", version="1.0.0", source_file="requirements.txt"),
            Dependency(name="common-util", version="2.1.0", source_file="requirements.txt"),
            Dependency(name="other-dep", version="3.0.0", source_file="requirements.txt"), # Uncategorized
        ],
        errors=[]
    )

    with patch('dependency_scanner_tool.cli.DependencyScanner') as mock_scanner_class, \
         patch('dependency_scanner_tool.cli.SimpleLanguageDetector'), \
         patch('dependency_scanner_tool.cli.SimplePackageManagerDetector'):

        mock_scanner_instance = mock_scanner_class.return_value
        mock_scanner_instance.scan_project.return_value = mock_scan_result

        result = cli_runner.invoke(
            main,
            [
                str(project_dir),
                "--config", str(config_file),
                "--json-output", str(output_json_file)
            ]
        )

        assert result.exit_code == 0
        assert output_json_file.exists()

        with open(output_json_file, 'r') as f:
            json_data = f.read()
            # Debug: print JSON data if parsing fails or for inspection
            # print("Generated JSON:", json_data)
            report_data = eval(json_data) # Using eval as it's saved as Python dict string

        assert "categorized_dependencies" in report_data
        categorized_deps = report_data["categorized_dependencies"]

        assert "CategoryAlpha" in categorized_deps
        assert len(categorized_deps["CategoryAlpha"]) == 1
        assert categorized_deps["CategoryAlpha"][0]["name"] == "dep-a"

        assert "GeneralUtils" in categorized_deps
        assert len(categorized_deps["GeneralUtils"]) == 1
        assert categorized_deps["GeneralUtils"][0]["name"] == "common-util"

        # Check unified_categories as well
        assert "unified_categories" in report_data
        unified_categories = report_data["unified_categories"]

        assert "CategoryAlpha" in unified_categories
        assert len(unified_categories["CategoryAlpha"]["dependencies"]) == 1
        assert unified_categories["CategoryAlpha"]["dependencies"][0]["name"] == "dep-a"

        assert "GeneralUtils" in unified_categories
        assert len(unified_categories["GeneralUtils"]["dependencies"]) == 1
        assert unified_categories["GeneralUtils"]["dependencies"][0]["name"] == "common-util"


def test_cli_category_config_precedence(cli_runner, tmp_path):
    """Test that --category-config takes precedence over --config for categorization."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    req_file = project_dir / "requirements.txt"
    req_file.write_text("dep-b==1.0.0")

    # Config YAML (--config option)
    config_yaml_content = """
categories:
  CategoryBeta: # This should be overridden
    dependencies: ["dep-b"]
    description: "Beta category from config.yaml"
"""
    config_file_yaml = tmp_path / "config.yaml"
    config_file_yaml.write_text(config_yaml_content)

    # Custom Category JSON (--category-config option)
    # This one should take precedence
    category_json_content = """
{
  "categories": {
    "CategoryGamma": {
      "dependencies": ["dep-b"],
      "description": "Gamma category from category_config.json"
    }
  }
}
"""
    category_file_json = tmp_path / "custom_categories.json"
    category_file_json.write_text(category_json_content)

    output_json_file = tmp_path / "output.json"

    mock_scan_result = ScanResult(
        languages={"Python": 100.0},
        package_managers={"pip"},
        dependency_files=[Path("requirements.txt")],
        dependencies=[
            Dependency(name="dep-b", version="1.0.0", source_file="requirements.txt"),
        ],
        errors=[]
    )

    with patch('dependency_scanner_tool.cli.DependencyScanner') as mock_scanner_class, \
         patch('dependency_scanner_tool.cli.SimpleLanguageDetector'), \
         patch('dependency_scanner_tool.cli.SimplePackageManagerDetector'):

        mock_scanner_instance = mock_scanner_class.return_value
        mock_scanner_instance.scan_project.return_value = mock_scan_result

        result = cli_runner.invoke(
            main,
            [
                str(project_dir),
                "--config", str(config_file_yaml),
                "--category-config", str(category_file_json),
                "--json-output", str(output_json_file)
            ]
        )

        assert result.exit_code == 0, f"CLI command failed: {result.output}"
        assert output_json_file.exists()

        with open(output_json_file, 'r') as f:
            json_text = f.read()
            # Use json.loads instead of eval
            report_data = json.loads(json_text)

        assert "categorized_dependencies" in report_data
        categorized_deps = report_data["categorized_dependencies"]

        assert "CategoryGamma" in categorized_deps, "CategoryGamma (from --category-config) should be present"
        assert "CategoryBeta" not in categorized_deps, "CategoryBeta (from --config) should NOT be present due to precedence"

        assert len(categorized_deps["CategoryGamma"]) == 1
        assert categorized_deps["CategoryGamma"][0]["name"] == "dep-b"

        # Check unified_categories as well
        assert "unified_categories" in report_data
        unified_categories = report_data["unified_categories"]

        assert "CategoryGamma" in unified_categories
        assert "CategoryBeta" not in unified_categories
        assert len(unified_categories["CategoryGamma"]["dependencies"]) == 1
        assert unified_categories["CategoryGamma"]["dependencies"][0]["name"] == "dep-b"
