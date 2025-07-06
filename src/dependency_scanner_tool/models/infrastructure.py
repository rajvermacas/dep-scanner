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


class SecurityFindingType(Enum):
    """Enumeration for security finding types."""
    SECRET = "secret"
    HARDCODED_PASSWORD = "hardcoded_password"
    API_KEY = "api_key"
    PRIVATE_KEY = "private_key"
    CERTIFICATE = "certificate"
    SENSITIVE_DATA = "sensitive_data"
    INSECURE_CONFIG = "insecure_config"
    DEPRECATED_TOOL = "deprecated_tool"
    VULNERABLE_DEPENDENCY = "vulnerable_dependency"


class SecuritySeverity(Enum):
    """Enumeration for security finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceFramework(Enum):
    """Enumeration for compliance frameworks."""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST = "nist"


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
    security_findings: List['SecurityFinding'] = field(default_factory=list)
    compliance_mappings: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class SecurityFinding:
    """Represents a security finding detected in the project."""
    finding_type: SecurityFindingType
    severity: SecuritySeverity
    title: str
    description: str
    source_file: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    matched_text: Optional[str] = None
    pattern: Optional[str] = None
    remediation: Optional[str] = None
    cve_id: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceViolation:
    """Represents a compliance violation detected in the project."""
    framework: ComplianceFramework
    rule_id: str
    title: str
    description: str
    severity: SecuritySeverity
    source_file: str
    line_number: Optional[int] = None
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityReport:
    """Represents a comprehensive security report for the project."""
    security_findings: List[SecurityFinding] = field(default_factory=list)
    compliance_violations: List[ComplianceViolation] = field(default_factory=list)
    security_tools_detected: List[str] = field(default_factory=list)
    secret_management_tools: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)