"""Scanner service for integrating with the existing DependencyScanner."""

import os
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List

from dependency_scanner_tool.scanner import DependencyScanner
from dependency_scanner_tool.api.models import ScanResultResponse
from dependency_scanner_tool.api.job_manager import job_manager, JobStatus


logger = logging.getLogger(__name__)


class ScannerService:
    """Service for scanning repositories."""
    
    def __init__(self):
        self.scanner = DependencyScanner()
        self.config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    
    async def scan_repository(self, job_id: str, git_url: str) -> None:
        """Scan a Git repository and update job status."""
        try:
            # Update job status to running
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 10)
            
            # Clone repository
            logger.info(f"Cloning repository: {git_url}")
            repo_path = await self._clone_repository(git_url)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 30)
            
            # Scan the repository
            logger.info(f"Scanning repository at: {repo_path}")
            scan_result = self.scanner.scan_project(str(repo_path))
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 80)
            
            # Transform results to category-based format
            logger.info("Transforming scan results")
            api_result = self._transform_results(git_url, scan_result)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 90)
            
            # Set results
            job_manager.set_job_result(job_id, api_result)
            logger.info(f"Scan completed successfully for job: {job_id}")
            
        except Exception as e:
            logger.error(f"Scan failed for job {job_id}: {str(e)}")
            job_manager.set_job_error(job_id, str(e))
        finally:
            # Cleanup temporary directory
            if 'repo_path' in locals():
                try:
                    shutil.rmtree(repo_path)
                    logger.info(f"Cleaned up temporary directory: {repo_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup directory {repo_path}: {str(e)}")
    
    async def _clone_repository(self, git_url: str) -> Path:
        """Clone a Git repository to a temporary directory."""
        temp_dir = tempfile.mkdtemp(prefix="repo_scan_")
        repo_path = Path(temp_dir) / "repo"
        
        # Use subprocess to clone repository
        cmd = ["git", "clone", git_url, str(repo_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            shutil.rmtree(temp_dir)
            raise Exception(f"Git clone failed: {result.stderr}")
        
        return repo_path
    
    def _transform_results(self, git_url: str, scan_result) -> ScanResultResponse:
        """Transform scan results to API format."""
        # For now, create dummy category-based results
        # In a real implementation, this would analyze the dependencies
        # and classify them based on the configuration
        dependencies = {
            "Data Science": False,
            "Machine Learning": False,
            "Web Frameworks": False,
            "Database": False,
            "Security": False
        }
        
        # Simple classification based on dependency names
        for dep in scan_result.dependencies:
            dep_name = dep.name.lower()
            if any(keyword in dep_name for keyword in ['pandas', 'numpy', 'scipy', 'matplotlib']):
                dependencies["Data Science"] = True
            elif any(keyword in dep_name for keyword in ['tensorflow', 'pytorch', 'sklearn']):
                dependencies["Machine Learning"] = True
            elif any(keyword in dep_name for keyword in ['flask', 'django', 'fastapi', 'spring']):
                dependencies["Web Frameworks"] = True
            elif any(keyword in dep_name for keyword in ['mysql', 'postgres', 'mongodb', 'redis']):
                dependencies["Database"] = True
            elif any(keyword in dep_name for keyword in ['crypto', 'security', 'auth']):
                dependencies["Security"] = True
        
        return ScanResultResponse(
            git_url=git_url,
            dependencies=dependencies
        )


# Global scanner service instance
scanner_service = ScannerService()