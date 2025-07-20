# Dependency Scanner API Client

A comprehensive Python client and CLI tool for interacting with the Dependency Scanner REST API.

## Features

- **Full API Coverage**: Supports all REST API endpoints
- **Async Operations**: Submit scans and wait for completion with progress tracking
- **CLI Interface**: Easy-to-use command-line interface
- **Authentication**: HTTP Basic Auth support with environment variable configuration
- **Multiple Output Formats**: JSON output support for integration
- **Error Handling**: Robust error handling and connection validation

## Installation

```bash
# Install in development mode
pip install -e .

# Or install from PyPI (when published)
pip install dependency-scanner-tool-3
```

## Quick Start

### Environment Setup

Create a `.env` file with your API credentials:

```bash
# API Server Configuration
SCANNER_SERVER_URL=http://localhost:8001
API_USERNAME=admin
API_PASSWORD=secure_password_change_me
```

### Using the Python Client

```python
from dependency_scanner_tool.client import DependencyScannerClient

# Initialize client
client = DependencyScannerClient(
    base_url="http://localhost:8001",
    username="admin", 
    password="secure_password_change_me"
)

# Submit scan and wait for completion
job_id, results = client.scan_repository_and_wait(
    git_url="https://github.com/rajvermacas/airflow.git",
    max_wait=600,
    show_progress=True
)

# Display results
print(f"Repository: {results.git_url}")
for category, has_deps in results.dependencies.items():
    status = "✅ Found" if has_deps else "❌ None"
    print(f"  {category}: {status}")
```

### Using the CLI

```bash
# Check server health
scanner-client health

# Scan a repository and wait for completion
scanner-client scan https://github.com/rajvermacas/airflow.git --json-output results.json

# Submit scan without waiting
scanner-client scan https://github.com/user/repo.git --no-wait

# Check job status
scanner-client status <job-id>

# Get job results
scanner-client results <job-id> --json-output results.json

# Wait for job completion
scanner-client wait <job-id>

# List all jobs
scanner-client list-jobs --page 1 --per-page 10

# List jobs with status filter
scanner-client list-jobs --status-filter completed

# Run demo with Airflow repository
scanner-client demo
```

## API Client Reference

### DependencyScannerClient

#### Constructor

```python
DependencyScannerClient(
    base_url: str,
    username: str, 
    password: str,
    timeout: int = 30,
    poll_interval: int = 5
)
```

#### Methods

- **`health_check()`** - Check API server health
- **`submit_scan(git_url: str)`** - Submit repository for scanning
- **`get_job_status(job_id: str)`** - Get job status and progress
- **`get_job_results(job_id: str)`** - Get scan results (completed jobs only)
- **`get_partial_results(job_id: str)`** - Get partial results (running jobs)
- **`list_jobs(page, per_page, status)`** - List jobs with pagination
- **`wait_for_completion(job_id, max_wait, show_progress)`** - Wait for job completion
- **`scan_repository_and_wait(git_url, max_wait, show_progress)`** - Complete scan workflow

## CLI Commands

### Global Options

