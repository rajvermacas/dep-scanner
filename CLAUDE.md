# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Testing
```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=src/dependency_scanner_tool

# Run specific test file
python -m pytest tests/test_scanner.py

# Run tests matching pattern
python -m pytest -k "test_python"
```

### Code Quality
```bash
# Lint code
python -m ruff check src tests

# Format code  
python -m black src tests

# Type checking
python -m mypy src/dependency_scanner_tool
```

### Running the Application
```bash
# Basic project scan
python -m dependency_scanner_tool /path/to/project

# Scan with configuration
python -m dependency_scanner_tool /path/to/project --config config.yaml

# Generate JSON report
python -m dependency_scanner_tool /path/to/project --json-output results.json

# Generate HTML report
python -m dependency_scanner_tool /path/to/project --html-output report.html

# Using CLI interface
python -m dependency_scanner_tool.cli scan /path/to/project

# Full project scan with detailed options
.venv/bin/python "src/dependency_scanner_tool/__main__.py" "." --exclude ".venv" --exclude ".venv-win" --exclude "*_cache" --exclude ".pyc" --html-output "dependency-report.html" --category-config "sample_categories.json" --config "config.yaml"
```

### Installation
```bash
# Development installation
pip install -e .

# With development dependencies
pip install -e .[dev]
```

## Architecture Overview

This is a multi-language dependency scanner tool that analyzes projects to identify dependencies and classify them based on configurable allow/restrict lists.

### Core Components

- **DependencyScanner** (`scanner.py`): Main orchestrator that coordinates the scanning process
- **ParserManager** (`parsers/parser_manager.py`): Manages language-specific dependency file parsers
- **AnalyzerManager** (`analyzers/analyzer_manager.py`): Manages source code import analyzers
- **ApiCallAnalyzerManager** (`api_analyzers/registry.py`): Manages API call detection in source code

### Plugin Architecture

The tool uses a registry-based plugin system:

1. **Parsers** (`parsers/`): Parse dependency files (requirements.txt, pom.xml, build.gradle, etc.)
2. **Analyzers** (`analyzers/`): Analyze source code imports (Python, Java)
3. **API Analyzers** (`api_analyzers/`): Detect and categorize API calls in source code
4. **Normalizers** (`normalizers/`): Handle package name variations between languages
5. **Reporters** (`reporters/`): Generate output in different formats (JSON, HTML)

### Supported Languages & Package Managers

- **Python**: requirements.txt, pyproject.toml, pip, conda
- **Java**: Maven (pom.xml), Gradle (build.gradle, build.gradle.kts)
- **Scala**: SBT (build.sbt)

### Key Data Models

- **Dependency**: Represents a package dependency with name, version, and source
- **ApiCall**: Represents an API call with URL, method, and classification
- **ScanResult**: Contains complete scan results including dependencies, API calls, and errors

### Configuration

The tool supports YAML configuration files with:
- `allowed_dependencies`/`restricted_dependencies`: For dependency classification
- `api_dependency_patterns`: For API URL classification and categorization
- `ignore_patterns`: Files/directories to skip during scanning

### Extension Points

To add support for new languages:

1. Create parser in `parsers/` inheriting from `DependencyParser`
2. Register with `ParserRegistry.register()`
3. Create analyzer in `analyzers/` inheriting from `ImportAnalyzer` 
4. Register with `ImportAnalyzerRegistry.register()`
5. Add normalizer in `normalizers/` if needed for package name mapping
6. Add tests following existing patterns

### Testing Strategy

- Unit tests for individual components
- Integration tests for parsers and analyzers  
- End-to-end tests for complete scanning workflow
- Test data in `tests/test_data/`
- Use `conftest.py` for pytest configuration and shared fixtures

The codebase follows TDD principles with comprehensive test coverage across all major components.