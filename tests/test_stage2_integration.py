"""Integration tests for Stage 2 features (Kubernetes and Cloud SDK Detection)."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from dependency_scanner_tool.infrastructure_scanners.manager import InfrastructureScannerManager
from dependency_scanner_tool.models.infrastructure import InfrastructureType


class TestStage2Integration:
    """Integration tests for Stage 2 features."""
    
    def setup_method(self):
        """Set up test environment."""
        self.manager = InfrastructureScannerManager()
    
    def test_kubernetes_scanner_registered(self):
        """Test that Kubernetes scanner is registered."""
        registry = self.manager.get_registry()
        scanners = registry.get_all()
        
        assert "kubernetes" in scanners
        kubernetes_scanner = scanners["kubernetes"]
        assert kubernetes_scanner.get_infrastructure_type() == InfrastructureType.CONTAINER
    
    def test_cloud_sdk_detector_registered(self):
        """Test that Cloud SDK detector is registered."""
        registry = self.manager.get_registry()
        scanners = registry.get_all()
        
        assert "cloud_sdk" in scanners
        cloud_sdk_detector = scanners["cloud_sdk"]
        assert cloud_sdk_detector.get_infrastructure_type() == InfrastructureType.CLOUD
    
    def test_scan_kubernetes_yaml_file(self):
        """Test scanning a Kubernetes YAML file through the manager."""
        k8s_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    spec:
      containers:
      - name: web
        image: nginx:latest
        ports:
        - containerPort: 80
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=k8s_yaml):
            
            file_path = Path("deployment.yaml")
            components = self.manager.scan_file(file_path)
            
            assert len(components) == 1
            component = components[0]
            
            assert component.type == InfrastructureType.CONTAINER
            assert component.service == "kubernetes"
            assert component.subtype == "Deployment"
            assert component.name == "web-app"
    
    def test_scan_python_with_cloud_sdk(self):
        """Test scanning a Python file with cloud SDK imports through the manager."""
        python_code = """
import boto3
from azure.storage.blob import BlobServiceClient
from google.cloud import storage

def setup_cloud_clients():
    # AWS
    s3_client = boto3.client('s3')
    
    # Azure
    blob_client = BlobServiceClient(account_url="https://myaccount.blob.core.windows.net")
    
    # GCP
    storage_client = storage.Client()
    
    return s3_client, blob_client, storage_client
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=python_code):
            
            file_path = Path("cloud_clients.py")
            components = self.manager.scan_file(file_path)
            
            assert len(components) >= 3  # Should detect AWS, Azure, and GCP
            
            # Check for each cloud provider
            providers = {c.service for c in components}
            assert "aws" in providers
            assert "azure" in providers
            assert "gcp" in providers
            
            # All should be cloud infrastructure components
            for component in components:
                assert component.type == InfrastructureType.CLOUD
                assert component.subtype == "sdk"
    
    def test_scan_multiple_file_types_individually_disabled(self):
        """Test scanning different infrastructure file types individually."""
        # Test each scanner can handle its file type
        test_cases = [
            {
                "file": Path("k8s/deployment.yaml"),
                "content": """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
""",
                "expected_service": "kubernetes",
                "expected_type": InfrastructureType.CONTAINER
            },
            {
                "file": Path("terraform/main.tf"),
                "content": """
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
}
""",
                "expected_service": "terraform",
                "expected_type": InfrastructureType.IaC
            },
            {
                "file": Path("src/aws_client.py"),
                "content": """
import boto3
s3 = boto3.client('s3')
""",
                "expected_service": "aws",
                "expected_type": InfrastructureType.CLOUD
            },
            {
                "file": Path("docker-compose.yml"),
                "content": """
version: '3.8'
services:
  web:
    image: nginx:latest
""",
                "expected_service": "docker",
                "expected_type": InfrastructureType.CONTAINER
            }
        ]
        
        for test_case in test_cases:
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('pathlib.Path.read_text', return_value=test_case["content"]):
                
                components = self.manager.scan_file(test_case["file"])
                
                assert len(components) >= 1, f"No components found for {test_case['file']}"
                
                # Check that we found the expected service
                services = {c.service for c in components}
                assert test_case["expected_service"] in services, \
                    f"Expected service {test_case['expected_service']} not found in {services}"
                
                # Check that we found the expected type
                types = {c.type for c in components}
                assert test_case["expected_type"] in types, \
                    f"Expected type {test_case['expected_type']} not found in {types}"
    
    def test_get_supported_extensions_includes_stage2(self):
        """Test that supported extensions include Stage 2 scanner patterns."""
        extensions = self.manager.get_supported_extensions()
        
        # Should include Kubernetes patterns
        assert ".yaml" in extensions
        assert ".yml" in extensions
        
        # Should include Cloud SDK patterns
        assert ".py" in extensions
        assert ".java" in extensions
        assert ".js" in extensions
        assert "requirements.txt" in extensions
        assert "package.json" in extensions
        assert "pom.xml" in extensions
    
    def test_stage2_scanners_handle_their_files(self):
        """Test that Stage 2 scanners correctly identify files they can handle."""
        registry = self.manager.get_registry()
        
        # Test Kubernetes scanner
        k8s_scanner = registry.get("kubernetes")
        assert k8s_scanner.can_handle_file(Path("deployment.yaml"))
        assert k8s_scanner.can_handle_file(Path("service.yml"))
        assert not k8s_scanner.can_handle_file(Path("main.tf"))
        
        # Test Cloud SDK detector
        cloud_scanner = registry.get("cloud_sdk")
        assert cloud_scanner.can_handle_file(Path("client.py"))
        assert cloud_scanner.can_handle_file(Path("Service.java"))
        assert cloud_scanner.can_handle_file(Path("requirements.txt"))
        assert not cloud_scanner.can_handle_file(Path("README.md"))
    
    def test_stage2_components_have_correct_metadata(self):
        """Test that Stage 2 components have correct metadata structure."""
        k8s_yaml = """
apiVersion: v1
kind: Service
metadata:
  name: web-service
  namespace: production
  labels:
    app: web
    tier: frontend
spec:
  selector:
    app: web
  ports:
    - port: 80
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=k8s_yaml):
            
            file_path = Path("service.yaml")
            components = self.manager.scan_file(file_path)
            
            assert len(components) == 1
            component = components[0]
            
            # Check metadata structure
            assert "api_version" in component.metadata
            assert "namespace" in component.metadata
            assert "labels" in component.metadata
            assert component.metadata["api_version"] == "v1"
            assert component.metadata["namespace"] == "production"
            assert component.metadata["labels"]["app"] == "web"