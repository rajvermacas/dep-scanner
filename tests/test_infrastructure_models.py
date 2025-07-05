"""Test cases for infrastructure data models."""
import pytest
from enum import Enum
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent,
    CloudResource,
    TechnologyStack
)
from dependency_scanner_tool.scanner import DependencyType, Dependency


def test_infrastructure_type_enum():
    """Test InfrastructureType enum values."""
    assert InfrastructureType.IaC.value == "iac"
    assert InfrastructureType.CONTAINER.value == "container"
    assert InfrastructureType.CLOUD.value == "cloud"
    assert InfrastructureType.CICD.value == "cicd"
    assert InfrastructureType.DATABASE.value == "database"
    assert InfrastructureType.MESSAGING.value == "messaging"
    assert InfrastructureType.MONITORING.value == "monitoring"
    assert InfrastructureType.SECURITY.value == "security"


def test_infrastructure_component_creation():
    """Test creating an InfrastructureComponent."""
    component = InfrastructureComponent(
        type=InfrastructureType.IaC,
        name="aws_instance",
        service="terraform",
        subtype="aws_instance",
        configuration={"instance_type": "t2.micro"},
        source_file="main.tf",
        line_number=10,
        classification=DependencyType.ALLOWED,
        metadata={"region": "us-west-2"}
    )
    
    assert component.type == InfrastructureType.IaC
    assert component.name == "aws_instance"
    assert component.service == "terraform"
    assert component.subtype == "aws_instance"
    assert component.configuration == {"instance_type": "t2.micro"}
    assert component.source_file == "main.tf"
    assert component.line_number == 10
    assert component.classification == DependencyType.ALLOWED
    assert component.metadata == {"region": "us-west-2"}


def test_infrastructure_component_defaults():
    """Test InfrastructureComponent with default values."""
    component = InfrastructureComponent(
        type=InfrastructureType.CONTAINER,
        name="nginx",
        service="docker",
        subtype="image",
        configuration={},
        source_file="Dockerfile"
    )
    
    assert component.line_number is None
    assert component.classification == DependencyType.UNKNOWN
    assert component.metadata == {}


def test_cloud_resource_creation():
    """Test creating a CloudResource."""
    resource = CloudResource(
        provider="aws",
        service="ec2",
        resource_type="instance",
        region="us-west-2",
        configuration={"instance_type": "t2.micro", "ami": "ami-12345678"},
        estimated_cost_tier="low",
        compliance_tags=["gdpr", "hipaa"]
    )
    
    assert resource.provider == "aws"
    assert resource.service == "ec2"
    assert resource.resource_type == "instance"
    assert resource.region == "us-west-2"
    assert resource.configuration == {"instance_type": "t2.micro", "ami": "ami-12345678"}
    assert resource.estimated_cost_tier == "low"
    assert resource.compliance_tags == ["gdpr", "hipaa"]


def test_cloud_resource_defaults():
    """Test CloudResource with default values."""
    resource = CloudResource(
        provider="azure",
        service="storage",
        resource_type="account",
        configuration={}
    )
    
    assert resource.region is None
    assert resource.estimated_cost_tier is None
    assert resource.compliance_tags == []


def test_technology_stack_creation():
    """Test creating a TechnologyStack."""
    dependency = Dependency(name="requests", version="2.28.0")
    infrastructure_component = InfrastructureComponent(
        type=InfrastructureType.CONTAINER,
        name="nginx",
        service="docker",
        subtype="image",
        configuration={},
        source_file="Dockerfile"
    )
    cloud_resource = CloudResource(
        provider="aws",
        service="s3",
        resource_type="bucket",
        configuration={"bucket_name": "my-bucket"}
    )
    
    stack = TechnologyStack(
        programming_languages={"python": 80.0, "javascript": 20.0},
        dependencies=[dependency],
        infrastructure_components=[infrastructure_component],
        cloud_resources=[cloud_resource],
        detected_services={"databases": ["postgresql"], "caches": ["redis"]},
        security_findings=[],
        compliance_mappings={"gdpr": ["encryption"]}
    )
    
    assert stack.programming_languages == {"python": 80.0, "javascript": 20.0}
    assert len(stack.dependencies) == 1
    assert stack.dependencies[0].name == "requests"
    assert len(stack.infrastructure_components) == 1
    assert stack.infrastructure_components[0].name == "nginx"
    assert len(stack.cloud_resources) == 1
    assert stack.cloud_resources[0].service == "s3"
    assert stack.detected_services == {"databases": ["postgresql"], "caches": ["redis"]}
    assert stack.security_findings == []
    assert stack.compliance_mappings == {"gdpr": ["encryption"]}


def test_technology_stack_defaults():
    """Test TechnologyStack with default values."""
    stack = TechnologyStack(
        programming_languages={},
        dependencies=[]
    )
    
    assert stack.infrastructure_components == []
    assert stack.cloud_resources == []
    assert stack.detected_services == {}
    assert stack.security_findings == []
    assert stack.compliance_mappings == {}