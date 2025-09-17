# Subprocess Monitoring Architecture for Dependency Scanner

## Overview

This document describes the architecture for monitoring CPU-bound repository scanning tasks without blocking the FastAPI worker's event loop. The solution uses subprocess execution with filesystem-based status tracking to provide real-time progress updates without external dependencies like Redis or databases.

## Problem Statement

When scanning GitLab groups with multiple repositories, the CPU-intensive scanning operations block the FastAPI worker's event loop, preventing:
- Gunicorn heartbeat signals from being sent
- Other API requests from being handled
- Worker timeout and potential termination

## Solution Architecture

### Core Approach

Use `asyncio.create_subprocess_exec` to spawn separate processes for CPU-bound work while maintaining visibility through filesystem-based status tracking.

```
[Client] → [FastAPI Worker] → [Subprocess (Scanner)] → [Status Files]
              ↓                         ↓
         (Returns immediately)    (Writes progress)
              ↓                         ↓
         [Status Endpoint] ← [Reads aggregated status]
```

### Key Components

#### 1. FastAPI Worker Process
- Handles HTTP requests
- Spawns subprocesses for scanning
- Aggregates status from filesystem
- Never blocks on CPU-intensive work

#### 2. Scanner Subprocess
- Performs actual repository scanning
- Writes progress to dedicated status file
- Completely isolated from API worker
- Can crash without affecting API

#### 3. Filesystem Status Tracking
- No shared state or race conditions
- Each subprocess owns its status file
- Master process only reads (never writes to subprocess files)

## Implementation Details

### Directory Structure

```
tmp/scan_jobs/
├── {job_id}/
│   ├── master.json         # Overall job status (aggregated)
│   ├── repo_0.json         # Status for 1st repository
│   ├── repo_1.json         # Status for 2nd repository
│   ├── repo_2.json         # Status for 3rd repository
│   └── ...
```

### Status File Formats

#### Repository Status File (`repo_X.json`)
Written by each subprocess scanner:

```json
{
  "repo_index": 0,
  "repo_name": "gitlab.com/mycompany/auth-service",
  "status": "scanning",
  "total_files": 1500,
  "current_file": 234,
  "current_filename": "src/auth/validator.py",
  "started_at": "2024-01-15T10:28:00Z",
  "last_update": "2024-01-15T10:30:00Z",
  "errors": [],
  "pid": 12345
}
```

#### Master Status File (`master.json`)
Aggregated by the API process:

```json
{
  "job_id": "abc-123-def",
  "group_url": "https://gitlab.com/mycompany",
  "total_repositories": 8,
  "status": "in_progress",
  "summary": {
    "completed": 2,
    "in_progress": 3,
    "pending": 3,
    "failed": 0
  },
  "started_at": "2024-01-15T10:27:00Z",
  "last_aggregation": "2024-01-15T10:30:15Z"
}
```

### Process Flow

#### 1. Job Initiation

```python
# API endpoint
@app.post("/scan")
async def scan_group(request: ScanGroupRequest):
    job_id = str(uuid.uuid4())

    # Create job directory
    job_dir = Path(f"tmp/scan_jobs/{job_id}")
    job_dir.mkdir(parents=True)

    # Initialize master status
    master_status = {
        "job_id": job_id,
        "group_url": request.group_url,
        "total_repositories": len(repositories),
        "status": "initializing"
    }

    # Spawn subprocess for scanning
    process = await asyncio.create_subprocess_exec(
        sys.executable, '-m', 'dependency_scanner_tool.scanner_worker',
        job_id, request.group_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Monitor in background (non-blocking)
    asyncio.create_task(monitor_job(job_id, process))

    return {"job_id": job_id}
```

#### 2. Scanner Worker Process

```python
# scanner_worker.py
class ScannerWorker:
    def __init__(self, job_id: str, repo_index: int):
        self.job_id = job_id
        self.repo_index = repo_index
        self.status_file = f"tmp/scan_jobs/{job_id}/repo_{repo_index}.json"
        self.last_update = 0
        self.status = {}

    def update_status(self, **kwargs):
        """Update in-memory status and write to file every 30 seconds"""
        self.status.update(kwargs)
        self.status["last_update"] = time.time()

        # Write to file every 30 seconds or on major events
        if (time.time() - self.last_update > 30 or
            kwargs.get("status") in ["completed", "failed", "starting"]):
            self._write_status_file()
            self.last_update = time.time()

    def _write_status_file(self):
        """Atomic write to avoid partial reads"""
        temp_file = f"{self.status_file}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(self.status, f, indent=2)
        os.rename(temp_file, self.status_file)  # Atomic on most filesystems

    def scan_repository(self, repo_url: str):
        self.update_status(
            repo_name=repo_url,
            status="cloning",
            repo_index=self.repo_index
        )

        # Clone repository...

        self.update_status(
            status="scanning",
            total_files=total_files,
            current_file=0
        )

        for i, file in enumerate(files):
            # Process file...

            self.update_status(
                current_file=i + 1,
                current_filename=file,
                percentage=((i + 1) / total_files) * 100
            )

        self.update_status(status="completed")
```

#### 3. Status Aggregation

