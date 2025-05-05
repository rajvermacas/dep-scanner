# Dependency Scanner Reporting Guide

This document explains how to use the reporting features of the Dependency Scanner Tool.

## JSON Output

The Dependency Scanner Tool can output scan results in JSON format, which can be used for further processing or visualization.

### Command-line Usage

To generate JSON output, use the `--output-format=json` option:

```bash
dependency-scanner-tool /path/to/project --output-format=json
```

To save the JSON output to a file, use the `--json-output` option:

```bash
dependency-scanner-tool /path/to/project --json-output=scan-results.json
```

### JSON Schema

The JSON output follows this schema:

```json
{
  "scan_summary": {
    "languages": {
      "Python": 75.5,
      "JavaScript": 24.5
    },
    "package_managers": ["pip", "npm"],
    "dependency_count": 42,
    "error_count": 0
  },
  "dependency_files": [
    "/path/to/project/requirements.txt",
    "/path/to/project/package.json"
  ],
  "dependencies": [
    {
      "name": "requests",
      "version": "2.28.1",
      "source_file": "/path/to/project/requirements.txt",
      "type": "allowed"
    }
  ],
  "errors": []
}
```

## HTML Report Generation

The Dependency Scanner Tool can generate HTML reports from JSON scan results.

### Command-line Usage

There are two ways to generate HTML reports:

1. Directly from a scan using the `--html-output` option:

```bash
dependency-scanner-tool /path/to/project --html-output=report.html
```

2. From an existing JSON file using the dedicated HTML report generator:

```bash
python -m dependency_scanner_tool.html_report scan-results.json -o report.html
```

### HTML Report Customization

You can customize the HTML report by providing your own template:

```bash
python -m dependency_scanner_tool.html_report scan-results.json -o report.html --template custom-template.html
```

The template should be a valid Jinja2 template. See the default template in `src/dependency_scanner_tool/reporters/templates/report.html` for reference.

## GitLab CI Integration

The Dependency Scanner Tool can be integrated into GitLab CI pipelines to automatically scan projects and generate reports.

### Setup

1. Add the `.gitlab-ci.yml` file to your project root directory
2. Configure the pipeline stages as needed

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
