"""GitLab CI pipeline scanner for detecting CI/CD configurations."""

import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class GitLabCIScanner(BaseInfrastructureScanner):
    """Scanner for GitLab CI pipeline configurations."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return list of file patterns this scanner can handle."""
        return [
            ".gitlab-ci.yml",
            ".gitlab-ci.yaml"
        ]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.CICD
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file for GitLab CI pipeline configurations."""
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            component = self._parse_pipeline(content, str(file_path))
            return [component]
        
        except Exception as e:
            logger.error(f"Error reading GitLab CI pipeline file {file_path}: {e}")
            return []
    
    def _parse_pipeline(self, content: str, source_file: str) -> InfrastructureComponent:
        """Parse GitLab CI pipeline content and extract configuration."""
        try:
            # Parse YAML content
            pipeline_data = yaml.safe_load(content)
            
            if pipeline_data is None:
                pipeline_data = {}
            
            # Determine subtype based on content
            subtype = "pipeline" if pipeline_data else "unknown"
            
            # Build configuration
            configuration = {}
            
            # Extract global configuration
            if "stages" in pipeline_data:
                configuration["stages"] = pipeline_data["stages"]
            
            if "variables" in pipeline_data:
                configuration["variables"] = pipeline_data["variables"]
            
            if "image" in pipeline_data:
                configuration["image"] = pipeline_data["image"]
            
            if "services" in pipeline_data:
                configuration["services"] = pipeline_data["services"]
            
            if "cache" in pipeline_data:
                configuration["cache"] = pipeline_data["cache"]
            
            if "include" in pipeline_data:
                configuration["include"] = pipeline_data["include"]
            
            if "before_script" in pipeline_data:
                configuration["before_script"] = pipeline_data["before_script"]
            
            if "after_script" in pipeline_data:
                configuration["after_script"] = pipeline_data["after_script"]
            
            # Extract jobs (everything that's not a global keyword)
            global_keywords = {
                "stages", "variables", "image", "services", "cache", "include",
                "before_script", "after_script", "default", "workflow"
            }
            
            jobs = {}
            for key, value in pipeline_data.items():
                if key not in global_keywords and isinstance(value, dict):
                    jobs[key] = value
            
            if jobs:
                configuration["jobs"] = jobs
            
            return InfrastructureComponent(
                type=InfrastructureType.CICD,
                name="gitlab-ci-pipeline",
                service="gitlab-ci",
                subtype=subtype,
                configuration=configuration,
                source_file=source_file,
                classification=DependencyType.UNKNOWN,
                metadata={
                    "job_count": len(jobs),
                    "stage_count": len(pipeline_data.get("stages", [])),
                    "file_size": len(content),
                    "includes_count": len(pipeline_data.get("include", [])),
                    "services_used": self._extract_services(pipeline_data)
                }
            )
        
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML in {source_file}: {e}")
            return InfrastructureComponent(
                type=InfrastructureType.CICD,
                name="gitlab-ci-pipeline",
                service="gitlab-ci",
                subtype="unknown",
                configuration={"raw_content": content[:500]},
                source_file=source_file,
                classification=DependencyType.UNKNOWN,
                metadata={
                    "file_size": len(content),
                    "parse_error": str(e)
                }
            )
        
        except Exception as e:
            logger.error(f"Unexpected error parsing pipeline {source_file}: {e}")
            return InfrastructureComponent(
                type=InfrastructureType.CICD,
                name="gitlab-ci-pipeline",
                service="gitlab-ci",
                subtype="unknown",
                configuration={"raw_content": content[:500]},
                source_file=source_file,
                classification=DependencyType.UNKNOWN,
                metadata={
                    "file_size": len(content),
                    "parse_error": str(e)
                }
            )
    
    def _extract_services(self, pipeline_data: Dict[str, Any]) -> List[str]:
        """Extract all services used in the pipeline."""
        services = []
        
        # Global services
        if "services" in pipeline_data and isinstance(pipeline_data["services"], list):
            services.extend(pipeline_data["services"])
        
        # Job-specific services
        global_keywords = {
            "stages", "variables", "image", "services", "cache", "include",
            "before_script", "after_script", "default", "workflow"
        }
        
        for key, value in pipeline_data.items():
            if key not in global_keywords and isinstance(value, dict):
                job_services = value.get("services", [])
                if isinstance(job_services, list):
                    services.extend(job_services)
        
        return list(set(services))  # Remove duplicates