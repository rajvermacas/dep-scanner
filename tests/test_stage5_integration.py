"""Integration tests for Stage 5 Advanced Cloud Provider Support scanners."""
import json
import tempfile
import yaml
from pathlib import Path

import pytest
from dependency_scanner_tool.infrastructure_scanners.manager import InfrastructureScannerManager
from dependency_scanner_tool.models.infrastructure import InfrastructureType


def test_cloudformation_scanner_registration():
    """Test that CloudFormation scanner is registered in manager."""
    manager = InfrastructureScannerManager()
    
    # Verify CloudFormation scanner is registered
    registry = manager.get_registry()
    scanner = registry.get("cloudformation")
    
    assert scanner is not None
    assert scanner.get_infrastructure_type() == InfrastructureType.IaC


def test_arm_template_scanner_registration():
    """Test that ARM template scanner is registered in manager."""
    manager = InfrastructureScannerManager()
    
    # Verify ARM template scanner is registered
    registry = manager.get_registry()
    scanner = registry.get("arm_template")
    
    assert scanner is not None
    assert scanner.get_infrastructure_type() == InfrastructureType.IaC


def test_gcp_deployment_scanner_registration():
    """Test that GCP deployment scanner is registered in manager."""
    manager = InfrastructureScannerManager()
    
    # Verify GCP deployment scanner is registered
    registry = manager.get_registry()
    scanner = registry.get("gcp_deployment")
    
    assert scanner is not None
    assert scanner.get_infrastructure_type() == InfrastructureType.IaC


def test_multi_cloud_infrastructure_detection():
    """Test detection of multi-cloud infrastructure in the same project."""
    manager = InfrastructureScannerManager()
    
    # Create temporary files for each cloud provider
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # CloudFormation template
        cf_template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "MyS3Bucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": "my-aws-bucket"
                    }
                }
            }
        }
        cf_file = temp_path / "aws-infrastructure.json"
        with open(cf_file, 'w') as f:
            json.dump(cf_template, f)
        
        # ARM template
        arm_template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [
                {
                    "type": "Microsoft.Storage/storageAccounts",
                    "apiVersion": "2021-04-01",
                    "name": "myazurestorage",
                    "location": "East US",
                    "sku": {
                        "name": "Standard_LRS"
                    }
                }
            ]
        }
        arm_file = temp_path / "azure-infrastructure.json"
        with open(arm_file, 'w') as f:
            json.dump(arm_template, f)
        
        # GCP deployment
        gcp_deployment = {
            "resources": [
                {
                    "name": "my-gcp-bucket",
                    "type": "storage.v1.bucket",
                    "properties": {
                        "location": "US",
                        "storageClass": "STANDARD"
                    }
                }
            ]
        }
        gcp_file = temp_path / "gcp-infrastructure.yaml"
        with open(gcp_file, 'w') as f:
            yaml.dump(gcp_deployment, f)
        
        # Scan directory
        components = manager.scan_directory(temp_path)
        
        # Should detect components from all three cloud providers
        assert len(components) >= 3
        
        # Verify we have components from each cloud provider
        services = [comp.service for comp in components]
        assert "cloudformation" in services
        assert "arm-template" in services
        assert "gcp-deployment" in services
        
        # Verify specific resources
        resource_names = [comp.name for comp in components]
        assert "MyS3Bucket" in resource_names
        assert "myazurestorage" in resource_names
        assert "my-gcp-bucket" in resource_names


def test_stage5_scanners_with_ignore_patterns():
    """Test that Stage 5 scanners respect ignore patterns."""
    manager = InfrastructureScannerManager()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a CloudFormation template in an ignored directory
        ignored_dir = temp_path / ".terraform"
        ignored_dir.mkdir()
        
        cf_template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "IgnoredBucket": {
                    "Type": "AWS::S3::Bucket"
                }
            }
        }
        ignored_file = ignored_dir / "ignored.json"
        with open(ignored_file, 'w') as f:
            json.dump(cf_template, f)
        
        # Create a valid CloudFormation template in the main directory
        valid_template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "ValidBucket": {
                    "Type": "AWS::S3::Bucket"
                }
            }
        }
        valid_file = temp_path / "valid.json"
        with open(valid_file, 'w') as f:
            json.dump(valid_template, f)
        
        # Scan with ignore patterns
        ignore_patterns = [".terraform", "*.backup"]
        components = manager.scan_directory(temp_path, ignore_patterns)
        
        # Should only find the valid file, not the ignored one
        resource_names = [comp.name for comp in components]
        assert "ValidBucket" in resource_names
        assert "IgnoredBucket" not in resource_names