- `--server` - API server URL (default: http://localhost:8000)
- `--username` - API username (can use API_USERNAME env var)
- `--password` - API password (can use API_PASSWORD env var)
- `--timeout` - Request timeout in seconds
- `--poll-interval` - Polling interval for job status

### Commands

#### `health`
Check API server health status.

#### `scan <git_url>`
Submit a repository for scanning.

Options:
- `--wait/--no-wait` - Wait for completion (default: true)
- `--max-wait` - Maximum wait time in seconds (default: 600)
- `--json-output` - Save results to JSON file

#### `status <job_id>`
Get job status and progress information.

#### `results <job_id>`
Get scan results for completed jobs.

Options:
- `--json-output` - Save results to JSON file

#### `wait <job_id>`
Wait for job completion with progress tracking.

Options:
- `--max-wait` - Maximum wait time in seconds (default: 600)

#### `list-jobs`
List jobs with pagination.

Options:
- `--page` - Page number (default: 1)
- `--per-page` - Jobs per page (default: 10)
- `--status-filter` - Filter by status (pending, running, completed, failed)

#### `demo`
Run a demonstration scan of the Airflow repository.

Options:
- `--json-output` - Output file for results (default: airflow_scan_results.json)

## Example Workflows

### 1. Basic Repository Scan

```bash
# Set environment variables
export SCANNER_SERVER_URL=http://localhost:8001
export API_USERNAME=admin
export API_PASSWORD=secure_password_change_me

# Scan a repository
scanner-client scan https://github.com/pallets/flask.git --json-output flask_scan.json
```

### 2. Monitor Long-Running Scan

```bash
# Submit scan without waiting
JOB_ID=$(scanner-client scan https://github.com/large/repository.git --no-wait | grep "Job ID:" | cut -d: -f2 | tr -d ' ')

# Monitor progress
scanner-client status $JOB_ID

# Wait for completion when ready
scanner-client wait $JOB_ID

# Get results
scanner-client results $JOB_ID --json-output results.json
```

### 3. Batch Processing

```bash
# Scan multiple repositories
repos=(
    "https://github.com/user/repo1.git"
    "https://github.com/user/repo2.git"
    "https://github.com/user/repo3.git"
)

for repo in "${repos[@]}"; do
    echo "Scanning: $repo"
    scanner-client scan "$repo" --json-output "$(basename $repo .git)_results.json"
done
```

## Integration Examples

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Scan Dependencies
  run: |
    scanner-client scan ${{ github.repository_url }} --json-output scan_results.json
    
- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: dependency-scan-results
    path: scan_results.json
```

### Python Integration

```python
import json
from dependency_scanner_tool.client import DependencyScannerClient

def scan_and_analyze(git_url: str) -> dict:
    """Scan repository and return analysis."""
    client = DependencyScannerClient(
        base_url=os.getenv('SCANNER_SERVER_URL'),
        username=os.getenv('API_USERNAME'),
        password=os.getenv('API_PASSWORD')
    )
    
    job_id, results = client.scan_repository_and_wait(git_url)
    
    return {
        'repository': results.git_url,
        'has_security_deps': results.dependencies.get('Security', False),
        'has_ml_deps': results.dependencies.get('Machine Learning', False),
        'categories': results.dependencies
    }

# Usage
analysis = scan_and_analyze("https://github.com/user/repo.git")
print(f"Security dependencies found: {analysis['has_security_deps']}")
```

## Error Handling

The client includes comprehensive error handling:

- **Connection Errors**: Validates server connectivity on initialization
- **Authentication Errors**: Clear error messages for credential issues
- **Request Timeouts**: Configurable timeout handling
- **API Errors**: Detailed error messages from server responses
- **Job Failures**: Proper handling of failed scans

## Testing

Successfully tested with:
- ✅ **https://github.com/rajvermacas/airflow.git** - Target repository (completed successfully)
- ✅ **https://github.com/pallets/flask.git** - Flask web framework (found Web Frameworks, Database, Security dependencies)
- ✅ All API endpoints working correctly
- ✅ CLI interface fully functional
- ✅ JSON output generation working
- ✅ Authentication and error handling working

## Troubleshooting

### Connection Issues
```bash
# Test server connectivity
curl -u $API_USERNAME:$API_PASSWORD $SCANNER_SERVER_URL/health

# Check client connection
scanner-client health
```

### Authentication Issues
```bash
# Verify credentials
echo "Username: $API_USERNAME"
echo "Password length: ${#API_PASSWORD}"

# Test with explicit credentials
scanner-client --username admin --password your_password health
```

### Job Failures
```bash
# Check recent jobs for error messages
scanner-client list-jobs --status-filter failed

# Get detailed job status
scanner-client status <job-id>
```

This client provides a complete interface to the Dependency Scanner API, enabling both interactive usage and programmatic integration for dependency analysis workflows.