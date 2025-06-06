# Dependency Scanner - Workflow and Execution Flow

This document describes the execution flow of the Dependency Scanner application, including the key entities in the system and how they interact to produce the final output.

## System Overview

The Dependency Scanner is a tool designed to analyze software projects and identify their dependencies. It scans project files, detects programming languages, package managers, and extracts dependencies from various file formats.

## Installation

### From PyPI

You can install the package directly from PyPI:

```bash
pip install dependency-scanner-tool
```

### From Source

Clone the repository and install from source:

```bash
git clone https://github.com/rajvermacas/dep-scanner.git
cd dep-scanner
pip install -e .
```

## Key Entities

### 1. Scanner Core Components

- **ProjectScanner**: The main orchestrator that coordinates the entire scanning process
- **LanguageDetector**: Detects programming languages used in the project
- **PackageManagerDetector**: Identifies package managers used in the project
- **DependencyClassifier**: Classifies dependencies as allowed, restricted, or unknown
- **DependencyCategorizer**: Categorizes dependencies into configurable groups based on names

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
  - **PomXmlParser**: Parses Java Maven pom.xml files
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
- **DependencyCategory**: Represents a group of dependencies with similar characteristics

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

## Supported Dependency Files

The dependency scanner currently supports the following dependency file formats:

### Python
- `requirements.txt`: Standard Python requirements file
- `pyproject.toml`: Modern Python project configuration (PEP 518)
- `pip` installed packages: Extracts dependencies from the current Python environment
- `conda environment.yml`: Conda environment configuration file

### Java
- `pom.xml`: Maven project configuration file

### Scala
- `build.sbt`: Scala SBT build configuration

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

## Advanced Features

### Java Support

The dependency scanner now provides comprehensive support for Java projects with the following features:

#### Maven POM Support

The scanner supports analyzing Java Maven projects by parsing `pom.xml` files. The Maven parser extracts dependencies with the following features:

- **Basic Dependency Extraction**: Extracts `groupId`, `artifactId`, and `version` information from dependency declarations
- **Property Resolution**: Resolves property references like `${junit.version}` using values defined in the `<properties>` section
- **Parent POM Detection**: Identifies parent POM references and includes them as dependencies
- **Namespace Handling**: Properly handles XML namespaces in Maven POM files

Example Maven dependency in a pom.xml file:

```xml
<dependencies>
  <dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.12</version>
    <scope>test</scope>
  </dependency>
  <dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-lang3</artifactId>
    <version>${commons.version}</version>
  </dependency>
</dependencies>
```

#### Gradle Build Support

The scanner also supports analyzing Java Gradle projects by parsing `build.gradle` and `build.gradle.kts` files. The Gradle parser extracts dependencies from both Groovy DSL and Kotlin DSL formats:

- **Multiple Notation Support**: Handles string notation (`'group:artifact:version'`) and map notation (`group: 'group', name: 'artifact', version: 'version'`)
- **Configuration Support**: Recognizes different dependency configurations like `implementation`, `api`, `compileOnly`, `runtimeOnly`, and `testImplementation`
- **Kotlin DSL Support**: Parses both Groovy and Kotlin DSL syntax

Example Gradle dependencies:

```groovy
// Groovy DSL (build.gradle)
dependencies {
    // String notation
    implementation 'org.springframework.boot:spring-boot-starter-web:2.5.0'
    
    // Map notation
    implementation group: 'com.google.guava', name: 'guava', version: '30.1-jre'
    
    // Different configurations
    api 'com.fasterxml.jackson.core:jackson-databind:2.12.3'
    testImplementation 'junit:junit:4.13.2'
}
```

```kotlin
// Kotlin DSL (build.gradle.kts)
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web:2.5.0")
    implementation(group = "com.google.guava", name = "guava", version = "30.1-jre")
    testImplementation("junit:junit:4.13.2")
}
```

#### Java Import Analysis

The scanner can analyze Java source files to extract import statements and map them to Maven dependencies:

- **Import Statement Extraction**: Extracts standard imports, static imports, and wildcard imports
- **Standard Library Filtering**: Ignores Java standard library imports (those starting with `java.` or `javax.`)
- **Maven Coordinate Mapping**: Maps Java package names to Maven coordinates (e.g., `org.springframework.boot` → `org.springframework.boot:spring-boot`)

#### Java Package Name Normalization

The scanner handles Java package naming conventions, mapping between Java package names and Maven coordinates:

- **Package to Artifact Mapping**: Maps Java package names to Maven coordinates
- **Artifact to Package Mapping**: Maps Maven coordinates to Java package names
- **Standard Library Detection**: Identifies packages that are part of the Java standard library

When using the dependency scanner with Java projects, you can use the same classification features to mark dependencies as allowed or restricted:

