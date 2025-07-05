"""GitHub Actions workflow scanner for detecting CI/CD configurations."""

import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class GitHubActionsScanner(BaseInfrastructureScanner):
    """Scanner for GitHub Actions workflow configurations."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return list of file patterns this scanner can handle."""
        return [
            ".github/workflows/*.yml",
            ".github/workflows/*.yaml"
        ]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.CICD
    
    def can_handle_file(self, file_path: Path) -> bool:
        """Check if this scanner can handle the given file."""
        # Check if file is in .github/workflows/ directory and has yaml extension
        path_str = str(file_path)
        return (
            ".github/workflows/" in path_str and 
            (path_str.endswith(".yml") or path_str.endswith(".yaml"))
        )
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file for GitHub Actions workflow configurations."""
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            component = self._parse_workflow(content, str(file_path))
            return [component]
        
        except Exception as e:
            logger.error(f"Error reading GitHub Actions workflow file {file_path}: {e}")
            return []
    
    def _parse_workflow(self, content: str, source_file: str) -> InfrastructureComponent:
        """Parse GitHub Actions workflow content and extract configuration."""
        try:
            # Parse YAML content
            workflow_data = yaml.safe_load(content)
            
            if workflow_data is None:
                workflow_data = {}
            
            # Extract workflow name
            workflow_name = workflow_data.get("name", "github-actions-workflow")
            
            # Determine subtype based on content
            subtype = "workflow" if workflow_data else "unknown"
            
            # Build configuration
            configuration = {}
            
            # Extract trigger events (handle YAML parsing quirk where 'on:' becomes True)
            if "on" in workflow_data:
                configuration["on"] = workflow_data["on"]
            elif True in workflow_data:
                # YAML parser converts 'on:' to True in some cases
                configuration["on"] = workflow_data[True]
            
            # Extract global environment variables
            if "env" in workflow_data:
                configuration["env"] = workflow_data["env"]
            
            # Extract jobs
            if "jobs" in workflow_data:
                configuration["jobs"] = workflow_data["jobs"]
            
            # Extract permissions
            if "permissions" in workflow_data:
                configuration["permissions"] = workflow_data["permissions"]
            
            # Extract defaults
            if "defaults" in workflow_data:
                configuration["defaults"] = workflow_data["defaults"]
            
            return InfrastructureComponent(
                type=InfrastructureType.CICD,
                name=workflow_name,
                service="github-actions",
                subtype=subtype,
                configuration=configuration,
                source_file=source_file,
                classification=DependencyType.UNKNOWN,
                metadata={
                    "job_count": len(workflow_data.get("jobs", {})),
                    "file_size": len(content),
                    "triggers": self._extract_triggers(workflow_data.get("on", workflow_data.get(True, {}))),
                    "actions_used": self._extract_actions(workflow_data.get("jobs", {}))
                }
            )
        
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML in {source_file}: {e}")
            return InfrastructureComponent(
                type=InfrastructureType.CICD,
                name="github-actions-workflow",
                service="github-actions",
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
            logger.error(f"Unexpected error parsing workflow {source_file}: {e}")
            return InfrastructureComponent(
                type=InfrastructureType.CICD,
                name="github-actions-workflow",
                service="github-actions",
                subtype="unknown",
                configuration={"raw_content": content[:500]},
                source_file=source_file,
                classification=DependencyType.UNKNOWN,
                metadata={
                    "file_size": len(content),
                    "parse_error": str(e)
                }
            )
    
    def _extract_triggers(self, on_config: Any) -> List[str]:
        """Extract trigger events from the 'on' configuration."""
        triggers = []
        
        if isinstance(on_config, str):
            triggers.append(on_config)
        elif isinstance(on_config, list):
            triggers.extend(on_config)
        elif isinstance(on_config, dict):
            triggers.extend(on_config.keys())
        
        return triggers
    
    def _extract_actions(self, jobs_config: Dict[str, Any]) -> List[str]:
        """Extract all actions used in the workflow jobs."""
        actions = []
        
        for job_name, job_config in jobs_config.items():
            if isinstance(job_config, dict) and "steps" in job_config:
                for step in job_config["steps"]:
                    if isinstance(step, dict) and "uses" in step:
                        actions.append(step["uses"])
        
        return list(set(actions))  # Remove duplicates