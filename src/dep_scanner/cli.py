"""Command-line interface for the dependency scanner."""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Set

import click
import yaml

from dep_scanner.scanner import (
    DependencyScanner,
    DependencyClassifier
)



def load_configuration(config_path: Path) -> dict:
    """Load scanner configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing configuration settings
    """
    try:
        with config_path.open() as f:
            return yaml.safe_load(f)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)


def format_scan_result(result, output_format="text"):
    """Format scan results for output.
    
    Args:
        result: ScanResult object
        output_format: Desired output format (text/json)
        
    Returns:
        Formatted string containing the results
    """
    if output_format == "json":
        # Convert to dictionary and then to JSON
        result_dict = {
            "languages": {k: float(v) for k, v in result.languages.items()},
            "package_managers": list(result.package_managers),
            "dependency_files": [str(df) for df in result.dependency_files],
            "dependencies": [
                {
                    "name": dep.name,
                    "version": dep.version,
                    "source_file": dep.source_file,
                    "type": dep.dependency_type.value
                } for dep in result.dependencies
            ],
            "errors": result.errors
        }
        return json.dumps(result_dict, indent=2)
    else:
        # Text format
        lines = [
            "=== Dependency Scanner Results ===",
            "",
            "Languages Detected:",
        ]
        
        for lang, percentage in result.languages.items():
            lines.append(f"  - {lang}: {percentage:.1f}%")
        
        lines.extend([
            "",
            "Package Managers:",
            *[f"  - {pm}" for pm in sorted(result.package_managers)],
            "",
            "Dependency Files:",
            *[f"  - {df}" for df in result.dependency_files],
            "",
            "Dependencies:",
        ])
        
        for dep in result.dependencies:
            status = dep.dependency_type.value.upper()
            version = f" ({dep.version})" if dep.version else ""
            source = f" from {dep.source_file}" if dep.source_file else ""
            lines.append(f"  - {dep.name}{version} [{status}]{source}")
        
        if result.errors:
            lines.extend([
                "",
                "Errors:",
                *[f"  - {error}" for error in result.errors],
            ])
        
        return "\n".join(lines)


@click.command()
@click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "-o",
    "--output-format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format for results",
)
@click.option(
    "--analyze-imports/--no-analyze-imports",
    default=True,
    help="Whether to analyze import statements in source code",
)
@click.option(
    "--extract-pip/--no-extract-pip",
    default=True,
    help="Whether to extract pip dependencies from the current environment",
)
@click.option(
    "--venv",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to virtual environment to analyze",
)
@click.option(
    "--conda-env",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to conda environment file (environment.yml) to analyze",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Patterns or directories to exclude from scanning (can be specified multiple times)",
)
@click.option(
    "--allow",
    multiple=True,
    help="Dependencies to mark as allowed (can be specified multiple times)",
)
@click.option(
    "--restrict",
    multiple=True,
    help="Dependencies to mark as restricted (can be specified multiple times)",
)
def main(project_path: Path, config: Path, output_format: str, analyze_imports: bool, extract_pip: bool, venv: Path, conda_env: Path, exclude: List[str], allow: List[str], restrict: List[str]):
    """Scan a project directory for dependencies and classify them.
    
    PROJECT_PATH is the root directory of the project to scan.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load configuration
    config_data = {}
    if config:
        config_data = load_configuration(config)
    
    # Initialize scanner components
    click.echo(f"Scanning project: {project_path}")
    
    # Create a simple language detector
    language_detector = SimpleLanguageDetector()
    
    # Create a simple package manager detector
    package_manager_detector = SimplePackageManagerDetector()
    
    # Combine allowed and restricted dependencies from config and CLI
    allowed_list = set(config_data.get("allowed_dependencies", []) or [])
    allowed_list.update(allow)
    
    restricted_list = set(config_data.get("restricted_dependencies", []) or [])
    restricted_list.update(restrict)
    
    # Create the project scanner
    scanner = DependencyScanner(
        language_detector=language_detector,
        package_manager_detector=package_manager_detector,
        ignore_patterns=config_data.get("ignore_patterns", []) + list(exclude)
    )
    
    # Perform the scan
    try:
        result = scanner.scan_project(
            project_path=str(project_path),
            analyze_imports=analyze_imports,
            extract_pip_deps=extract_pip,
            venv_path=venv,
            conda_env_path=conda_env
        )
        
        # Classify dependencies using the classifier
        if allowed_list or restricted_list:
            dependency_classifier = DependencyClassifier(allowed_list, restricted_list)
            for dependency in result.dependencies:
                dependency.dependency_type = dependency_classifier.classify_dependency(dependency)
        
        # Format and display the results
        formatted_result = format_scan_result(result, output_format)
        click.echo(formatted_result)
    except Exception as e:
        click.echo(f"Error scanning project: {e}", err=True)
        sys.exit(1)


# Simple language detector implementation
class SimpleLanguageDetector:
    """Simple implementation of language detection based on file extensions."""
    
    def detect_languages(self, project_path: Path) -> Dict[str, float]:
        """Detect programming languages used in the project.
        
        Args:
            project_path: Root directory of the project
            
        Returns:
            Dictionary mapping language names to their usage percentage
        """
        # Map of file extensions to languages
        extension_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".scala": "Scala",
            ".rb": "Ruby",
            ".go": "Go",
            ".php": "PHP",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#",
            ".html": "HTML",
            ".css": "CSS",
            ".md": "Markdown",
            ".json": "JSON",
            ".xml": "XML",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".sh": "Shell",
            ".bat": "Batch",
            ".ps1": "PowerShell",
        }
        
        # Count files by extension
        extension_counts = {}
        total_files = 0
        
        for file_path in project_path.glob("**/*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in extension_map:
                    lang = extension_map[ext]
                    extension_counts[lang] = extension_counts.get(lang, 0) + 1
                    total_files += 1
        
        # Calculate percentages
        if total_files == 0:
            return {}
            
        return {lang: round((count / total_files) * 100, 2) for lang, count in extension_counts.items()}


# Simple package manager detector implementation
class SimplePackageManagerDetector:
    """Simple implementation of package manager detection based on common files."""
    
    def detect_package_managers(self, project_path: Path) -> Set[str]:
        """Detect package managers used in the project.
        
        Args:
            project_path: Root directory of the project
            
        Returns:
            Set of detected package manager names
        """
        # Map of files to package managers
        package_manager_files = {
            "requirements.txt": "pip",
            "pyproject.toml": "pip",
            "setup.py": "pip",
            "Pipfile": "pipenv",
            "environment.yml": "conda",
            "package.json": "npm",
            "yarn.lock": "yarn",
            "pom.xml": "maven",
            "build.gradle": "gradle",
            "build.sbt": "sbt",
            "Gemfile": "bundler",
            "go.mod": "go",
            "composer.json": "composer",
        }
        
        package_managers = set()
        
        for file_name, manager in package_manager_files.items():
            if (project_path / file_name).exists():
                package_managers.add(manager)
                
        return package_managers


if __name__ == "__main__":
    main()