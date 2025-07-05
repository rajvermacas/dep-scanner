"""Integration tests for Stage 3 CI/CD Pipeline Detection."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List

from dependency_scanner_tool.infrastructure_scanners.manager import InfrastructureScannerManager
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType
from dependency_scanner_tool.scanner import DependencyType


class TestStage3Integration:
    """Integration tests for Stage 3 CI/CD scanners."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner_manager = InfrastructureScannerManager()
        self.temp_dir = None
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_temp_directory(self) -> Path:
        """Create a temporary directory for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        return self.temp_dir
    
    def test_jenkins_scanner_registration(self):
        """Test that Jenkins scanner is properly registered."""
        registry = self.scanner_manager.get_registry()
        jenkins_scanner = registry.get("jenkins")
        
        assert jenkins_scanner is not None
        assert jenkins_scanner.get_infrastructure_type() == InfrastructureType.CICD
        assert "Jenkinsfile" in jenkins_scanner.get_supported_file_patterns()
    
    def test_github_actions_scanner_registration(self):
        """Test that GitHub Actions scanner is properly registered."""
        registry = self.scanner_manager.get_registry()
        github_scanner = registry.get("github_actions")
        
        assert github_scanner is not None
        assert github_scanner.get_infrastructure_type() == InfrastructureType.CICD
        assert ".github/workflows/*.yml" in github_scanner.get_supported_file_patterns()
    
    def test_gitlab_ci_scanner_registration(self):
        """Test that GitLab CI scanner is properly registered."""
        registry = self.scanner_manager.get_registry()
        gitlab_scanner = registry.get("gitlab_ci")
        
        assert gitlab_scanner is not None
        assert gitlab_scanner.get_infrastructure_type() == InfrastructureType.CICD
        assert ".gitlab-ci.yml" in gitlab_scanner.get_supported_file_patterns()
    
    def test_comprehensive_cicd_project_scan(self):
        """Test scanning a project with multiple CI/CD configurations."""
        # Create temporary directory structure
        temp_dir = self._create_temp_directory()
        
        # Create Jenkins pipeline
        jenkinsfile_content = """
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'npm run build'
            }
        }
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
        stage('Deploy') {
            steps {
                sh 'npm run deploy'
            }
        }
    }
}
"""
        jenkinsfile_path = temp_dir / "Jenkinsfile"
        jenkinsfile_path.write_text(jenkinsfile_content)
        
        # Create GitHub Actions workflow
        github_workflow_dir = temp_dir / ".github" / "workflows"
        github_workflow_dir.mkdir(parents=True)
        
        github_workflow_content = """
name: CI/CD
on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Node
      uses: actions/setup-node@v3
      with:
        node-version: '16'
    - name: Install dependencies
      run: npm install
    - name: Build
      run: npm run build
"""
        github_workflow_path = github_workflow_dir / "ci.yml"
        github_workflow_path.write_text(github_workflow_content)
        
        # Create GitLab CI pipeline
        gitlab_ci_content = """
stages:
  - build
  - test
  - deploy

build_job:
  stage: build
  script:
    - npm install
    - npm run build

test_job:
  stage: test
  script:
    - npm test

deploy_job:
  stage: deploy
  script:
    - npm run deploy
  only:
    - main
"""
        gitlab_ci_path = temp_dir / ".gitlab-ci.yml"
        gitlab_ci_path.write_text(gitlab_ci_content)
        
        # Scan the directory
        components = self.scanner_manager.scan_directory(temp_dir)
        
        # Verify results
        cicd_components = [comp for comp in components if comp.type == InfrastructureType.CICD]
        assert len(cicd_components) == 3
        
        # Verify Jenkins component
        jenkins_components = [comp for comp in cicd_components if comp.service == "jenkins"]
        assert len(jenkins_components) == 1
        jenkins_comp = jenkins_components[0]
        assert jenkins_comp.name == "jenkins-pipeline"
        assert jenkins_comp.subtype == "declarative"
        assert len(jenkins_comp.configuration["stages"]) == 3
        
        # Verify GitHub Actions component
        github_components = [comp for comp in cicd_components if comp.service == "github-actions"]
        assert len(github_components) == 1
        github_comp = github_components[0]
        assert github_comp.name == "CI/CD"
        assert github_comp.subtype == "workflow"
        assert "build" in github_comp.configuration["jobs"]
        
        # Verify GitLab CI component
        gitlab_components = [comp for comp in cicd_components if comp.service == "gitlab-ci"]
        assert len(gitlab_components) == 1
        gitlab_comp = gitlab_components[0]
        assert gitlab_comp.name == "gitlab-ci-pipeline"
        assert gitlab_comp.subtype == "pipeline"
        assert gitlab_comp.configuration["stages"] == ["build", "test", "deploy"]
    
    def test_stage3_with_ignore_patterns(self):
        """Test that CI/CD scanners respect ignore patterns."""
        # Create temporary directory structure
        temp_dir = self._create_temp_directory()
        
        # Create CI/CD files in different locations
        jenkinsfile_path = temp_dir / "Jenkinsfile"
        jenkinsfile_path.write_text("pipeline { agent any }")
        
        # Create file in ignored directory
        ignored_dir = temp_dir / "node_modules"
        ignored_dir.mkdir()
        ignored_jenkinsfile = ignored_dir / "Jenkinsfile"
        ignored_jenkinsfile.write_text("pipeline { agent any }")
        
        # Scan with ignore patterns
        components = self.scanner_manager.scan_directory(temp_dir, ignore_patterns=["node_modules"])
        
        # Should only find the non-ignored file
        cicd_components = [comp for comp in components if comp.type == InfrastructureType.CICD]
        assert len(cicd_components) == 1
        assert "node_modules" not in cicd_components[0].source_file
    
    def test_mixed_infrastructure_and_cicd_scan(self):
        """Test scanning project with both infrastructure and CI/CD files."""
        # Create temporary directory structure
        temp_dir = self._create_temp_directory()
        
        # Create Terraform file (Stage 1)
        terraform_content = """
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = "t2.micro"
}
"""
        terraform_path = temp_dir / "main.tf"
        terraform_path.write_text(terraform_content)
        
        # Create Docker file (Stage 1)
        dockerfile_content = """