```yaml
# config.yaml
allowed_dependencies:
  - junit:junit
  - org.springframework.boot:spring-boot
  - com.google.guava:guava

restricted_dependencies:
  - com.insecure:vulnerable-library
```

```bash
# Command line
dep-scanner /path/to/java/project --allow "junit:junit" --restrict "com.insecure:vulnerable-library"
```

### Python Package Name Normalization

The dependency scanner now supports Python package naming conventions, handling the inconsistencies between how packages are imported and how they're specified in dependency files. This is particularly useful when classifying dependencies as allowed or restricted.

Examples of supported naming conventions:

| Import Name | PyPI Name | Notes |
|-------------|-----------|-------|
| `bs4` | `beautifulsoup4` | Different names |
| `PIL` | `pillow` | Different names |
| `sklearn` | `scikit-learn` | Different names |
| `scikit_learn` | `scikit-learn` | Underscore vs. hyphen |
| `Django` | `django` | Case insensitivity |
| `google.cloud` | `google-cloud` | Namespace packages |

When you specify allowed or restricted dependencies, the scanner will automatically handle these naming conventions. For example, if you allow `beautifulsoup4`, the scanner will also recognize imports of `bs4` as allowed.

```bash
# Both of these will match imports of "bs4" and "beautifulsoup4"
dep-scanner /path/to/project --allow beautifulsoup4
dep-scanner /path/to/project --allow bs4
```

You can also specify these in your configuration file:

```yaml
allowed_dependencies:
  - beautifulsoup4  # Will also match imports of "bs4"
  - scikit-learn    # Will also match imports of "sklearn"

restricted_dependencies:
  - pillow          # Will also match imports of "PIL"
  - python-dotenv   # Will also match imports of "dotenv"
```

This feature makes it easier to manage dependencies without having to worry about the different naming conventions used in Python packages.

## CLI Options

The dependency scanner provides the following command-line options:

```
Usage: dep-scanner [OPTIONS] PROJECT_PATH

  Scan a project directory for dependencies and classify them.

  PROJECT_PATH is the root directory of the project to scan.

Options:
  -c, --config PATH               Path to configuration file
  -o, --output-format [text|json]
                                  Output format for results
  --json-output PATH              Path to save JSON output (implies --output-format=json)
  --html-output PATH              Path to save HTML report (implies generating JSON output)
  --html-template PATH            Path to custom HTML template for report generation
  --analyze-imports / --no-analyze-imports
                                  Whether to analyze import statements in source code
  --extract-pip / --no-extract-pip
                                  Whether to extract pip dependencies from the current environment
  --venv PATH                     Path to virtual environment to analyze
  --conda-env PATH                Path to conda environment.yml file to analyze
  --category-config PATH          Path to JSON file containing dependency category definitions
  --exclude TEXT                  Patterns to exclude from scanning (can be used multiple times)
  --allow TEXT                    Dependencies to mark as allowed (can be used multiple times)
  --restrict TEXT                 Dependencies to mark as restricted (can be used multiple times)
  --help                          Show this message and exit.
```

### Using Virtual Environments

You can analyze dependencies in a virtual environment by using the `--venv` option:

```bash
dep-scanner /path/to/project --venv /path/to/venv
```

This will extract all packages installed in the virtual environment using pip.

### Using Conda Environments

You can analyze dependencies in a conda environment by using the `--conda-env` option:

```bash
dep-scanner /path/to/project --conda-env /path/to/environment.yml
```

This will extract all packages defined in the conda environment file, including both conda packages and pip packages (if specified in the `pip:` section).

Example conda environment file:

```yaml
name: myenv
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - numpy=1.21.0
  - pandas>=1.3.0
  - matplotlib
  - pip
  - pip:
    - requests>=2.25.0
    - flask
```

The scanner will extract all dependencies from this file, including both conda packages (python, numpy, pandas, matplotlib) and pip packages (requests, flask).

### Combining Multiple Sources

You can combine multiple sources of dependencies by using multiple options:

```bash
dep-scanner /path/to/project --venv /path/to/venv --conda-env /path/to/environment.yml
```

This will extract dependencies from:
1. Project dependency files (requirements.txt, pyproject.toml, etc.)
2. Import statements in source code
3. Packages installed in the virtual environment
4. Packages defined in the conda environment file

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

### Using a Configuration File

To use a configuration file, you can pass the path to the file using the `--config` option:

```bash
# Use a configuration file
dep-scanner scan /path/to/project --config config.yaml

# Combine configuration file with command-line options
dep-scanner scan /path/to/project --config config.yaml --allow "additional-package" --restrict "another-bad-package"
```

The configuration file should be in YAML format and contain the following keys:

