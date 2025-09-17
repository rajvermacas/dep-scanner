# Subprocess Monitoring Implementation

## Overview

This document describes the implementation of subprocess-based repository scanning with filesystem monitoring to prevent FastAPI worker timeout issues during CPU-intensive operations.

## Problem Solved

Previously, when scanning GitLab groups with multiple repositories, the CPU-intensive scanning operations would block the FastAPI worker's event loop, causing:
- Gunicorn heartbeat timeout
- Worker termination
- Failed scans for large repository groups

## Solution Architecture

### Core Components

1. **Scanner Worker Process** (`scanner_worker.py`)
   - Runs as independent subprocess
   - Performs actual repository scanning
   - Writes progress to filesystem status files
   - Fails fast on errors with detailed reporting

2. **Job Monitor** (`job_monitor.py`)
   - Aggregates status from multiple subprocess files
   - Provides unified job status API
   - Handles subprocess lifecycle monitoring
   - Manages cleanup of old job directories

3. **Scanner Service** (`scanner_service.py`)
   - Spawns subprocesses using `asyncio.create_subprocess_exec`
   - Manages concurrent subprocess execution
   - Transforms subprocess results to API responses
   - Handles process cleanup on job completion

4. **API Endpoints** (`app.py`)
   - New `/scan/{job_id}` endpoint for detailed progress
   - Non-blocking scan submission
   - Real-time progress monitoring
   - Periodic cleanup task in lifespan

## Status File Structure

```
tmp/scan_jobs/
├── {job_id}/
│   ├── master.json         # Overall job status
│   ├── repo_0.json         # Status for first repository
│   ├── repo_1.json         # Status for second repository
│   └── ...
```

### Repository Status File Format

```json
{
  "repo_index": 0,
  "repo_name": "project-name",
  "status": "scanning",
  "total_files": 1500,
  "current_file": 234,
  "current_filename": "src/main.py",
  "percentage": 15.6,
  "started_at": "2024-01-15T10:28:00Z",
  "last_update": "2024-01-15T10:30:00Z",
  "pid": 12345,
  "errors": []
}
```

### Master Status File Format

```json
{
  "job_id": "abc-123-def",
  "group_url": "https://gitlab.com/mycompany",
  "total_repositories": 8,
  "status": "in_progress",
  "started_at": "2024-01-15T10:27:00Z",
  "completed_at": null,
  "last_aggregation": "2024-01-15T10:30:15Z"
}
```

## API Response Structure

### GET /scan/{job_id}

Returns detailed progress information:

```json
{
  "job_id": "abc-123-def",
  "status": "in_progress",
  "group_url": "https://gitlab.com/mycompany",
  "summary": {
    "total_repositories": 8,
    "completed": 2,
    "in_progress": 3,
    "pending": 3,
    "failed": 0
  },
  "current_repositories": [
    {
      "repo_name": "auth-service",
      "status": "scanning",
      "progress": {
        "total_files": 1500,
        "current_file": 234,
        "percentage": 15.6,
        "current_file_name": "src/auth/validator.py"
      },
      "started_at": "2024-01-15T10:28:00Z"
    }
  ],
  "completed_repositories": ["config-server", "logging-lib"],
  "failed_repositories": [],
  "elapsed_time_seconds": 125,
  "last_update": "2024-01-15T10:30:15Z"
}
```

## Key Features

### 1. Non-Blocking Execution
- API returns immediately after spawning subprocesses
- Worker event loop remains responsive
- Multiple API requests can be handled concurrently

### 2. Real-Time Progress Monitoring
- Status files updated every 30 seconds
- Immediate updates on state changes
- File-level scanning progress tracking

### 3. Fail-Fast Error Handling
- No silent failures or retries
- Immediate error propagation
- Detailed error logging with stack traces

### 4. Process Isolation
- Each repository scanned in separate process
- Subprocess crashes don't affect API
- Memory leaks contained to subprocess

### 5. Automatic Cleanup
- Old job directories removed after 24 hours
- Periodic cleanup task runs hourly
- Configurable retention period

### 6. Concurrent Execution
- Up to 5 concurrent subprocesses (configurable)
- Semaphore-based concurrency control
- Efficient processing of large repository groups

## Configuration

### Environment Variables

