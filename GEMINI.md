# Project Overview

This project is a dependency scanning tool written in Python. It is designed to analyze software projects to identify their dependencies, programming languages, and package managers. The tool can be used as a command-line interface (CLI) application or through a REST API.

**Key Features:**

*   **Dependency Scanning:** Scans project files to detect and extract dependencies from various file formats, including `requirements.txt`, `pyproject.toml`, `pom.xml`, and `build.sbt`.
*   **Language and Package Manager Detection:** Identifies the programming languages and package managers used in a project.
*   **Import Analysis:** Analyzes source code files for import statements to identify dependencies.
*   **Dependency Classification:** Classifies dependencies as "allowed," "restricted," or "unknown" based on user-defined rules.
*   **Dependency Categorization:** Groups dependencies into custom categories (e.g., "Web Frameworks," "Data Science").
*   **Reporting:** Generates reports in various formats, including text, JSON, and HTML.
*   **REST API:** Provides an API for programmatic access to the scanner's functionality.
*   **GitLab Integration:** Includes features for scanning GitLab groups and integrating with GitLab CI pipelines.

**Technology Stack:**

*   **Backend:** Python
*   **CLI Framework:** Click
*   **API Framework:** FastAPI
*   **Templating:** Jinja2 (for HTML reports)
*   **Configuration:** YAML, .env files

# Building and Running

## Installation

You can install the tool from PyPI or from source.

**From PyPI:**

```bash
pip install dependency-scanner-tool-3
```

**From Source:**

```bash
git clone https://github.com/rajvermacas/dep-scanner.git
cd dep-scanner
pip install -e .
```

## Running the Scanner

The main command-line interface can be invoked as follows:

```bash
dependency-scanner-tool-3 [OPTIONS] PROJECT_PATH
```

**Example:**

```bash
# Scan a project and print results to the console
dependency-scanner-tool-3 /path/to/your/project

# Scan a project and generate an HTML report
dependency-scanner-tool-3 /path/to/your/project --html-output report.html
```

## Running the API Server

The REST API server can be started with the following command:

```bash
python -m src.dependency_scanner_tool.api.main
```

The server will be available at `http://localhost:8000`.

## Using the API Client

The client CLI can be used to interact with the API server.

**Example:**

```bash
# Scan a remote Git repository
scanner-client scan https://github.com/rajvermacas/airflow.git

# Scan a GitLab group
scanner-client group-scan https://gitlab.com/my-group-name
```

# Development Conventions

*   **Linting and Formatting:** The project uses `ruff` for linting and `black` for code formatting.
*   **Type Checking:** `mypy` is used for static type checking.
*   **Testing:** Tests are written using `pytest`.
*   **Configuration:** Project configuration is defined in `pyproject.toml`.
