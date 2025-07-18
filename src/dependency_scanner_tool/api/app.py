"""FastAPI application for dependency scanner REST API."""

import logging
from datetime import datetime, timezone
from fastapi import FastAPI, BackgroundTasks, HTTPException, status, Depends
from fastapi.security import HTTPBasic
from contextlib import asynccontextmanager

from dependency_scanner_tool.api.models import ScanRequest, ScanResponse, JobStatusResponse, ScanResultResponse, JobStatus
from dependency_scanner_tool.api.job_manager import job_manager
from dependency_scanner_tool.api.scanner_service import scanner_service
from dependency_scanner_tool.api.auth import get_current_user
from dependency_scanner_tool.api.job_lifecycle import job_lifecycle_manager
from dependency_scanner_tool.api.validation import validate_git_url

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info("Starting Dependency Scanner API")
    await job_lifecycle_manager.start()
    yield
    # Shutdown
    logger.info("Shutting down Dependency Scanner API")
    await job_lifecycle_manager.stop()


app = FastAPI(
    title="Dependency Scanner API", 
    version="1.0.0",
    lifespan=lifespan
)

# Note: Using dependency injection for auth instead of middleware for cleaner error handling

# Security dependency
security = HTTPBasic()


@app.get("/health")
async def health_check(current_user: str = Depends(get_current_user)):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "user": current_user
    }


@app.post("/scan", response_model=ScanResponse)
async def scan_repository(
    request: ScanRequest, 
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """Submit a repository for scanning."""
    # Check if service can accept new jobs
    if not scanner_service.is_service_ready():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many concurrent jobs. Please try again later."
        )
    
    # Validate Git URL (this will raise HTTPException if invalid)
    try:
        validate_git_url(request.git_url)
    except HTTPException:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Unexpected validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Git URL"
        )
    
    # Create job
    job_id = job_manager.create_job(request.git_url)
    
    # Start background scanning task
    background_tasks.add_task(scanner_service.scan_repository, job_id, request.git_url)
    
    logger.info(f"Job {job_id} created by user {current_user} for URL: {request.git_url}")
    
    return ScanResponse(
        job_id=job_id,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat()
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, current_user: str = Depends(get_current_user)):
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
async def get_job_results(job_id: str, current_user: str = Depends(get_current_user)):
    """Get job results by ID."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    if not job.result:
        raise HTTPException(status_code=500, detail="Job completed but no results available")
    
    return job.result