```python
class JobMonitor:
    async def get_job_status(self, job_id: str) -> dict:
        """Aggregate status from all subprocess files"""
        job_dir = Path(f"tmp/scan_jobs/{job_id}")

        if not job_dir.exists():
            return {"status": "not_found"}

        # Read master status
        master_file = job_dir / "master.json"
        if master_file.exists():
            with open(master_file) as f:
                master_status = json.load(f)
        else:
            master_status = {"status": "initializing"}

        # Read all repository status files
        repo_statuses = []
        for repo_file in sorted(job_dir.glob("repo_*.json")):
            with open(repo_file) as f:
                repo_status = json.load(f)
                repo_statuses.append(repo_status)

        # Aggregate information
        completed = [r for r in repo_statuses if r["status"] == "completed"]
        in_progress = [r for r in repo_statuses if r["status"] in ["cloning", "scanning", "analyzing"]]
        failed = [r for r in repo_statuses if r["status"] == "failed"]

        # Build response
        return {
            "job_id": job_id,
            "status": self._determine_overall_status(master_status, repo_statuses),
            "group_url": master_status.get("group_url"),
            "summary": {
                "total_repositories": master_status.get("total_repositories", 0),
                "completed": len(completed),
                "in_progress": len(in_progress),
                "pending": master_status.get("total_repositories", 0) - len(completed) - len(in_progress) - len(failed),
                "failed": len(failed)
            },
            "current_repositories": in_progress,
            "completed_repositories": [r["repo_name"] for r in completed],
            "failed_repositories": [r["repo_name"] for r in failed],
            "last_update": max([r.get("last_update", 0) for r in repo_statuses], default=0),
            "elapsed_time_seconds": time.time() - master_status.get("started_at", time.time())
        }
```

### API Response Structure

When clients call `GET /scan/{job_id}`, they receive:

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
      "repo_name": "gitlab.com/mycompany/auth-service",
      "status": "scanning",
      "progress": {
        "total_files": 1500,
        "current_file": 234,
        "percentage": 15.6,
        "current_file_name": "src/auth/validator.py"
      },
      "started_at": "2024-01-15T10:28:00Z"
    },
    {
      "repo_name": "gitlab.com/mycompany/payment-api",
      "status": "cloning",
      "progress": {
        "message": "Cloning repository..."
      },
      "started_at": "2024-01-15T10:29:30Z"
    },
    {
      "repo_name": "gitlab.com/mycompany/user-service",
      "status": "analyzing",
      "progress": {
        "total_files": 890,
        "current_file": 890,
        "percentage": 100,
        "message": "Analyzing API calls..."
      },
      "started_at": "2024-01-15T10:25:00Z"
    }
  ],
  "completed_repositories": [
    "gitlab.com/mycompany/config-server",
    "gitlab.com/mycompany/logging-lib"
  ],
  "pending_repositories": [
    "gitlab.com/mycompany/frontend",
    "gitlab.com/mycompany/admin-panel",
    "gitlab.com/mycompany/mobile-api"
  ],
  "last_update": "2024-01-15T10:30:15Z",
  "elapsed_time_seconds": 125
}
```

## Advantages of This Approach

### 1. No Race Conditions
- Each subprocess writes only to its own file
- No shared write access
- Master process only reads

### 2. Process Isolation
- Subprocess crashes don't affect API
- Memory leaks contained to subprocess
- Clean process per repository

### 3. Simple Implementation
- No external dependencies (Redis/RabbitMQ)
- Standard library only (asyncio, subprocess)
- Easy to debug (just JSON files)

### 4. Scalability
- Can spawn multiple concurrent subprocesses
- Each subprocess independent
- Filesystem I/O minimal (30-second intervals)

### 5. Observability
- Status files human-readable
- Easy debugging (just check JSON files)
- Progress visible at multiple granularities

## Error Handling

### Subprocess Crashes
```python
async def monitor_job(job_id: str, process):
    """Monitor subprocess health"""
    returncode = await process.wait()

    if returncode != 0:
        # Mark job as failed
        stderr = await process.stderr.read()
        update_master_status(job_id, {
            "status": "failed",
            "error": f"Process exited with code {returncode}",
            "stderr": stderr.decode()
        })
```

### Timeout Handling
```python
async def monitor_with_timeout(job_id: str, process, timeout=3600):
    """Kill process if it runs too long"""
    try:
        await asyncio.wait_for(process.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        update_master_status(job_id, {
            "status": "timeout",
            "error": f"Process killed after {timeout} seconds"
        })
```

### Stale Status Detection
```python
def is_status_stale(status: dict, threshold=120) -> bool:
    """Check if status hasn't been updated recently"""
    last_update = status.get("last_update", 0)
    return (time.time() - last_update) > threshold
```

## Cleanup Strategy

### Automatic Cleanup
```python
async def cleanup_old_jobs(age_hours=24):
    """Remove old job directories"""
    base_dir = Path("tmp/scan_jobs")
    cutoff_time = time.time() - (age_hours * 3600)

    for job_dir in base_dir.iterdir():
        if job_dir.is_dir():
            master_file = job_dir / "master.json"
            if master_file.exists():
                with open(master_file) as f:
                    status = json.load(f)
                    if status.get("completed_at", 0) < cutoff_time:
                        shutil.rmtree(job_dir)
```

## Performance Considerations

### Status Update Frequency
- **In-memory buffering**: Keep status in memory, write periodically
- **30-second intervals**: Balance between visibility and I/O
- **Event-based writes**: Write immediately on major state changes

### File I/O Optimization
- **Atomic writes**: Use rename for consistency
- **Minimal reads**: Only read when client requests status
- **Directory structure**: Separate files prevent contention

### Process Management
- **Process pooling**: Limit concurrent subprocesses
- **Queue management**: Process repositories in batches
- **Resource limits**: Set memory/CPU limits per subprocess

## Future Enhancements

1. **WebSocket Support**: Real-time status streaming to clients
2. **Compression**: Compress old status files
3. **S3 Integration**: Store results in S3 for persistence
4. **Metrics Collection**: Prometheus metrics for monitoring
5. **Retry Logic**: Automatic retry for failed repositories

## Conclusion

This architecture provides a robust, simple solution for monitoring CPU-bound tasks in FastAPI without external dependencies. It ensures worker health, provides detailed progress visibility, and maintains system stability through process isolation.