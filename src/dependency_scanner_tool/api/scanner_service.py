"""Scanner service for integrating with the existing DependencyScanner."""

import logging
import yaml
from pathlib import Path

from dependency_scanner_tool.scanner import DependencyScanner
from dependency_scanner_tool.api.models import ScanResultResponse, ProjectScanResult
from dependency_scanner_tool.api.job_manager import job_manager, JobStatus
from dependency_scanner_tool.api.git_service import repository_service
from dependency_scanner_tool.api.job_lifecycle import job_lifecycle_manager
from dependency_scanner_tool.api.validation import validate_git_url, is_gitlab_group_url
from dependency_scanner_tool.api.gitlab_service import GitLabGroupService


logger = logging.getLogger(__name__)


class ScannerService:
    """Service for scanning repositories."""
    
    def __init__(self):
        self.scanner = DependencyScanner()
        self.config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    
    def _load_config(self) -> dict:
        """Load configuration from config.yaml file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Successfully loaded config from {self.config_path}")
                return config
        except FileNotFoundError:
            logger.error(f"Config file not found at {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}")
            return {}
    
    async def scan_repository(self, job_id: str, git_url: str) -> None:
        """Scan a Git repository or GitLab group and update job status."""
        try:
            # Register job start with lifecycle manager
            job_lifecycle_manager.register_job_start(job_id)
            
            # Validate Git URL
            logger.info(f"Validating Git URL: {git_url}")
            validated_url = validate_git_url(git_url)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 5)
            
            # Determine if this is a group or single repository scan
            if is_gitlab_group_url(validated_url):
                logger.info(f"Detected GitLab group URL: {validated_url}")
                await self._scan_gitlab_group(job_id, validated_url)
            else:
                logger.info(f"Detected single repository URL: {validated_url}")
                await self._scan_single_repository(job_id, validated_url)
                
        except Exception as e:
            logger.error(f"Scan failed for job {job_id}: {str(e)}")
            job_manager.set_job_error(job_id, str(e))
        finally:
            # Register job completion and cleanup
            job_lifecycle_manager.register_job_completion(job_id)
    
    async def _scan_single_repository(self, job_id: str, git_url: str) -> None:
        """Scan a single Git repository."""
        repo_path = None
        try:
            # Download repository using secure repository service
            logger.info(f"Downloading repository: {git_url}")
            repo_path = repository_service.download_repository(git_url)
            job_lifecycle_manager.register_job_resource(job_id, repo_path)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 30)
            
            # Validate downloaded repository
            if not repository_service.validate_repository(repo_path):
                raise Exception("Invalid or corrupted repository")
            
            # Scan the repository
            logger.info(f"Scanning repository at: {repo_path}")
            scan_result = self.scanner.scan_project(str(repo_path))
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 80)
            
            # Transform results to category-based format
            logger.info("Transforming scan results")
            api_result = self._transform_single_repo_results(git_url, scan_result)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 90)
            
            # Set results
            job_manager.set_job_result(job_id, api_result)
            logger.info(f"Repository scan completed successfully for job: {job_id}")
            
        except Exception as e:
            logger.error(f"Repository scan failed for job {job_id}: {str(e)}")
            raise
    
    async def _scan_gitlab_group(self, job_id: str, group_url: str) -> None:
        """Scan all repositories in a GitLab group."""
        gitlab_service = GitLabGroupService()
        
        try:
            # Get project information
            logger.info(f"Fetching GitLab group projects: {group_url}")
            project_info = gitlab_service.get_project_info(group_url)
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 10)
            
            if not project_info:
                raise Exception("No projects found in the GitLab group")
            
            logger.info(f"Found {len(project_info)} projects in group")
            
            # Scan each project
            project_results = []
            failed_projects = []
            group_dependencies = {}
            total_projects = len(project_info)
            
            for i, project in enumerate(project_info):
                project_name = project['name']
                git_url = project['git_url']
                
                if not git_url:
                    logger.warning(f"Skipping project {project_name}: no git URL")
                    continue
                
                logger.info(f"Scanning project [{i+1}/{total_projects}]: {project_name}")
                
                try:
                    # Scan individual project
                    repo_path = repository_service.download_repository(git_url)
                    job_lifecycle_manager.register_job_resource(job_id, repo_path)
                    
                    if repository_service.validate_repository(repo_path):
                        scan_result = self.scanner.scan_project(str(repo_path))
                        project_dependencies = self._transform_dependencies_only(scan_result, project_name)
                        
                        project_results.append(ProjectScanResult(
                            project_name=project_name,
                            git_url=git_url,
                            dependencies=project_dependencies,
                            status="success"
                        ))
                        
                        # Aggregate dependencies (OR logic: if any project has it, mark as present)
                        for category, has_deps in project_dependencies.items():
                            if category not in group_dependencies:
                                group_dependencies[category] = has_deps
                            else:
                                group_dependencies[category] = group_dependencies[category] or has_deps
                        
                        logger.info(f"✅ Project {project_name} scanned successfully")
                    else:
                        raise Exception("Invalid or corrupted repository")
                        
                except Exception as e:
                    logger.error(f"❌ Project {project_name} scan failed: {e}")
                    failed_projects.append({
                        'project_name': project_name,
                        'git_url': git_url,
                        'error': str(e)
                    })
                    project_results.append(ProjectScanResult(
                        project_name=project_name,
                        git_url=git_url,
                        dependencies={},
                        status="failed",
                        error=str(e)
                    ))
                
                # Update progress
                progress = 10 + int((i + 1) / total_projects * 80)
                job_manager.update_job_status(job_id, JobStatus.RUNNING, progress)
            
            # Create group scan result
            successful_scans = len([r for r in project_results if r.status == "success"])
            failed_scans = len([r for r in project_results if r.status == "failed"])
            
            api_result = ScanResultResponse(
                git_url=group_url,
                dependencies=group_dependencies,
                scan_type="group",
                total_projects=total_projects,
                successful_scans=successful_scans,
                failed_scans=failed_scans,
                project_results=project_results,
                failed_projects=failed_projects
            )
            
            job_manager.update_job_status(job_id, JobStatus.RUNNING, 95)
            job_manager.set_job_result(job_id, api_result)
            logger.info(f"Group scan completed successfully for job: {job_id}")
            
        except Exception as e:
            logger.error(f"Group scan failed for job {job_id}: {str(e)}")
            raise
    
    def is_service_ready(self) -> bool:
        """Check if the scanner service is ready to accept jobs."""
        return job_lifecycle_manager.can_create_job()
    
    def _transform_single_repo_results(self, git_url: str, scan_result) -> ScanResultResponse:
        """Transform scan results to API format for single repository."""
        # Extract repository name from URL for logging
        repo_name = git_url.split('/')[-1].replace('.git', '') if '/' in git_url else git_url
        dependencies = self._transform_dependencies_only(scan_result, f"Single Repository ({repo_name})")
        
        return ScanResultResponse(
            git_url=git_url,
            dependencies=dependencies,
            scan_type="repository"
        )
    
    def _transform_dependencies_only(self, scan_result, project_name: str = None) -> dict:
        """Transform scan results to dependency dictionary with detailed logging."""
        # Load configuration to get categories
        config = self._load_config()
        categories = config.get('categories', {})
        
        # Initialize all categories as False
        dependencies = {category_name: False for category_name in categories.keys()}
        
        # If no categories are defined in config, use fallback
        if not dependencies:
            logger.warning("No categories found in config, using default categories")
            dependencies = {
                "Data Science": False,
                "Machine Learning": False,
                "Web Frameworks": False,
                "Database": False,
                "Security": False
            }
        
        # Prepare detailed tracking
        category_matches = {category: [] for category in dependencies.keys()}
        unmatched_dependencies = []
        total_dependencies = len(scan_result.dependencies)
        source_files = set()
        
        # Classify dependencies based on config
        for dep in scan_result.dependencies:
            dep_name = dep.name.lower()
            matched = False
            
            # Track source file
            if dep.source_file:
                source_files.add(dep.source_file)
            
            # Check each category's dependency list
            for category_name, category_config in categories.items():
                category_dependencies = category_config.get('dependencies', [])
                
                # Check if dependency matches any in the category
                for config_dep in category_dependencies:
                    if dep_name == config_dep.lower() or config_dep.lower() in dep_name:
                        dependencies[category_name] = True
                        category_matches[category_name].append(dep.name)
                        matched = True
                        logger.debug(f"Matched dependency '{dep.name}' to category '{category_name}'")
                        break
                
                if matched:
                    break
            
            # Track unmatched dependencies
            if not matched:
                unmatched_dependencies.append(dep.name)
        
        # Log detailed dependency information
        self._log_project_dependencies(
            project_name or "Repository",
            total_dependencies,
            category_matches, 
            unmatched_dependencies,
            source_files
        )
        
        return dependencies
    
    def _log_project_dependencies(self, project_name: str, total_dependencies: int, 
                                  category_matches: dict, unmatched_dependencies: list, 
                                  source_files: set):
        """Log detailed dependency information for a project."""
        logger.info(f"📦 Project: {project_name}")
        logger.info(f"   Dependencies found: {total_dependencies} total")
        
        # Log matched categories with dependency details
        found_categories = 0
        for category, matched_deps in category_matches.items():
            if matched_deps:
                found_categories += 1
                deps_str = ", ".join(matched_deps[:5])  # Show first 5 dependencies
                if len(matched_deps) > 5:
                    deps_str += f" (and {len(matched_deps) - 5} more)"
                logger.info(f"   ✅ {category}: {deps_str} ({len(matched_deps)} found)")
            else:
                logger.info(f"   ❌ {category}: None found")
        
        # Log unmatched dependencies if any
        if unmatched_dependencies:
            unmatched_str = ", ".join(unmatched_dependencies[:10])  # Show first 10
            if len(unmatched_dependencies) > 10:
                unmatched_str += f" (and {len(unmatched_dependencies) - 10} more)"
            logger.info(f"   🔍 Unmatched: {unmatched_str} ({len(unmatched_dependencies)} dependencies)")
        
        # Log source files
        if source_files:
            source_str = ", ".join(sorted(source_files)[:3])  # Show first 3 files
            if len(source_files) > 3:
                source_str += f" (and {len(source_files) - 3} more)"
            logger.info(f"   📁 Sources: {source_str}")
        
        # Summary statistics
        match_percentage = (total_dependencies - len(unmatched_dependencies)) / total_dependencies * 100 if total_dependencies > 0 else 0
        logger.info(f"   📊 Categories matched: {found_categories}/{len(category_matches)}, Dependencies categorized: {match_percentage:.1f}%")


# Global scanner service instance
scanner_service = ScannerService()