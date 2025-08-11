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
.venv/bin/python -m dependency_scanner_tool /path/to/project

# Full project scan with HTML output (development testing)
.venv/bin/python "src/dependency_scanner_tool/__main__.py" "." --exclude ".venv" --exclude ".venv-win" --exclude "*_cache" --exclude ".pyc" --html-output "public/index.html" --config "config.yaml"

# Serve HTML report locally
.venv/bin/python -m http.server 9871 -d public

# REST API server
python -m src.dependency_scanner_tool.api.main
```

### PyPI Deployment
```bash
# Build and deploy
.venv/bin/python -m build
.venv/bin/python -m twine upload dist/*
```

## Core Architecture

This is a **registry-based plugin system** for multi-language dependency scanning. The architecture uses three key registries that manage language-specific components:

### Registry Pattern (Central to Understanding the Codebase)

1. **ParserRegistry** (`parsers/base.py`): Maps file patterns to parsers
   - `requirements.txt` → `RequirementsTxtParser`
   - `pom.xml` → `MavenPomParser`  
   - `build.gradle` → `GradleBuildParser`

2. **ImportAnalyzerRegistry** (`analyzers/base.py`): Maps file extensions to analyzers
   - `.py` → `PythonImportAnalyzer`
   - `.java` → `JavaImportAnalyzer`
   - `.scala` → `ScalaImportAnalyzer`

3. **ApiCallAnalyzerRegistry** (`api_analyzers/registry.py`): Maps languages to API analyzers
   - `python` → `PythonApiCallAnalyzer`
   - `scala` → `ScalaApiCallAnalyzer`

### Data Flow

```
Project Path → DependencyScanner → ParserManager → Individual Parsers → Dependencies
                                ↓
                               AnalyzerManager → Import Analyzers → More Dependencies  
                                ↓
                               ApiCallAnalyzerManager → API Analyzers → API Calls
                                ↓
                               ScanResult (dependencies + API calls + metadata)
```

### Key Extension Points

**Adding New Language Support:**
1. Create parser class inheriting from `DependencyParser` in `parsers/`
2. Register with `@ParserRegistry.register(pattern, extensions)`
3. Create analyzer class inheriting from `ImportAnalyzer` in `analyzers/`
4. Register with `@ImportAnalyzerRegistry.register(extensions)`
5. Add normalizer in `normalizers/` for package name mapping if needed
6. Create API analyzer in `api_analyzers/` if API call detection needed

### Package Name Normalization

Critical for cross-language dependency matching:
- **PythonPackageNormalizer**: `beautifulsoup4` ↔ `bs4`, `scikit-learn` ↔ `sklearn`
- **JavaPackageNormalizer**: Package names ↔ Maven coordinates

### REST API Architecture

- **FastAPI server** (`api/main.py`) with async job processing
- **JobManager** handles background scanning tasks
- **Client CLI** (`client_cli.py`) with GitLab group scanning support
- **Repository caching** for efficient re-scanning

### Testing Strategy

- **TDD approach** - tests first, implementation second
- **Component isolation** - mock external dependencies extensively  
- **Test data** in `tests/test_data/` with realistic project structures
- **Integration tests** verify complete scanning workflows
- **43 test files** covering all major components and edge cases