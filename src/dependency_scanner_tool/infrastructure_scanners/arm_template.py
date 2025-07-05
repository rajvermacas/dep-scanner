"""ARM template scanner for Azure Infrastructure as Code detection."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent
)
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class ARMTemplateScanner(BaseInfrastructureScanner):
    """Scanner for Azure Resource Manager (ARM) templates."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return supported file patterns for ARM template files."""
        return ["*.json", "azuredeploy.json", "mainTemplate.json"]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.IaC
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan an ARM template file for infrastructure components."""
        try:
            if not file_path.exists():
                logger.warning(f"ARM template file does not exist: {file_path}")
                return []
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning(f"ARM template file is empty: {file_path}")
                return []
            
            # Parse the JSON content
            template_data = self._parse_template_content(content, file_path)
            
            if not template_data:
                return []
            
            # Validate it's an ARM template
            if not self._is_arm_template(template_data):
                return []
            
            return self._extract_components(template_data, file_path)
                
        except Exception as e:
            logger.error(f"Error scanning ARM template file {file_path}: {e}")
            return []
    
    def _parse_template_content(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse ARM template JSON content."""
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing ARM template {file_path}: {e}")
            return None
    
    def _is_arm_template(self, template_data: Dict[str, Any]) -> bool:
        """Check if the parsed data is an ARM template."""
        if not isinstance(template_data, dict):
            return False
        
        # Check for ARM template-specific schema or properties
        schema = template_data.get("$schema", "")
        if "deploymentTemplate.json" in schema or "schema.management.azure.com" in schema:
            return True
        
        # Check for ARM-specific keys
        arm_keys = ["$schema", "contentVersion", "parameters", "variables", "resources", "outputs"]
        
        # Must have at least resources section or ARM schema
        if "resources" in template_data:
            # Additional check: if resources exist, look for Microsoft.* resource types
            resources = template_data.get("resources", [])
            if isinstance(resources, list) and resources:
                for resource in resources:
                    if isinstance(resource, dict) and "type" in resource:
                        if resource["type"].startswith("Microsoft."):
                            return True
        
        # Check if it has multiple ARM-like keys
        arm_key_count = sum(1 for key in arm_keys if key in template_data)
        return arm_key_count >= 3
    
    def _extract_components(self, template_data: Dict[str, Any], file_path: Path) -> List[InfrastructureComponent]:
        """Extract infrastructure components from ARM template."""
        components = []
        
        # Extract resources (main components)
        if "resources" in template_data:
            resource_components = self._extract_resources(template_data["resources"], file_path)
            components.extend(resource_components)
        
        # Extract parameters as configuration components
        if "parameters" in template_data and template_data["parameters"]:
            param_component = self._extract_parameters(template_data["parameters"], file_path)
            if param_component:
                components.append(param_component)
        
        # Extract variables as configuration components
        if "variables" in template_data and template_data["variables"]:
            var_component = self._extract_variables(template_data["variables"], file_path)
            if var_component:
                components.append(var_component)
        
        # Extract outputs as configuration components
        if "outputs" in template_data and template_data["outputs"]:
            output_component = self._extract_outputs(template_data["outputs"], file_path)
            if output_component:
                components.append(output_component)
        
        return components
    
    def _extract_resources(self, resources: List[Dict[str, Any]], file_path: Path) -> List[InfrastructureComponent]:
        """Extract resource components from ARM template resources section."""
        components = []
        
        if not isinstance(resources, list):
            logger.warning(f"ARM template resources section is not a list in {file_path}")
            return components
        
        for resource in resources:
            if not isinstance(resource, dict) or "type" not in resource or "name" not in resource:
                continue
            
            # Extract resource name (can be an expression like "[parameters('vmName')]")
            resource_name = resource["name"]
            if isinstance(resource_name, str) and resource_name.startswith("[") and resource_name.endswith("]"):
                # Simplify ARM expressions for display
                resource_name = resource_name.strip("[]")
            
            component = InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name=resource_name,
                service="arm-template",
                subtype=resource["type"],
                configuration=resource,
                source_file=str(file_path),
                classification=DependencyType.UNKNOWN,
                metadata={
                    "azure_resource_type": resource["type"],
                    "api_version": resource.get("apiVersion"),
                    "location": resource.get("location"),
                    "has_properties": "properties" in resource,
                    "has_depends_on": "dependsOn" in resource
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
            service="arm-template",
            subtype="parameters",
            configuration=parameters,
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={
                "parameter_count": len(parameters),
                "parameter_names": list(parameters.keys())
            }
        )
    
    def _extract_variables(self, variables: Dict[str, Any], file_path: Path) -> Optional[InfrastructureComponent]:
        """Extract variables as a single configuration component."""
        if not variables:
            return None
        
        return InfrastructureComponent(
            type=self.get_infrastructure_type(),
            name="Variables",
            service="arm-template",
            subtype="variables",
            configuration=variables,
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={
                "variable_count": len(variables),
                "variable_names": list(variables.keys())
            }
        )
    
    def _extract_outputs(self, outputs: Dict[str, Any], file_path: Path) -> Optional[InfrastructureComponent]:
        """Extract outputs as a single configuration component."""
        if not outputs:
            return None
        
        return InfrastructureComponent(
            type=self.get_infrastructure_type(),
            name="Outputs",
            service="arm-template",
            subtype="outputs",
            configuration=outputs,
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={
                "output_count": len(outputs),
                "output_names": list(outputs.keys())
            }
        )