"""GCP Deployment Manager scanner for Google Cloud Infrastructure as Code detection."""

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


class GCPDeploymentScanner(BaseInfrastructureScanner):
    """Scanner for Google Cloud Platform Deployment Manager templates."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return supported file patterns for GCP Deployment Manager files."""
        return ["*.yaml", "*.yml", "deployment.yaml", "*.jinja"]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.IaC
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a GCP Deployment Manager file for infrastructure components."""
        try:
            if not file_path.exists():
                logger.warning(f"GCP deployment file does not exist: {file_path}")
                return []
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning(f"GCP deployment file is empty: {file_path}")
                return []
            
            # Skip Jinja templates for now (they require rendering)
            if file_path.suffix.lower() == '.jinja':
                logger.info(f"Skipping Jinja template file: {file_path}")
                return []
            
            # Parse the YAML content
            deployment_data = self._parse_deployment_content(content, file_path)
            
            if not deployment_data:
                return []
            
            # Validate it's a GCP Deployment Manager template
            if not self._is_gcp_deployment(deployment_data):
                return []
            
            return self._extract_components(deployment_data, file_path)
                
        except Exception as e:
            logger.error(f"Error scanning GCP deployment file {file_path}: {e}")
            return []
    
    def _parse_deployment_content(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse GCP deployment YAML content."""
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing GCP deployment YAML {file_path}: {e}")
            return None
    
    def _is_gcp_deployment(self, deployment_data: Dict[str, Any]) -> bool:
        """Check if the parsed data is a GCP Deployment Manager template."""
        if not isinstance(deployment_data, dict):
            return False
        
        # Check for GCP Deployment Manager-specific keys
        gcp_keys = ["resources", "imports", "outputs"]
        
        # Must have at least resources section
        if "resources" not in deployment_data:
            return False
        
        resources = deployment_data.get("resources", [])
        if isinstance(resources, list) and resources:
            # Check if resources have GCP-specific resource types
            for resource in resources:
                if isinstance(resource, dict) and "type" in resource:
                    resource_type = resource["type"]
                    # GCP resource types typically have format like "compute.v1.instance", "storage.v1.bucket"
                    if self._is_gcp_resource_type(resource_type):
                        return True
        
        # Check if it has imports (common in GCP deployments)
        if "imports" in deployment_data:
            return True
        
        return False
    
    def _is_gcp_resource_type(self, resource_type: str) -> bool:
        """Check if the resource type is a GCP resource type."""
        # GCP resource types typically follow patterns like:
        # - compute.v1.instance
        # - storage.v1.bucket
        # - sqladmin.v1beta4.instance
        # - cloudfunctions.v1.function
        gcp_services = [
            "compute.", "storage.", "sqladmin.", "cloudfunctions.", "container.",
            "appengine.", "pubsub.", "bigquery.", "cloudresourcemanager.",
            "iam.", "dns.", "dataflow.", "dataproc.", "monitoring.",
            "logging.", "deploymentmanager."
        ]
        
        return any(resource_type.startswith(service) for service in gcp_services)
    
    def _extract_components(self, deployment_data: Dict[str, Any], file_path: Path) -> List[InfrastructureComponent]:
        """Extract infrastructure components from GCP deployment."""
        components = []
        
        # Extract resources (main components)
        if "resources" in deployment_data:
            resource_components = self._extract_resources(deployment_data["resources"], file_path)
            components.extend(resource_components)
        
        # Extract imports as configuration components
        if "imports" in deployment_data and deployment_data["imports"]:
            import_component = self._extract_imports(deployment_data["imports"], file_path)
            if import_component:
                components.append(import_component)
        
        # Extract outputs as configuration components
        if "outputs" in deployment_data and deployment_data["outputs"]:
            output_component = self._extract_outputs(deployment_data["outputs"], file_path)
            if output_component:
                components.append(output_component)
        
        return components
    
    def _extract_resources(self, resources: List[Dict[str, Any]], file_path: Path) -> List[InfrastructureComponent]:
        """Extract resource components from GCP deployment resources section."""
        components = []
        
        if not isinstance(resources, list):
            logger.warning(f"GCP deployment resources section is not a list in {file_path}")
            return components
        
        for resource in resources:
            if not isinstance(resource, dict) or "type" not in resource or "name" not in resource:
                continue
            
            # Extract resource name
            resource_name = resource["name"]
            
            component = InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name=resource_name,
                service="gcp-deployment",
                subtype=resource["type"],
                configuration=resource,
                source_file=str(file_path),
                classification=DependencyType.UNKNOWN,
                metadata={
                    "gcp_resource_type": resource["type"],
                    "has_properties": "properties" in resource,
                    "has_metadata": "metadata" in resource
                }
            )
            components.append(component)
        
        return components
    
    def _extract_imports(self, imports: List[Dict[str, Any]], file_path: Path) -> Optional[InfrastructureComponent]:
        """Extract imports as a single configuration component."""
        if not imports:
            return None
        
        return InfrastructureComponent(
            type=self.get_infrastructure_type(),
            name="Imports",
            service="gcp-deployment",
            subtype="imports",
            configuration={"imports": imports},
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={
                "import_count": len(imports),
                "import_paths": [imp.get("path", "") for imp in imports if isinstance(imp, dict)]
            }
        )
    
    def _extract_outputs(self, outputs: List[Dict[str, Any]], file_path: Path) -> Optional[InfrastructureComponent]:
        """Extract outputs as a single configuration component."""
        if not outputs:
            return None
        
        return InfrastructureComponent(
            type=self.get_infrastructure_type(),
            name="Outputs",
            service="gcp-deployment",
            subtype="outputs",
            configuration={"outputs": outputs},
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={
                "output_count": len(outputs),
                "output_names": [out.get("name", "") for out in outputs if isinstance(out, dict)]
            }
        )