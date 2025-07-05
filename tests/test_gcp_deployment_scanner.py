"""Test cases for GCP Deployment Manager scanner."""
import pytest
import tempfile
import yaml
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.gcp_deployment import GCPDeploymentScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType


def test_gcp_deployment_scanner_initialization():
    """Test GCPDeploymentScanner initialization."""
    scanner = GCPDeploymentScanner()
    
    assert scanner.get_infrastructure_type() == InfrastructureType.IaC
    supported_patterns = scanner.get_supported_file_patterns()
    assert "*.yaml" in supported_patterns
    assert "*.yml" in supported_patterns
    assert "deployment.yaml" in supported_patterns
    assert "*.jinja" in supported_patterns


def test_gcp_deployment_scanner_can_handle_file():
    """Test GCPDeploymentScanner file handling."""
    scanner = GCPDeploymentScanner()
    
    assert scanner.can_handle_file(Path("deployment.yaml")) is True
    assert scanner.can_handle_file(Path("infrastructure.yml")) is True
    assert scanner.can_handle_file(Path("template.jinja")) is True
    assert scanner.can_handle_file(Path("gcp-config.yaml")) is True
    assert scanner.can_handle_file(Path("test.txt")) is False
    assert scanner.can_handle_file(Path("main.tf")) is False


