"""Jenkins pipeline scanner for detecting Jenkins configurations."""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class JenkinsScanner(BaseInfrastructureScanner):
    """Scanner for Jenkins pipeline configurations."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return list of file patterns this scanner can handle."""
        return [
            "Jenkinsfile",
            "Jenkinsfile.*",
            "*.jenkins"
        ]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.CICD
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file for Jenkins pipeline configurations."""
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            component = self._parse_jenkinsfile(content, str(file_path))
            return [component]
        
        except Exception as e:
            logger.error(f"Error reading Jenkins file {file_path}: {e}")
            return []
    
    def _parse_jenkinsfile(self, content: str, source_file: str) -> InfrastructureComponent:
        """Parse Jenkinsfile content and extract pipeline information."""
        configuration = {}
        
        # Determine pipeline type
        if "pipeline {" in content:
            pipeline_type = "declarative"
            configuration = self._parse_declarative_pipeline(content)
        elif "node {" in content or "node(" in content:
            pipeline_type = "scripted"
            configuration = self._parse_scripted_pipeline(content)
        else:
            pipeline_type = "unknown"
            configuration = {"raw_content": content[:500]}  # First 500 chars for analysis
        
        return InfrastructureComponent(
            type=InfrastructureType.CICD,
            name="jenkins-pipeline",
            service="jenkins",
            subtype=pipeline_type,
            configuration=configuration,
            source_file=source_file,
            classification=DependencyType.UNKNOWN,
            metadata={
                "pipeline_type": pipeline_type,
                "file_size": len(content)
            }
        )
    
    def _parse_declarative_pipeline(self, content: str) -> Dict[str, Any]:
        """Parse declarative pipeline syntax."""
        config = {}
        
        # Extract agent configuration
        agent_match = re.search(r'agent\s+(\w+)', content)
        if agent_match:
            config["agent"] = agent_match.group(1)
        
        # Extract stages
        stages = self._extract_stages(content)
        if stages:
            config["stages"] = stages
        
        # Extract tools
        tools = self._extract_tools(content)
        if tools:
            config["tools"] = tools
        
        # Extract environment variables
        environment = self._extract_environment(content)
        if environment:
            config["environment"] = environment
        
        return config
    
    def _parse_scripted_pipeline(self, content: str) -> Dict[str, Any]:
        """Parse scripted pipeline syntax."""
        config = {}
        
        # Extract stages from scripted pipeline
        stages = self._extract_stages(content)
        if stages:
            config["stages"] = stages
        
        return config
    
    def _extract_stages(self, content: str) -> List[str]:
        """Extract stage names from pipeline content."""
        stages = []
        
        # Pattern to match stage declarations
        stage_pattern = r"stage\s*\(\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(stage_pattern, content)
        
        for match in matches:
            stages.append(match)
        
        return stages
    
    def _extract_tools(self, content: str) -> Dict[str, str]:
        """Extract tools configuration from declarative pipeline."""
        tools = {}
        
        # Find tools block
        tools_match = re.search(r'tools\s*\{([^}]+)\}', content, re.DOTALL)
        if tools_match:
            tools_content = tools_match.group(1)
            
            # Extract tool declarations
            tool_pattern = r'(\w+)\s+[\'"]([^\'"]+)[\'"]'
            tool_matches = re.findall(tool_pattern, tools_content)
            
            for tool_type, tool_version in tool_matches:
                tools[tool_type] = tool_version
        
        return tools
    
    def _extract_environment(self, content: str) -> Dict[str, str]:
        """Extract environment variables from declarative pipeline."""
        environment = {}
        
        # Find environment block
        env_match = re.search(r'environment\s*\{([^}]+)\}', content, re.DOTALL)
        if env_match:
            env_content = env_match.group(1)
            
            # Extract environment variable declarations
            env_pattern = r'(\w+)\s*=\s*[\'"]([^\'"]+)[\'"]'
            env_matches = re.findall(env_pattern, env_content)
            
            for var_name, var_value in env_matches:
                environment[var_name] = var_value
        
        return environment