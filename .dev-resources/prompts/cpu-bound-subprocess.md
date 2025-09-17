Task: Implement Subprocess Monitoring for Repository Scanner

  Context

  You need to implement a monitoring system for CPU-bound repository scanning tasks in the dependency scanner tool. The current implementation blocks the FastAPI worker's event loop, causing Gunicorn timeout issues. The
  solution architecture is documented in .dev-resources/architecture/subprocess-monitoring-architecture.md.

  Primary Objective

  Refactor the existing scanner service to use subprocess execution with filesystem-based monitoring, ensuring the API remains responsive while scanning large GitLab groups.

  Implementation Requirements

  1. Core Components to Implement

  - Create scanner_worker.py module that runs as a subprocess
  - Implement ScannerWorker class with status file writing (30-second intervals)
  - Modify scanner_service.py to spawn subprocesses instead of direct execution
  - Create JobMonitor class for status aggregation
  - Update API endpoints to return detailed progress information

  2. Key Files to Modify/Create

  - src/dependency_scanner_tool/api/scanner_worker.py (NEW)
  - src/dependency_scanner_tool/api/scanner_service.py (MODIFY)
  - src/dependency_scanner_tool/api/job_monitor.py (NEW)
  - src/dependency_scanner_tool/api/app.py (MODIFY endpoints)

  3. Technical Specifications

  - Use asyncio.create_subprocess_exec for subprocess spawning
  - Store status files in tmp/scan_jobs/{job_id}/ directory structure
  - Implement atomic file writes using temp file + rename pattern
  - Ensure no race conditions (each subprocess writes only to its own file)
  - Handle subprocess crashes gracefully with proper error reporting

  4. Status Update Requirements

  - Repository-level status files (repo_X.json) with progress details
  - Master status file (master.json) with aggregated summary
  - 30-second update intervals for active scans
  - Immediate updates on state changes (completed/failed/starting)

  5. API Response Format

  The /scan/{job_id} endpoint must return the detailed structure shown in the architecture document, including:
  - Overall summary (X of Y repositories)
  - Current repository details with file-level progress
  - Lists of completed/pending/failed repositories
  - Elapsed time and last update timestamp

  Testing Requirements

  - Test subprocess spawning doesn't block the API
  - Verify status files are created and updated correctly
  - Test concurrent scanning of multiple repositories
  - Verify crash handling (kill a subprocess mid-scan)
  - Test status aggregation with various states
  - Ensure cleanup of old job directories works

  Implementation Best Practices

  1. Error Handling: Wrap all file I/O in try-except blocks
  2. Logging: Add comprehensive logging at INFO level for major events, DEBUG for details
  3. Type Hints: Use proper type annotations for all new functions
  4. Docstrings: Document all classes and public methods
  5. Constants: Define paths and intervals as constants at module level
  6. Backwards Compatibility: Ensure existing single-repo scan endpoints still work

  Step-by-Step Implementation Order

  1. First, create the scanner_worker.py with basic status writing
  2. Test it standalone with a simple mock scan
  3. Integrate with scanner_service.py using subprocess
  4. Implement JobMonitor for status aggregation
  5. Update API endpoints to use new monitoring
  6. Add error handling and timeout logic
  7. Implement cleanup strategy
  8. Write comprehensive tests

  Validation Criteria

  - The API must remain responsive during scanning (test with concurrent requests)
  - Gunicorn workers must not timeout during long scans
  - Status updates must be visible within 30 seconds
  - Memory usage should remain stable (no leaks in subprocesses)
  - All existing tests must still pass

  Important Notes

  - DO NOT use Redis, queues, or databases - filesystem only
  - DO NOT modify the core scanning logic, only how it's executed
  - ENSURE the solution works on both Linux and macOS
  - The architecture document is the source of truth - follow it precisely
  - If you encounter ambiguities, choose the simplest solution that meets requirements

  Deliverables

  1. Working implementation with all components
  2. Updated API documentation (docstrings)
  3. Basic integration test demonstrating non-blocking behavior
  4. Brief summary of changes made and any deviations from architecture

  Reference

  Refer to .dev-resources/architecture/subprocess-monitoring-architecture.md for detailed specifications, code examples, and expected JSON structures.