```yaml
allowed_dependencies:
  - "requests"
  - "pytest"
  - "flask"

restricted_dependencies:
  - "insecure-package"
  - "deprecated-library"

ignore_patterns:
  - "node_modules"
  - "*.pyc"
  - "__pycache__"
  - "tests/fixtures/*"
```

## Reporting Features

The dependency scanner can generate reports in different formats to help you visualize and analyze the scan results.

### JSON Output

You can generate JSON output using the `--output-format=json` option:

```bash
dep-scanner /path/to/project --output-format=json
```

To save the JSON output to a file, use the `--json-output` option:

```bash
dep-scanner /path/to/project --json-output=scan-results.json
```

The JSON output includes detailed information about detected languages, package managers, dependencies, and any errors encountered during the scan.

### HTML Reports

You can generate an HTML report directly from a scan using the `--html-output` option:

```bash
dep-scanner /path/to/project --html-output=report.html
```

You can also generate an HTML report from an existing JSON file using the dedicated HTML report generator:

```bash
python -m dependency_scanner_tool.html_report scan-results.json -o report.html
```

The HTML report provides a visual representation of the scan results, including:
- Summary statistics (number of dependencies, languages, package managers)
- Language breakdown with visualization
- List of detected package managers
- Detailed dependency information with classification status
- Any errors encountered during the scan

#### Customizing HTML Reports

You can customize the HTML report by providing your own template:

```bash
python -m dependency_scanner_tool.html_report scan-results.json -o report.html --template custom-template.html
```

The template should be a valid Jinja2 template. See the default template in `src/dependency_scanner_tool/reporters/templates/report.html` for reference.

## GitLab CI Integration

The dependency scanner can be integrated into GitLab CI pipelines to automatically scan projects and generate reports.

### Setup

1. Add the `.gitlab-ci.yml` file to your project root directory:

```bash
cp /path/to/dependency_scanner_tool/ci/.gitlab-ci.yml /path/to/your/project/
```

2. Commit and push the file to your GitLab repository:

```bash
git add .gitlab-ci.yml
git commit -m "Add dependency scanner CI configuration"
git push
```

### Pipeline Stages

The default pipeline includes the following stages:

1. **Setup**: Install dependencies
2. **Scan**: Run the dependency scanner and output JSON
3. **Report**: Generate HTML report from JSON
4. **Deploy**: Deploy the report to GitLab Pages

### Accessing the Report

Once deployed, the HTML report will be available at:

```
https://<username>.gitlab.io/<project-name>/
```

### Customizing the Pipeline

You can customize the pipeline by modifying the `.gitlab-ci.yml` file. For example, to scan only specific directories:

```yaml
scan:
  stage: scan
  script:
    - python -m dependency_scanner_tool "$CI_PROJECT_DIR/src" --analyze-imports --json-output="$CI_PROJECT_DIR/scan-results.json"
```

Or to add custom allowed/restricted dependencies:

```yaml
scan:
  stage: scan
  script:
    - python -m dependency_scanner_tool "$CI_PROJECT_DIR" --allow="requests" --restrict="flask<2.0.0" --json-output="$CI_PROJECT_DIR/scan-results.json"
```

For more information on the reporting features and GitLab CI integration, see the [Reporting Guide](docs/reporting.md).

## Dependency Categorization

The dependency scanner supports categorizing dependencies into configurable groups based on their names. This feature helps identify the usage of certain technologies in your project based on the presence of their dependencies.

### Configuration

To use dependency categorization, create a JSON configuration file with the following structure:

```json
{
  "categories": {
    "Web Frameworks": ["flask", "django", "fastapi", "bottle"],
    "Data Science": ["numpy", "pandas", "scipy", "matplotlib"],
    "Machine Learning": ["tensorflow", "pytorch", "scikit-learn", "keras"]
  }
}
```

Each category is defined by a name and a list of dependency names that belong to that category. Dependencies can belong to multiple categories if needed.

### Usage

To use dependency categorization, provide the path to your category configuration file using the `--category-config` option:

```bash
dep-scanner /path/to/project --category-config=categories.json
```

This will add a "Categorized Dependencies" section to the output, showing dependencies grouped by category.

### Reports

When using the `--json-output` or `--html-output` options with a category configuration, the reports will include the categorized dependencies:

```bash
dep-scanner /path/to/project --category-config=categories.json --html-output=report.html
```

The HTML report will include a new section showing dependencies grouped by their categories, making it easier to identify the types of technologies used in your project.

### Default Category

Dependencies that don't match any category in your configuration will be placed in an "Uncategorized" category by default.

### Multiple Categories

If a dependency matches multiple categories, it will appear in all matching categories in the reports.

## Error Handling

Throughout the process, errors are caught and logged:
- File access errors
- Parsing errors
- Analysis errors

These errors are included in the final `ScanResult` but don't stop the scanning process, allowing for partial results even when some files can't be processed.
