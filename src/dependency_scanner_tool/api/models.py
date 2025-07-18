"""Pydantic models for the REST API."""

import re
from datetime import datetime
from enum import Enum
from typing import Optional, Dict
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
        git_url_pattern = r'^https?://[^\s/$.?#].[^\s]*\.git$'
        if not re.match(git_url_pattern, v):
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