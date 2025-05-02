# Dependency Scanner - Product Requirements Document (PRD)

## 1. Introduction/Overview
The Dependency Scanner is a Python application designed to analyze software project directories and identify their key characteristics, focusing on programming languages and dependencies. Its primary purpose is to help development teams, security professionals, and compliance officers maintain better visibility and control over project dependencies by automatically scanning codebases and classifying dependencies against predefined lists.

## 2. Goals/Objectives
- Automate the process of dependency identification and classification across multiple programming languages
- Improve project security posture through systematic dependency tracking
- Provide clear visibility into project technology stacks
- Enable compliance monitoring through dependency classification
- Reduce manual effort in dependency auditing

## 3. Target Audience
- Software Developers and Development Teams
- Security Engineers and Security Teams
- Compliance Officers
- Engineering Managers
- DevOps Engineers

## 4. Functional Requirements

### FR1: Project Scanning
- Accept a directory path as input
- Recursively scan all files and subdirectories
- Handle various file encodings appropriately
- Ignore common non-relevant directories (e.g., .git, node_modules, __pycache__)

### FR2: Language Detection
- Analyze file extensions and content patterns
- Support multiple programming languages including:
  - Python (.py)
  - Java (.java)
  - JavaScript/TypeScript (.js, .ts)
  - Scala (.scala)
  - Go (.go)
  - Ruby (.rb)
  - PHP (.php)
- Handle projects with multiple programming languages
- Report language distribution statistics

### FR3: Package Manager Detection
- Identify package managers based on characteristic files:
  - Python: pip (requirements.txt, pyproject.toml), conda (environment.yml)
  - Node.js: npm (package.json), yarn (yarn.lock)
  - Java: Maven (pom.xml), Gradle (build.gradle)
  - Scala: sbt (build.sbt)
  - Go: go modules (go.mod)
  - Ruby: bundler (Gemfile)
  - PHP: composer (composer.json)

### FR4: Dependency File Identification
- Locate and parse dependency definition files:
  - requirements.txt, pyproject.toml (Python)
  - package.json (Node.js)
  - pom.xml (Maven)
  - build.gradle (Gradle)
  - build.sbt (Scala)
  - go.mod (Go)
  - Gemfile (Ruby)
  - composer.json (PHP)

### FR5: Dependency Extraction
- Implement specific parsers for each supported file format:
  - Text-based parsing for requirements.txt
  - TOML parsing for pyproject.toml
  - JSON parsing for package.json, composer.json
  - XML parsing for pom.xml
  - Custom parsing for build.gradle, build.sbt
  - Extract dependency names and version constraints

### FR6: Source Code Import Analysis
- Scan source files for import statements
- Support language-specific import patterns:
  - Python: import, from...import
  - Java: import
  - JavaScript: require, import
  - Scala: import
  - Go: import
  - Ruby: require
  - PHP: use, require, include

### FR7: Dependency Consolidation
- Merge dependencies from all sources
- Map source code imports to package names
- Identify discrepancies between declared and used dependencies
- De-duplicate dependencies across different files

### FR8: Dependency Classification
- Maintain configurable classification lists:
  - Allowed List: approved dependencies
  - Restricted List: prohibited or restricted dependencies
- Classify each dependency into categories:
  - Allowed: Present in Allowed List
  - Restricted: Present in Restricted List
  - Cannot Determine: Not found in either list

### FR9: Reporting
Generate comprehensive reports including:
- Project Overview:
  - Detected programming languages and their usage percentages
  - Identified package managers
  - List of dependency files found
- Dependency Analysis:
  - Complete list of identified dependencies
  - Version information (where available)
  - Source of identification (file or import)
  - Classification status
- Issues and Warnings:
  - Restricted dependencies found
  - Discrepancies between declared and used dependencies
  - Unclassified dependencies

## 5. Non-Functional Requirements

### NFR1: Extensibility
- Modular architecture supporting easy addition of:
  - New programming languages
  - Package managers
  - Dependency file formats
  - Parser implementations
- Plugin system for custom analyzers

### NFR2: Robustness
- Graceful error handling for:
  - Malformed dependency files
  - Unsupported file formats
  - Access permission issues
  - Invalid project structures
- Clear error reporting
- Partial results when full analysis isn't possible

### NFR3: Performance
- Complete analysis within reasonable timeframes:
  - Small projects (< 1000 files): < 30 seconds
  - Medium projects (1000-10000 files): < 2 minutes
  - Large projects (> 10000 files): < 5 minutes
- Efficient file system traversal
- Caching of repeated operations

### NFR4: Maintainability
- Clear code structure and organization
- Comprehensive documentation
- Type hints and docstrings
- Unit tests for core functionality
- Integration tests for parsers
- Code quality checks (linting, formatting)

### NFR5: Configuration
- External configuration files (YAML/JSON)
- Configurable options:
  - Allowed/Restricted lists location
  - Custom file patterns
  - Ignore patterns
  - Output formats
  - Scanning depth

## 6. Design Considerations

### Recommended Libraries
- File Parsing:
  - `tomli` for TOML parsing
  - `xml.etree.ElementTree` for XML
  - `json` for JSON files
  - `packaging` for Python package version parsing
  - `ast` for Python source analysis

### Detection Strategy
- File extension mapping
- Content-based detection
- Marker file identification
- Import statement analysis

### Output Formats
- JSON for machine processing
- Markdown for human readability
- HTML reports (optional)
- CSV export capability

## 7. Out of Scope
- Transitive dependency analysis
- Vulnerability scanning
- License compliance checking
- Automatic dependency updates
- Binary file analysis
- Remote repository scanning

## 8. Success Metrics
- Language Detection Accuracy: > 95%
- Package Manager Detection Accuracy: > 90%
- Dependency Identification Accuracy: > 85%
- Performance targets met for different project sizes
- User satisfaction through feedback
- Adoption rate in target organizations

## 9. Implementation Phases

### Phase 1: Core Infrastructure
- Basic project scanning
- File type detection
- Simple dependency file parsing

### Phase 2: Language Support
- Python support
- Java support
- JavaScript support

### Phase 3: Advanced Features
- Additional language support
- Import analysis
- Classification system

### Phase 4: Reporting and Integration
- Report generation
- Configuration system
- Documentation and testing