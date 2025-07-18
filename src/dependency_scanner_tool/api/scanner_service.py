"""Scanner service for integrating with the existing DependencyScanner."""

import logging
from pathlib import Path

from dependency_scanner_tool.scanner import DependencyScanner
from dependency_scanner_tool.api.models import ScanResultResponse
from dependency_scanner_tool.api.job_manager import job_manager, JobStatus
from dependency_scanner_tool.api.git_service import git_service
from dependency_scanner_tool.api.job_lifecycle import job_lifecycle_manager
from dependency_scanner_tool.api.validation import validate_git_url


logger = logging.getLogger(__name__)


class ScannerService:
    """Service for scanning repositories."""
    
    def __init__(self):
        self.scanner = DependencyScanner()
        self.config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    
    async def scan_repository(self, job_id: str, git_url: str) -> None:
        """Scan a Git repository and update job status."""
        repo_path = None
        try:
            # Register job start with lifecycle manager
            job_lifecycle_manager.register_job_start(job_id)
            
            # Validate Git URL
            logger.info(f"Validating Git URL: {git_url}")
            validated_url = validate_git_url(git_url)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 5)
            
            # Clone repository using secure Git service
            logger.info(f"Cloning repository: {validated_url}")
            repo_path = git_service.clone_repository(validated_url)
            job_lifecycle_manager.register_job_resource(job_id, repo_path)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 30)
            
            # Validate cloned repository
            if not git_service.validate_repository(repo_path):
                raise Exception("Invalid or corrupted repository")
            
            # Scan the repository
            logger.info(f"Scanning repository at: {repo_path}")
            scan_result = self.scanner.scan_project(str(repo_path))
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 80)
            
            # Transform results to category-based format
            logger.info("Transforming scan results")
            api_result = self._transform_results(validated_url, scan_result)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 90)
            
            # Set results
            job_manager.set_job_result(job_id, api_result)
            logger.info(f"Scan completed successfully for job: {job_id}")
            
        except Exception as e:
            logger.error(f"Scan failed for job {job_id}: {str(e)}")
            job_manager.set_job_error(job_id, str(e))
        finally:
            # Register job completion and cleanup
            job_lifecycle_manager.register_job_completion(job_id)
    
    def is_service_ready(self) -> bool:
        """Check if the scanner service is ready to accept jobs."""
        return job_lifecycle_manager.can_create_job()
    
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