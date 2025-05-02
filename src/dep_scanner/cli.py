"""Command-line interface for the dependency scanner."""

import sys
from pathlib import Path

import click
import yaml



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
    # TODO: Implement different output formats
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
def main(project_path: Path, config: Path, output_format: str):
    """Scan a project directory for dependencies and classify them.
    
    PROJECT_PATH is the root directory of the project to scan.
    """
    # Load configuration
    if config:
        load_configuration(config)
    
    # TODO: Initialize scanner components based on configuration
    click.echo("Scanning project...")
    
    # TODO: Implement actual scanning logic
    click.echo("Not yet implemented")
    sys.exit(1)


if __name__ == "__main__":
    main()