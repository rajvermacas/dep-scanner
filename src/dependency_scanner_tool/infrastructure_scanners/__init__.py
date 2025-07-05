"""Infrastructure scanners for the dependency scanner tool."""

from .base import BaseInfrastructureScanner, InfrastructureScannerRegistry
from .manager import InfrastructureScannerManager

# Stage 1: Terraform and Docker
from .terraform import TerraformScanner
from .docker import DockerScanner

# Stage 2: Kubernetes and Cloud SDK Detection
from .kubernetes import KubernetesScanner
from .cloud_sdk import CloudSDKDetector

# Stage 3: CI/CD Pipeline Detection
from .jenkins import JenkinsScanner
from .github_actions import GitHubActionsScanner
from .gitlab_ci import GitLabCIScanner

# Stage 4: Database and Messaging Detection
from .database import DatabaseScanner
from .messaging import MessagingScanner

# Stage 5: Advanced Cloud Provider Support
from .cloudformation import CloudFormationScanner
from .arm_template import ARMTemplateScanner
from .gcp_deployment import GCPDeploymentScanner

__all__ = [
    "BaseInfrastructureScanner",
    "InfrastructureScannerRegistry",
    "InfrastructureScannerManager",
    # Stage 1
    "TerraformScanner",
    "DockerScanner",
    # Stage 2
    "KubernetesScanner",
    "CloudSDKDetector",
    # Stage 3
    "JenkinsScanner",
    "GitHubActionsScanner",
    "GitLabCIScanner",
    # Stage 4
    "DatabaseScanner",
    "MessagingScanner",
    # Stage 5
    "CloudFormationScanner",
    "ARMTemplateScanner",
    "GCPDeploymentScanner",
]