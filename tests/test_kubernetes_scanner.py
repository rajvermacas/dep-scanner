"""Test cases for Kubernetes scanner."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from dependency_scanner_tool.infrastructure_scanners.kubernetes import KubernetesScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType, InfrastructureComponent


class TestKubernetesScanner:
    """Test cases for KubernetesScanner."""
    
    def setup_method(self):
        """Set up test environment."""
        self.scanner = KubernetesScanner()
    
    def test_get_supported_file_patterns(self):
        """Test getting supported file patterns."""
        patterns = self.scanner.get_supported_file_patterns()
        expected_patterns = [
            "*.yaml",
            "*.yml",
            "kustomization.yaml",
            "kustomization.yml"
        ]
        assert patterns == expected_patterns
    
    def test_get_infrastructure_type(self):
        """Test getting infrastructure type."""
        assert self.scanner.get_infrastructure_type() == InfrastructureType.CONTAINER
    
    def test_can_handle_file_yaml(self):
        """Test file handling for YAML files."""
        yaml_file = Path("deployment.yaml")
        assert self.scanner.can_handle_file(yaml_file) is True
        
        yml_file = Path("service.yml")
        assert self.scanner.can_handle_file(yml_file) is True
        
        kustomization_file = Path("kustomization.yaml")
        assert self.scanner.can_handle_file(kustomization_file) is True
    
    def test_can_handle_file_non_yaml(self):
        """Test file handling for non-YAML files."""
        non_yaml_file = Path("Dockerfile")
        assert self.scanner.can_handle_file(non_yaml_file) is False
        
        txt_file = Path("readme.txt")
        assert self.scanner.can_handle_file(txt_file) is False
    
    def test_scan_deployment_yaml(self):
        """Test scanning Kubernetes deployment YAML."""
        deployment_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=deployment_yaml):
            
            file_path = Path("deployment.yaml")
            components = self.scanner.scan_file(file_path)
            
            assert len(components) == 1
            component = components[0]
            
            assert component.type == InfrastructureType.CONTAINER
            assert component.name == "nginx-deployment"
            assert component.service == "kubernetes"
            assert component.subtype == "Deployment"
            assert component.source_file == str(file_path)
            assert component.configuration["apiVersion"] == "apps/v1"
            assert component.configuration["spec"]["replicas"] == 3
    
    def test_scan_service_yaml(self):
        """Test scanning Kubernetes service YAML."""
        service_yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: LoadBalancer
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=service_yaml):
            
            file_path = Path("service.yaml")
            components = self.scanner.scan_file(file_path)
            
            assert len(components) == 1
            component = components[0]
            
            assert component.type == InfrastructureType.CONTAINER
            assert component.name == "nginx-service"
            assert component.service == "kubernetes"
            assert component.subtype == "Service"
            assert component.configuration["spec"]["type"] == "LoadBalancer"
    
    def test_scan_multiple_resources_yaml(self):
        """Test scanning YAML with multiple Kubernetes resources."""
        multi_resource_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    spec:
      containers:
      - name: web
        image: nginx:latest
---
apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  selector:
    app: web
  ports:
    - port: 80
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=multi_resource_yaml):
            
            file_path = Path("web-resources.yaml")
            components = self.scanner.scan_file(file_path)
            
            assert len(components) == 2
            
            deployment = components[0]
            assert deployment.name == "web-deployment"
            assert deployment.subtype == "Deployment"
            
            service = components[1]
            assert service.name == "web-service"
            assert service.subtype == "Service"
    
    def test_scan_configmap_yaml(self):
        """Test scanning Kubernetes ConfigMap YAML."""
        configmap_yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_url: "postgresql://localhost/myapp"
  debug: "true"
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=configmap_yaml):
            
            file_path = Path("configmap.yaml")
            components = self.scanner.scan_file(file_path)
            
            assert len(components) == 1
            component = components[0]
            
            assert component.name == "app-config"
            assert component.subtype == "ConfigMap"
            assert component.configuration["data"]["database_url"] == "postgresql://localhost/myapp"
    
    def test_scan_invalid_yaml(self):
        """Test scanning invalid YAML file."""
        invalid_yaml = """
apiVersion: v1
kind: Service
metadata:
  name: invalid-service
spec:
  - invalid: yaml: structure
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=invalid_yaml):
            
            file_path = Path("invalid.yaml")
            components = self.scanner.scan_file(file_path)
            
            # Should handle invalid YAML gracefully
            assert len(components) == 0
    
    def test_scan_non_kubernetes_yaml(self):
        """Test scanning YAML file that's not Kubernetes related."""
        non_k8s_yaml = """
version: '3.8'
services:
  web:
    image: nginx
    ports:
      - "80:80"
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=non_k8s_yaml):
            
            file_path = Path("docker-compose.yml")
            components = self.scanner.scan_file(file_path)
            
            # Should not detect non-Kubernetes YAML as Kubernetes resources
            assert len(components) == 0
    
    def test_scan_file_not_exists(self):
        """Test scanning file that doesn't exist."""
        file_path = Path("nonexistent.yaml")
        components = self.scanner.scan_file(file_path)
        
        assert len(components) == 0
    
    def test_scan_ingress_yaml(self):
        """Test scanning Kubernetes Ingress YAML."""
        ingress_yaml = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=ingress_yaml):
            
            file_path = Path("ingress.yaml")
            components = self.scanner.scan_file(file_path)
            
            assert len(components) == 1
            component = components[0]
            
            assert component.name == "example-ingress"
            assert component.subtype == "Ingress"
            assert component.configuration["spec"]["rules"][0]["host"] == "example.com"
    
    def test_scan_pvc_yaml(self):
        """Test scanning Kubernetes PersistentVolumeClaim YAML."""
        pvc_yaml = """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=pvc_yaml):
            
            file_path = Path("pvc.yaml")
            components = self.scanner.scan_file(file_path)
            
            assert len(components) == 1
            component = components[0]
            
            assert component.name == "data-pvc"
            assert component.subtype == "PersistentVolumeClaim"
            assert component.configuration["spec"]["resources"]["requests"]["storage"] == "10Gi"