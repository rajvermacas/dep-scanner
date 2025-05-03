# Dependency Scanner - Workflow and Execution Flow

This document describes the execution flow of the Dependency Scanner application, including the key entities in the system and how they interact to produce the final output.

## System Overview

The Dependency Scanner is a tool designed to analyze software projects and identify their dependencies. It scans project files, detects programming languages, package managers, and extracts dependencies from various file formats.

## Key Entities

### 1. Scanner Core Components

- **ProjectScanner**: The main orchestrator that coordinates the entire scanning process
- **LanguageDetector**: Detects programming languages used in the project
- **PackageManagerDetector**: Identifies package managers used in the project
- **DependencyClassifier**: Classifies dependencies as allowed, restricted, or unknown

### 2. File Handling Components

- **FileTypeDetector**: Identifies file types based on extensions and content patterns
- **FileUtils**: Utilities for file operations and directory traversal

### 3. Parser System

- **ParserRegistry**: Central registry for all dependency file parsers
- **DependencyParser**: Base interface for all parsers
- **ParserManager**: Manages and coordinates all parsers
- **Specific Parsers**:
  - **RequirementsTxtParser**: Parses Python requirements.txt files
  - **PyprojectTomlParser**: Parses Python pyproject.toml files
  - **BuildSbtParser**: Parses Scala build.sbt files
  - *(More parsers to be added for other languages)*

### 4. Import Analysis System

- **ImportAnalyzerRegistry**: Central registry for all import analyzers
- **ImportAnalyzer**: Base interface for all import analyzers
- **AnalyzerManager**: Manages and coordinates all import analyzers
- **Specific Analyzers**:
  - **PythonImportAnalyzer**: Analyzes Python import statements
  - *(More analyzers to be added for other languages)*

### 5. Data Models

- **Dependency**: Represents a single project dependency
- **DependencyType**: Enum for dependency classification (allowed, restricted, unknown)
- **ScanResult**: Contains the complete results of a project scan

## Execution Flow

### 1. Initialization

1. The application starts with the creation of a `ProjectScanner` instance
2. The scanner initializes its components:
   - Language detector
   - Package manager detector
   - Parser manager (which loads all registered parsers)
   - Analyzer manager (which loads all registered import analyzers)
   - Dependency classifier

### 2. Project Scanning

When a project scan is initiated:

1. The user provides a project directory path to scan
2. The `ProjectScanner.scan_project()` method is called with this path

### 3. Language Detection

1. The scanner uses the `LanguageDetector` to identify programming languages in the project
2. Files are examined based on extensions and content patterns
3. A dictionary of languages with their usage percentages is generated

### 4. Package Manager Detection

1. The scanner uses the `PackageManagerDetector` to identify package managers
2. Package manager configuration files are detected
3. A set of detected package managers is generated

### 5. Dependency File Parsing

1. The scanner finds dependency files using the `_find_dependency_files()` method
2. For each dependency file:
   - The appropriate parser is selected using `ParserManager.get_parser_for_file()`
   - The file is parsed using `ParserManager.parse_file()`
   - Dependencies are extracted and added to the results

### 6. Import Analysis

1. The scanner finds source code files using the `_find_source_files()` method
2. For each source file:
   - The appropriate analyzer is selected using `AnalyzerManager.get_analyzer_for_file()`
   - The file is analyzed using `AnalyzerManager.analyze_file()`
   - Dependencies from imports are extracted and added to the results

### 7. Result Generation

1. All collected data is assembled into a `ScanResult` object containing:
   - Detected languages
   - Detected package managers
   - Found dependency files
   - Extracted dependencies
   - Any errors encountered during scanning
2. A summary of the scan is logged
3. The `ScanResult` is returned to the caller

## Data Flow Diagram