def test_gcp_deployment_scanner_basic_compute_instance():
    """Test scanning basic GCP Compute Engine instance."""
    scanner = GCPDeploymentScanner()
    
    gcp_deployment = {
        "resources": [
            {
                "name": "vm-instance",
                "type": "compute.v1.instance",
                "properties": {
                    "zone": "us-central1-a",
                    "machineType": "projects/my-project/zones/us-central1-a/machineTypes/f1-micro",
                    "disks": [
                        {
                            "boot": True,
                            "autoDelete": True,
                            "initializeParams": {
                                "sourceImage": "projects/debian-cloud/global/images/family/debian-11"
                            }
                        }
                    ],
                    "networkInterfaces": [
                        {
                            "network": "projects/my-project/global/networks/default"
                        }
                    ]
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(gcp_deployment, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.IaC
        assert component.name == "vm-instance"
        assert component.service == "gcp-deployment"
        assert component.subtype == "compute.v1.instance"
        assert component.configuration["properties"]["zone"] == "us-central1-a"


def test_gcp_deployment_scanner_storage_bucket():
    """Test scanning GCP Cloud Storage bucket."""
    scanner = GCPDeploymentScanner()
    
    gcp_deployment = {
        "resources": [
            {
                "name": "my-storage-bucket",
                "type": "storage.v1.bucket",
                "properties": {
                    "location": "US",
                    "storageClass": "STANDARD",
                    "versioning": {
                        "enabled": True
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(gcp_deployment, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.name == "my-storage-bucket"
        assert component.subtype == "storage.v1.bucket"
        assert component.configuration["properties"]["storageClass"] == "STANDARD"


def test_gcp_deployment_scanner_multiple_resources():
    """Test scanning GCP deployment with multiple resources."""
    scanner = GCPDeploymentScanner()
    
    gcp_deployment = {
        "resources": [
            {
                "name": "my-network",
                "type": "compute.v1.network",
                "properties": {
                    "autoCreateSubnetworks": False,
                    "routingConfig": {
                        "routingMode": "REGIONAL"
                    }
                }
            },
            {
                "name": "my-firewall",
                "type": "compute.v1.firewall",
                "properties": {
                    "network": "$(ref.my-network.selfLink)",
                    "allowed": [
                        {
                            "IPProtocol": "tcp",
                            "ports": ["80", "443"]
                        }
                    ]
                }
            },
            {
                "name": "my-sql-instance",
                "type": "sqladmin.v1beta4.instance",
                "properties": {
                    "databaseVersion": "MYSQL_8_0",
                    "tier": "db-f1-micro",
                    "region": "us-central1"
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(gcp_deployment, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 3
        resource_names = [comp.name for comp in components]
        assert "my-network" in resource_names
        assert "my-firewall" in resource_names
        assert "my-sql-instance" in resource_names


def test_gcp_deployment_scanner_with_imports():
    """Test scanning GCP deployment with imports."""
    scanner = GCPDeploymentScanner()
    
    gcp_deployment = {
        "imports": [
            {
                "path": "templates/vm_template.jinja",
                "name": "vm-template"
            },
            {
                "path": "schemas/vm_schema.jinja.schema"
            }
        ],
        "resources": [
            {
                "name": "my-vm",
                "type": "vm-template",
                "properties": {
                    "zone": "us-west1-a",
                    "machineType": "n1-standard-1"
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(gcp_deployment, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should detect imports and resources
        assert len(components) >= 1
        
        # Check that we have the resource
        resource_components = [c for c in components if c.subtype == "vm-template"]
        assert len(resource_components) == 1


def test_gcp_deployment_scanner_app_engine():
    """Test scanning GCP App Engine configuration."""
    scanner = GCPDeploymentScanner()
    
    gcp_deployment = {
        "resources": [
            {
                "name": "my-app-engine-app",
                "type": "appengine.v1.application",
                "properties": {
                    "id": "my-project-id",
                    "locationId": "us-central"
                }
            },
            {
                "name": "my-app-engine-version",
                "type": "appengine.v1.version",
                "properties": {
                    "service": "default",
                    "runtime": "python39",
                    "entrypoint": {
                        "shell": "gunicorn -b :$PORT main:app"
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(gcp_deployment, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 2
        resource_types = [comp.subtype for comp in components]
        assert "appengine.v1.application" in resource_types
        assert "appengine.v1.version" in resource_types


def test_gcp_deployment_scanner_invalid_yaml():
    """Test scanning invalid YAML GCP deployment file."""
    scanner = GCPDeploymentScanner()
    
    invalid_yaml = """
resources:
  - name: test
    type: invalid yaml content
      missing proper structure
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(invalid_yaml)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for invalid files
        assert components == []


def test_gcp_deployment_scanner_empty_file():
    """Test scanning empty GCP deployment file."""
    scanner = GCPDeploymentScanner()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("")
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for empty files
        assert components == []


def test_gcp_deployment_scanner_non_gcp_yaml():
    """Test scanning non-GCP deployment YAML file."""
    scanner = GCPDeploymentScanner()
    
    non_gcp_yaml = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "test-pod"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(non_gcp_yaml, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for non-GCP deployment files
        assert components == []


def test_gcp_deployment_scanner_cloud_functions():
    """Test scanning GCP Cloud Functions deployment."""
    scanner = GCPDeploymentScanner()
    
    gcp_deployment = {
        "resources": [
            {
                "name": "my-cloud-function",
                "type": "cloudfunctions.v1.function",
                "properties": {
                    "location": "us-central1",
                    "sourceArchiveUrl": "gs://my-bucket/function-source.zip",
                    "entryPoint": "hello_world",
                    "runtime": "python39",
                    "httpsTrigger": {}
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(gcp_deployment, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.name == "my-cloud-function"
        assert component.subtype == "cloudfunctions.v1.function"
        assert component.configuration["properties"]["runtime"] == "python39"


def test_gcp_deployment_scanner_kubernetes_cluster():
    """Test scanning GCP GKE cluster deployment."""
    scanner = GCPDeploymentScanner()
    
    gcp_deployment = {
        "resources": [
            {
                "name": "my-gke-cluster",
                "type": "container.v1.cluster",
                "properties": {
                    "zone": "us-central1-a",
                    "initialNodeCount": 3,
                    "nodeConfig": {
                        "machineType": "e2-medium",
                        "diskSizeGb": 100,
                        "oauthScopes": [
                            "https://www.googleapis.com/auth/cloud-platform"
                        ]
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(gcp_deployment, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.name == "my-gke-cluster"
        assert component.subtype == "container.v1.cluster"
        assert component.configuration["properties"]["initialNodeCount"] == 3


def test_gcp_deployment_scanner_file_not_found():
    """Test scanning non-existent file."""
    scanner = GCPDeploymentScanner()
    
    components = scanner.scan_file(Path("/non/existent/file.yaml"))
    
    # Should return empty list for non-existent files
    assert components == []


def test_gcp_deployment_scanner_complex_deployment():
    """Test scanning complex GCP deployment with multiple resource types."""
    scanner = GCPDeploymentScanner()
    
    gcp_deployment = {
        "imports": [
            {
                "path": "templates/network.jinja"
            }
        ],
        "resources": [
            {
                "name": "my-pubsub-topic",
                "type": "pubsub.v1.topic",
                "properties": {
                    "topic": "my-topic"
                }
            },
            {
                "name": "my-big-query-dataset",
                "type": "bigquery.v2.dataset",
                "properties": {
                    "datasetId": "my_dataset",
                    "location": "US"
                }
            },
            {
                "name": "my-iam-policy",
                "type": "cloudresourcemanager.v1.projectIamPolicy",
                "properties": {
                    "resource": "my-project-id",
                    "bindings": [
                        {
                            "role": "roles/viewer",
                            "members": ["user:test@example.com"]
                        }
                    ]
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(gcp_deployment, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) >= 3
        
        # Verify all resource types are detected
        resource_types = [comp.subtype for comp in components if comp.subtype.startswith(('pubsub', 'bigquery', 'cloudresourcemanager'))]
        assert "pubsub.v1.topic" in resource_types
        assert "bigquery.v2.dataset" in resource_types
        assert "cloudresourcemanager.v1.projectIamPolicy" in resource_types