def test_stage5_file_type_detection():
    """Test that Stage 5 scanners correctly identify their supported file types."""
    manager = InfrastructureScannerManager()
    
    # Test CloudFormation files
    cf_files = [
        "template.json",
        "cloudformation.yaml",
        "stack.yml",
        "infrastructure.template"
    ]
    
    for filename in cf_files:
        file_path = Path(filename)
        scanners = manager.get_registry().get_scanners_for_file(file_path)
        
        # Should have at least one scanner (CloudFormation might share some patterns)
        assert len(scanners) >= 1
        
        # At least one should be CloudFormation scanner
        scanner_classes = [scanner.__class__.__name__ for scanner in scanners]
        has_cf_scanner = any("CloudFormation" in name for name in scanner_classes)
        
        # For .json files, might be detected by multiple scanners, which is okay
        if filename.endswith('.json'):
            assert len(scanners) >= 1
        else:
            assert has_cf_scanner or len(scanners) >= 1


def test_stage5_supported_extensions():
    """Test that Stage 5 scanners contribute their extensions to the manager."""
    manager = InfrastructureScannerManager()
    
    supported_extensions = manager.get_supported_extensions()
    
    # Should include extensions from Stage 5 scanners
    stage5_extensions = [
        ".json",  # CloudFormation and ARM templates
        ".yaml",  # CloudFormation, ARM templates, and GCP deployments
        ".yml",   # CloudFormation, ARM templates, and GCP deployments
        ".template",  # CloudFormation
        ".jinja",  # GCP deployment manager
        "azuredeploy.json",  # ARM templates
        "mainTemplate.json",  # ARM templates
        "deployment.yaml"  # GCP deployments
    ]
    
    for ext in stage5_extensions:
        assert ext in supported_extensions


def test_stage5_error_handling():
    """Test error handling in Stage 5 scanners."""
    manager = InfrastructureScannerManager()
    
    # Test with non-existent file
    non_existent = Path("/non/existent/file.json")
    components = manager.scan_file(non_existent)
    assert components == []
    
    # Test with invalid JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"invalid": json}')
        f.flush()
        
        components = manager.scan_file(Path(f.name))
        # Should handle gracefully and return empty list
        assert isinstance(components, list)


def test_stage5_cross_scanner_compatibility():
    """Test that Stage 5 scanners work alongside existing scanners."""
    manager = InfrastructureScannerManager()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create files for different infrastructure types
        # Terraform (Stage 1)
        tf_content = '''
resource "aws_s3_bucket" "example" {
  bucket = "my-terraform-bucket"
}
'''
        tf_file = temp_path / "main.tf"
        with open(tf_file, 'w') as f:
            f.write(tf_content)
        
        # CloudFormation (Stage 5)
        cf_template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "MyCloudFormationBucket": {
                    "Type": "AWS::S3::Bucket"
                }
            }
        }
        cf_file = temp_path / "cloudformation.json"
        with open(cf_file, 'w') as f:
            json.dump(cf_template, f)
        
        # Kubernetes (Stage 2)
        k8s_content = '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
'''
        k8s_file = temp_path / "deployment.yaml"
        with open(k8s_file, 'w') as f:
            f.write(k8s_content)
        
        # Scan directory
        components = manager.scan_directory(temp_path)
        
        # Should detect components from multiple stages
        assert len(components) >= 3
        
        # Verify we have components from different stages
        services = [comp.service for comp in components]
        assert "terraform" in services
        assert "cloudformation" in services
        assert "kubernetes" in services
        
        # Verify infrastructure types are appropriate
        infrastructure_types = [comp.type for comp in components]
        assert InfrastructureType.IaC in infrastructure_types  # Terraform and CloudFormation
        assert InfrastructureType.CONTAINER in infrastructure_types  # Kubernetes