```
User Input (Project Path)
       │
       ▼
┌─────────────────┐
│  ProjectScanner │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│                                                 │
│  ┌───────────────┐    ┌────────────────────┐    │
│  │LanguageDetector│───▶│Detected Languages │    │
│  └───────────────┘    └────────────────────┘    │
│                                                 │
│  ┌────────────────────┐    ┌───────────────┐    │
│  │PackageManagerDetector│──▶│Package Managers│   │
│  └────────────────────┘    └───────────────┘    │
│                                                 │
│  ┌──────────────┐    ┌───────────────────┐      │
│  │ParserManager │───▶│Dependency Files   │      │
│  └──────┬───────┘    └─────────┬─────────┘      │
│         │                      │                │
│         ▼                      ▼                │
│  ┌──────────────┐    ┌───────────────────┐      │
│  │File Parsers  │───▶│Dependencies       │      │
│  └──────────────┘    └─────────┬─────────┘      │
│                                │                │
│  ┌──────────────┐              │                │
│  │AnalyzerManager│             │                │
│  └──────┬───────┘              │                │
│         │                      │                │
│         ▼                      │                │
│  ┌──────────────┐              │                │
│  │Import Analyzers│────────────┘                │
│  └──────────────┘                               │
│                                                 │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
               ┌─────────────┐
               │ ScanResult  │
               └──────┬──────┘
                      │
                      ▼
             Final Output to User
```

## Example Workflow

1. User runs: `dep-scanner scan /path/to/project`
2. The CLI creates a `ProjectScanner` and calls `scan_project()`
3. The scanner detects languages (e.g., Python 70%, JavaScript 30%)
4. The scanner detects package managers (e.g., pip, npm)
5. The scanner finds dependency files:
   - requirements.txt
   - pyproject.toml
   - package.json
6. Each file is parsed by the appropriate parser:
   - RequirementsTxtParser parses requirements.txt
   - PyprojectTomlParser parses pyproject.toml
   - (Future) PackageJsonParser would parse package.json
7. Source files are analyzed for imports:
   - PythonImportAnalyzer analyzes .py files
   - (Future) JavaScriptImportAnalyzer would analyze .js files
8. All dependencies are collected and classified
9. A `ScanResult` is generated and returned to the user

## CLI Options

The dependency scanner provides several command-line options to customize the scanning process:

```
Usage: dep-scanner [OPTIONS] PROJECT_PATH

  Scan a project directory for dependencies and classify them.

  PROJECT_PATH is the root directory of the project to scan.

Options:
  -c, --config FILE               Path to configuration file
  -o, --output-format [text|json] Output format for results
  --analyze-imports / --no-analyze-imports
                                  Whether to analyze import statements in
                                  source code
  --extract-pip / --no-extract-pip
                                  Whether to extract pip dependencies from the
                                  current environment
  --venv DIRECTORY                Path to virtual environment to analyze
  --exclude TEXT                  Patterns or directories to exclude from
                                  scanning (can be specified multiple times)
  --allow TEXT                    Dependencies to mark as allowed (can be
                                  specified multiple times)
  --restrict TEXT                 Dependencies to mark as restricted (can be
                                  specified multiple times)
  --help                          Show this message and exit.
```

### Excluding Directories and Files

You can exclude specific directories, files, or patterns from being scanned using the `--exclude` option:

```bash
# Exclude a specific directory
dep-scanner scan /path/to/project --exclude "node_modules"

# Exclude multiple directories
dep-scanner scan /path/to/project --exclude "node_modules" --exclude ".venv" --exclude "build"

# Use glob patterns
dep-scanner scan /path/to/project --exclude "*.pyc" --exclude "__pycache__"
```

The exclude patterns work with:
- Directory names (e.g., "node_modules")
- File patterns (e.g., "*.pyc")
- Relative paths (e.g., "tests/fixtures/*")

You can also specify exclude patterns in your configuration file:

```yaml
ignore_patterns:
  - "node_modules"
  - "*.pyc"
  - "__pycache__"
  - "tests/fixtures/*"
```

### Classifying Dependencies

You can classify dependencies as "allowed" or "restricted" using the `--allow` and `--restrict` options:

```bash
# Mark specific dependencies as allowed
dep-scanner scan /path/to/project --allow "requests" --allow "flask"

# Mark specific dependencies as restricted
dep-scanner scan /path/to/project --restrict "insecure-package" --restrict "deprecated-library"

# Combine allow and restrict options
dep-scanner scan /path/to/project --allow "requests" --restrict "insecure-package"
```

You can also specify allowed and restricted dependencies in your configuration file:

```yaml
allowed_dependencies:
  - "requests"
  - "pytest"
  - "flask"

restricted_dependencies:
  - "insecure-package"
  - "deprecated-library"
```

Dependencies specified via the command line are combined with those in the configuration file.

## Error Handling

Throughout the process, errors are caught and logged:
- File access errors
- Parsing errors
- Analysis errors

These errors are included in the final `ScanResult` but don't stop the scanning process, allowing for partial results even when some files can't be processed.
