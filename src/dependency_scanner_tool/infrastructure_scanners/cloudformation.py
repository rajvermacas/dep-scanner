"""CloudFormation scanner for AWS Infrastructure as Code detection."""

import json
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent
)
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class CloudFormationScanner(BaseInfrastructureScanner):
    """Scanner for AWS CloudFormation templates."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return supported file patterns for CloudFormation files."""
        return ["*.template", "*.json", "*.yaml", "*.yml"]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.IaC
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a CloudFormation file for infrastructure components."""
        try:
            if not file_path.exists():
                logger.warning(f"CloudFormation file does not exist: {file_path}")
                return []
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning(f"CloudFormation file is empty: {file_path}")
                return []
            
            # Parse the content based on file extension
            template_data = self._parse_template_content(content, file_path)
            
            if not template_data:
                return []
            
            # Validate it's a CloudFormation template
            if not self._is_cloudformation_template(template_data):
                return []
            
            return self._extract_components(template_data, file_path)
                
        except Exception as e:
            logger.error(f"Error scanning CloudFormation file {file_path}: {e}")
            return []
    
    def _parse_template_content(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse template content based on file format."""
        try:
            if file_path.suffix.lower() in ['.json', '.template']:
                return json.loads(content)
            elif file_path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(content)
            else:
                # Try JSON first, then YAML
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return yaml.safe_load(content)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            logger.error(f"Error parsing CloudFormation template {file_path}: {e}")
            return None
    
    def _is_cloudformation_template(self, template_data: Dict[str, Any]) -> bool:
        """Check if the parsed data is a CloudFormation template."""
        if not isinstance(template_data, dict):
            return False
        
        # Check for CloudFormation-specific keys
        cf_keys = ["AWSTemplateFormatVersion", "Resources", "Parameters", "Outputs", "Mappings"]
        
        # Must have at least Resources section or AWSTemplateFormatVersion
        if "Resources" in template_data or "AWSTemplateFormatVersion" in template_data:
            return True
        
        # Check if it has multiple CloudFormation-like keys
        cf_key_count = sum(1 for key in cf_keys if key in template_data)
        return cf_key_count >= 2
    
    def _extract_components(self, template_data: Dict[str, Any], file_path: Path) -> List[InfrastructureComponent]:
        """Extract infrastructure components from CloudFormation template."""
        components = []
        
        # Extract resources (main components)
        if "Resources" in template_data:
            resource_components = self._extract_resources(template_data["Resources"], file_path)
            components.extend(resource_components)
        
        # Extract parameters as configuration components
        if "Parameters" in template_data:
            param_component = self._extract_parameters(template_data["Parameters"], file_path)
            if param_component:
                components.append(param_component)
        
        # Extract outputs as configuration components
        if "Outputs" in template_data:
            output_component = self._extract_outputs(template_data["Outputs"], file_path)
            if output_component:
                components.append(output_component)
        
        return components
    
    def _extract_resources(self, resources: Dict[str, Any], file_path: Path) -> List[InfrastructureComponent]:
        """Extract resource components from CloudFormation Resources section."""
        components = []
        
        for resource_name, resource_config in resources.items():
            if not isinstance(resource_config, dict) or "Type" not in resource_config:
                continue
            
            component = InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name=resource_name,
                service="cloudformation",
                subtype=resource_config["Type"],
                configuration=resource_config,
                source_file=str(file_path),
                classification=DependencyType.UNKNOWN,
                metadata={
                    "aws_resource_type": resource_config["Type"],
                    "has_properties": "Properties" in resource_config,
                    "has_metadata": "Metadata" in resource_config
                }
            )
            components.append(component)
        
        return components
    
    def _extract_parameters(self, parameters: Dict[str, Any], file_path: Path) -> Optional[InfrastructureComponent]:
        """Extract parameters as a single configuration component."""
        if not parameters:
            return None
        
        return InfrastructureComponent(
            type=self.get_infrastructure_type(),
            name="Parameters",
            service="cloudformation",
            subtype="parameters",
            configuration=parameters,
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={
                "parameter_count": len(parameters),
                "parameter_names": list(parameters.keys())
            }
        )
    
    def _extract_outputs(self, outputs: Dict[str, Any], file_path: Path) -> Optional[InfrastructureComponent]:
        """Extract outputs as a single configuration component."""
        if not outputs:
            return None
        
        return InfrastructureComponent(
            type=self.get_infrastructure_type(),
            name="Outputs",
            service="cloudformation",
            subtype="outputs",
            configuration=outputs,
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={
                "output_count": len(outputs),
                "output_names": list(outputs.keys())
            }
        )