FROM node:16
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
"""
        dockerfile_path = temp_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        
        # Create Kubernetes file (Stage 2)
        k8s_content = """
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
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: myapp:latest
        ports:
        - containerPort: 3000
"""
        k8s_path = temp_dir / "deployment.yaml"
        k8s_path.write_text(k8s_content)
        
        # Create Jenkins file (Stage 3)
        jenkinsfile_content = """
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'docker build -t myapp .'
            }
        }
        stage('Deploy') {
            steps {
                sh 'kubectl apply -f deployment.yaml'
            }
        }
    }
}
"""
        jenkinsfile_path = temp_dir / "Jenkinsfile"
        jenkinsfile_path.write_text(jenkinsfile_content)
        
        # Scan the directory
        components = self.scanner_manager.scan_directory(temp_dir)
        
        # Verify we have components from all stages
        iac_components = [comp for comp in components if comp.type == InfrastructureType.IaC]
        container_components = [comp for comp in components if comp.type == InfrastructureType.CONTAINER]
        cicd_components = [comp for comp in components if comp.type == InfrastructureType.CICD]
        
        # Should have at least one component from each category
        assert len(iac_components) >= 1  # Terraform
        assert len(container_components) >= 2  # Docker + Kubernetes
        assert len(cicd_components) >= 1  # Jenkins
        
        # Verify specific components exist
        terraform_comps = [comp for comp in iac_components if comp.service == "terraform"]
        docker_comps = [comp for comp in container_components if comp.service == "docker"]
        k8s_comps = [comp for comp in container_components if comp.service == "kubernetes"]
        jenkins_comps = [comp for comp in cicd_components if comp.service == "jenkins"]
        
        assert len(terraform_comps) >= 1
        assert len(docker_comps) >= 1
        assert len(k8s_comps) >= 1
        assert len(jenkins_comps) >= 1
    
    def test_stage3_performance_large_project(self):
        """Test performance with a larger project structure."""
        # Create temporary directory structure
        temp_dir = self._create_temp_directory()
        
        # Create multiple CI/CD files across different directories
        for i in range(5):
            # Create subdirectory
            subdir = temp_dir / f"service-{i}"
            subdir.mkdir()
            
            # Create Jenkins pipeline
            jenkinsfile = subdir / "Jenkinsfile"
            jenkinsfile.write_text(f"""
pipeline {{
    agent any
    stages {{
        stage('Build Service {i}') {{
            steps {{
                sh 'make build-service-{i}'
            }}
        }}
    }}
}}
""")
            
            # Create GitHub Actions workflow
            github_dir = subdir / ".github" / "workflows"
            github_dir.mkdir(parents=True)
            github_workflow = github_dir / f"service-{i}.yml"
            github_workflow.write_text(f"""
name: Service {i} CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build Service {i}
      run: make build-service-{i}
""")
        
        # Scan the directory
        import time
        start_time = time.time()
        components = self.scanner_manager.scan_directory(temp_dir)
        end_time = time.time()
        
        # Verify performance (should complete within reasonable time)
        scan_duration = end_time - start_time
        assert scan_duration < 10.0  # Should complete within 10 seconds
        
        # Verify all components were found
        cicd_components = [comp for comp in components if comp.type == InfrastructureType.CICD]
        assert len(cicd_components) == 10  # 5 Jenkins + 5 GitHub Actions