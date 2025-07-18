"""Pydantic models for the REST API."""

import re
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanRequest(BaseModel):
    """Request model for scan endpoint."""
    git_url: str = Field(..., description="Git repository URL to scan")
    
    @field_validator('git_url')
    @classmethod
    def validate_git_url(cls, v):
        """Validate Git URL format."""
        # Accept HTTPS/HTTP URLs ending with .git
        https_pattern = r'^https?://[^\s/$.?#].[^\s]*\.git$'
        # Accept SSH URLs like git@github.com:user/repo.git
        ssh_pattern = r'^git@[^\s/$.?#].[^\s]*:[^\s]*\.git$'
        # Accept git:// URLs
        git_pattern = r'^git://[^\s/$.?#].[^\s]*\.git$'
        
        if not (re.match(https_pattern, v) or re.match(ssh_pattern, v) or re.match(git_pattern, v)):
            raise ValueError('Invalid Git URL format')
        return v


class ScanResponse(BaseModel):
    """Response model for scan endpoint."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    created_at: str = Field(..., description="Job creation timestamp")


class JobStatusResponse(BaseModel):
    """Response model for job status endpoint."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    created_at: str = Field(..., description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    progress: int = Field(..., description="Job progress percentage")


class ScanResultResponse(BaseModel):
    """Response model for scan results endpoint."""
    git_url: str = Field(..., description="Original Git repository URL")
    dependencies: Dict[str, bool] = Field(..., description="Category-based dependency flags")


class JobSummary(BaseModel):
    """Summary model for job listing."""
    job_id: str = Field(..., description="Unique job identifier")
    git_url: str = Field(..., description="Git repository URL")
    status: JobStatus = Field(..., description="Current job status")
    created_at: str = Field(..., description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    progress: int = Field(..., description="Job progress percentage")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class JobHistoryResponse(BaseModel):
    """Response model for job history endpoint."""
    jobs: list[JobSummary] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of jobs per page")
    total_pages: int = Field(..., description="Total number of pages")


class PartialResultsResponse(BaseModel):
    """Response model for partial results endpoint."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: int = Field(..., description="Job progress percentage")
    partial_results: Optional[Dict[str, Any]] = Field(None, description="Partial scan results")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")