None required - all configuration is in code constants:

- `MAX_CONCURRENT_PROCESSES = 5` - Maximum concurrent subprocesses
- `SUBPROCESS_TIMEOUT = 3600` - Subprocess timeout in seconds
- `UPDATE_INTERVAL = 30` - Status update interval in seconds
- `CLEANUP_AGE_HOURS = 24` - Job cleanup age in hours

## Error Handling

### Subprocess Crashes
- Process exit code recorded
- stderr captured and logged
- Failed status written to filesystem

### Timeout Handling
- Processes killed after timeout
- Timeout status recorded
- Job marked as failed

### File I/O Errors
- Atomic writes using rename
- Fail fast on write errors
- No corrupted status files

## Testing

### Integration Tests

Created comprehensive test suite in `tests/test_subprocess_monitoring.py`:

1. **Non-blocking behavior**: Verify API remains responsive during scans
2. **Status file operations**: Test creation, updates, and aggregation
3. **Concurrent execution**: Verify multiple subprocess spawning
4. **Crash handling**: Test subprocess failure scenarios
5. **Timeout handling**: Verify timeout detection and cleanup
6. **Cleanup**: Test old job directory removal
7. **Atomic writes**: Verify no file corruption
8. **Race conditions**: Confirm isolation between processes

### Manual Testing

Test scanner worker standalone:
```bash
python scripts/test_scanner_worker.py
```

Test API server:
```bash
python -m src.dependency_scanner_tool.api.main
```

Submit scan via API:
```bash
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -u username:password \
  -d '{"git_url": "https://github.com/example/repo.git"}'
```

Monitor progress:
```bash
curl http://localhost:8000/scan/{job_id} -u username:password
```

## Performance Characteristics

- **API Response Time**: < 100ms for scan submission
- **Status Update Latency**: Maximum 30 seconds
- **Memory Usage**: Isolated per subprocess
- **Concurrent Scans**: Up to 5 repositories simultaneously
- **Cleanup**: Automatic after 24 hours

## Advantages

1. **No External Dependencies**: Filesystem-only, no Redis/databases
2. **Simple Implementation**: Standard library (asyncio, subprocess)
3. **Easy Debugging**: Human-readable JSON status files
4. **Scalable**: Can adjust concurrent process limit
5. **Resilient**: Process isolation prevents cascading failures

## Migration Notes

### Breaking Changes
- Scanner service completely rewritten for subprocess execution
- Job monitoring now filesystem-based instead of in-memory
- New `/scan/{job_id}` endpoint for progress monitoring

### Backwards Compatibility
- Existing `/jobs/{job_id}` endpoint still works
- `/jobs/{job_id}/results` endpoint unchanged
- Authentication unchanged

## Future Enhancements

Potential improvements for future versions:

1. **WebSocket Support**: Real-time status streaming
2. **Result Persistence**: Save scan results to files
3. **S3 Integration**: Store results in cloud storage
4. **Metrics**: Prometheus metrics for monitoring
5. **Retry Logic**: Optional retry for failed repositories
6. **Dynamic Scaling**: Adjust concurrency based on load

## Troubleshooting

### Common Issues

1. **Status files not updating**
   - Check filesystem permissions
   - Verify `tmp/scan_jobs` directory exists
   - Check subprocess logs for errors

2. **Subprocesses hanging**
   - Check timeout configuration
   - Monitor process list with `ps aux`
   - Review subprocess stderr output

3. **High memory usage**
   - Reduce MAX_CONCURRENT_PROCESSES
   - Check for memory leaks in scanner
   - Monitor individual subprocess memory

### Debug Commands

View job status files:
```bash
ls -la tmp/scan_jobs/{job_id}/
cat tmp/scan_jobs/{job_id}/master.json | jq
```

Monitor running processes:
```bash
ps aux | grep scanner_worker
```

Check API logs:
```bash
tail -f /var/log/dependency-scanner.log
```

## Conclusion

The subprocess monitoring implementation successfully solves the worker timeout issue by:
- Moving CPU-intensive work to subprocesses
- Maintaining API responsiveness
- Providing detailed progress visibility
- Ensuring robust error handling
- Enabling concurrent repository scanning

The solution requires no external dependencies and provides a simple, maintainable approach to handling long-running scanning operations.