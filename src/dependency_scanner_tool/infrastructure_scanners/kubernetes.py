"""Kubernetes infrastructure scanner for detecting Kubernetes manifests."""

import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent,
    DependencyType
)


logger = logging.getLogger(__name__)


class KubernetesScanner(BaseInfrastructureScanner):
    """Scanner for Kubernetes YAML manifests."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return list of file patterns this scanner can handle."""
        return [
            "*.yaml",
            "*.yml",
            "kustomization.yaml",
            "kustomization.yml"
        ]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.CONTAINER
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file for Kubernetes infrastructure components."""
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            return self._parse_kubernetes_content(content, str(file_path))
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []
    
    def _parse_kubernetes_content(self, content: str, source_file: str) -> List[InfrastructureComponent]:
        """Parse Kubernetes YAML content and extract components."""
        components = []
        
        try:
            # Handle multiple documents separated by ---
            documents = yaml.safe_load_all(content)
            
            for doc in documents:
                if doc and isinstance(doc, dict):
                    component = self._parse_kubernetes_document(doc, source_file)
                    if component:
                        components.append(component)
        
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML in {source_file}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing {source_file}: {e}")
        
        return components
    
    def _parse_kubernetes_document(self, doc: Dict[str, Any], source_file: str) -> InfrastructureComponent:
        """Parse a single Kubernetes document."""
        # Check if this is a Kubernetes resource
        if not self._is_kubernetes_resource(doc):
            return None
        
        try:
            api_version = doc.get("apiVersion", "")
            kind = doc.get("kind", "")
            metadata = doc.get("metadata", {})
            name = metadata.get("name", f"unnamed-{kind.lower()}")
            
            # Create infrastructure component
            component = InfrastructureComponent(
                type=InfrastructureType.CONTAINER,
                name=name,
                service="kubernetes",
                subtype=kind,
                configuration=doc,
                source_file=source_file,
                classification=DependencyType.UNKNOWN,
                metadata={
                    "api_version": api_version,
                    "namespace": metadata.get("namespace", "default"),
                    "labels": metadata.get("labels", {}),
                    "annotations": metadata.get("annotations", {}),
                }
            )
            
            return component
        
        except Exception as e:
            logger.error(f"Error parsing Kubernetes document in {source_file}: {e}")
            return None
    
    def _is_kubernetes_resource(self, doc: Dict[str, Any]) -> bool:
        """Check if a document is a Kubernetes resource."""
        # Must have apiVersion and kind
        if "apiVersion" not in doc or "kind" not in doc:
            return False
        
        # Common Kubernetes apiVersion patterns
        api_version = doc["apiVersion"]
        kind = doc["kind"]
        
        # Known Kubernetes API versions
        kubernetes_api_versions = [
            "v1",
            "apps/v1",
            "batch/v1",
            "networking.k8s.io/v1",
            "rbac.authorization.k8s.io/v1",
            "storage.k8s.io/v1",
            "apiextensions.k8s.io/v1",
            "networking.k8s.io/v1beta1",
            "policy/v1beta1",
        ]
        
        # Check for exact match or pattern match
        if api_version in kubernetes_api_versions:
            return True
        
        # Check for additional patterns (e.g., custom resources)
        if any(pattern in api_version for pattern in ["k8s.io", "kubernetes.io"]):
            return True
        
        # Common Kubernetes resource kinds
        kubernetes_kinds = [
            "Pod", "Service", "Deployment", "ReplicaSet", "StatefulSet",
            "DaemonSet", "Job", "CronJob", "ConfigMap", "Secret",
            "Ingress", "NetworkPolicy", "ServiceAccount", "Role",
            "RoleBinding", "ClusterRole", "ClusterRoleBinding",
            "PersistentVolume", "PersistentVolumeClaim", "StorageClass",
            "Namespace", "LimitRange", "ResourceQuota", "HorizontalPodAutoscaler",
            "VerticalPodAutoscaler", "PodDisruptionBudget", "CustomResourceDefinition"
        ]
        
        # If kind is recognized as Kubernetes, it's likely a valid resource
        if kind in kubernetes_kinds:
            return True
        
        return False