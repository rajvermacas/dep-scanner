"""FastAPI application for dependency scanner REST API."""

from datetime import datetime, timezone
from fastapi import FastAPI, BackgroundTasks, HTTPException

from dependency_scanner_tool.api.models import ScanRequest, ScanResponse, JobStatusResponse, ScanResultResponse, JobStatus
from dependency_scanner_tool.api.job_manager import job_manager
from dependency_scanner_tool.api.scanner_service import scanner_service

app = FastAPI(title="Dependency Scanner API", version="1.0.0")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


@app.post("/scan", response_model=ScanResponse)
async def scan_repository(request: ScanRequest, background_tasks: BackgroundTasks):
    """Submit a repository for scanning."""
    # Create job
    job_id = job_manager.create_job(request.git_url)
    
    # Start background scanning task
    background_tasks.add_task(scanner_service.scan_repository, job_id, request.git_url)
    
    return ScanResponse(
        job_id=job_id,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat()
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status by ID."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        progress=job.progress
    )


@app.get("/jobs/{job_id}/results", response_model=ScanResultResponse)
async def get_job_results(job_id: str):
    """Get job results by ID."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job.result:
        raise HTTPException(status_code=500, detail="Job completed but no results available")
    
    return job.result


