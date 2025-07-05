"""Infrastructure data models for the dependency scanner tool."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

from dependency_scanner_tool.scanner import DependencyType, Dependency


class InfrastructureType(Enum):
    """Enumeration for infrastructure component types."""
    IaC = "iac"
    CONTAINER = "container"
    CLOUD = "cloud"
    CICD = "cicd"
    DATABASE = "database"
    MESSAGING = "messaging"
    MONITORING = "monitoring"
    SECURITY = "security"


@dataclass
class InfrastructureComponent:
    """Represents an infrastructure component detected in the project."""
    type: InfrastructureType
    name: str
    service: str  # terraform, docker, aws, jenkins, etc.
    subtype: str  # resource type, service name, etc.
    configuration: Dict[str, Any]
    source_file: str
    line_number: Optional[int] = None
    classification: DependencyType = DependencyType.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CloudResource:
    """Represents a cloud resource detected in infrastructure configurations."""
    provider: str  # aws, azure, gcp
    service: str  # ec2, s3, vm, storage, etc.
    resource_type: str  # instance, bucket, database, etc.
    configuration: Dict[str, Any]
    region: Optional[str] = None
    estimated_cost_tier: Optional[str] = None  # free, low, medium, high
    compliance_tags: List[str] = field(default_factory=list)  # gdpr, hipaa, pci-dss, etc.


@dataclass
class TechnologyStack:
    """Represents the complete technology stack detected in a project."""
    programming_languages: Dict[str, float]  # Existing capability
    dependencies: List[Dependency]  # Existing capability
    infrastructure_components: List[InfrastructureComponent] = field(default_factory=list)
    cloud_resources: List[CloudResource] = field(default_factory=list)
    detected_services: Dict[str, List[str]] = field(default_factory=dict)
    security_findings: List[Any] = field(default_factory=list)  # Will be defined later
    compliance_mappings: Dict[str, List[str]] = field(default_factory=dict)