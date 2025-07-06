"""Integration tests for Stage 6: Security and Compliance Framework."""

import pytest
import tempfile
from pathlib import Path

from dependency_scanner_tool.infrastructure_scanners.manager import InfrastructureScannerManager
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    SecurityFindingType,
    SecuritySeverity,
    ComplianceFramework
)


class TestStage6Integration:
    """Integration tests for Stage 6 security and compliance features."""
    
    def test_security_scanner_integration(self):
        """Test SecurityScanner integration with InfrastructureScannerManager."""
        manager = InfrastructureScannerManager()
        
        # Verify security scanner is registered
        registry = manager.get_registry()
        scanners = registry.get_all()
        assert "security" in scanners
        
        # Test scanning a file with secrets
        content = '''
# Configuration file
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgresql://user:password123@localhost:5432/db"
SECRET_TOKEN = "ghp_1234567890abcdef1234567890abcdef12345678"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = manager.scan_file(Path(f.name))
            
            # Should find security components
            security_components = [c for c in components if c.service == "security"]
            assert len(security_components) >= 1
            
            security_component = security_components[0]
            assert security_component.type == InfrastructureType.SECURITY
            assert security_component.subtype == "secrets"
            
            # Should have security findings
            assert "security_findings" in security_component.metadata
            findings = security_component.metadata["security_findings"]
            assert len(findings) >= 2
            
            # Clean up
            Path(f.name).unlink()
    
    def test_compliance_checker_integration(self):
        """Test ComplianceChecker integration with InfrastructureScannerManager."""
        manager = InfrastructureScannerManager()
        
        # Verify compliance checker is registered
        registry = manager.get_registry()
        scanners = registry.get_all()
        assert "compliance" in scanners
        
        # Test scanning a file with compliance violations
        content = '''
# GDPR violation: storing personal data without consent
user_data = {
    "email": "user@example.com",
    "phone": "+1234567890",
    "ssn": "123-45-6789"
}

# Store data permanently without retention policy
store_user_data_permanently(user_data)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = manager.scan_file(Path(f.name))
            
            # Should find compliance components
            compliance_components = [c for c in components if c.service == "compliance"]
            assert len(compliance_components) >= 1
            
            compliance_component = compliance_components[0]
            assert compliance_component.type == InfrastructureType.SECURITY
            assert compliance_component.subtype == ComplianceFramework.GDPR.value
            
            # Should have compliance violations
            assert "compliance_violations" in compliance_component.metadata
            violations = compliance_component.metadata["compliance_violations"]
            assert len(violations) >= 1
            
            # Clean up
            Path(f.name).unlink()
    
    def test_security_tools_detection(self):
        """Test security tools detection in Docker Compose files."""
        manager = InfrastructureScannerManager()
        
        content = '''
version: '3.8'
services:
  vault:
    image: hashicorp/vault:latest
    ports:
      - "8200:8200"
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: myroot
  
  trivy:
    image: aquasec/trivy:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
  
  app:
    image: myapp:latest
    ports:
      - "3000:3000"
'''
        
        # Create a proper docker-compose.yml file
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_file = Path(tmpdir) / "docker-compose.yml"
            compose_file.write_text(content)
            
            components = manager.scan_file(compose_file)
            
            # Should find both Docker and security components
            docker_components = [c for c in components if c.service == "docker"]
            security_components = [c for c in components if c.service == "security"]
            
            assert len(docker_components) >= 1  # Docker compose + services
            assert len(security_components) >= 1  # Security tools detected
            
            # Check security tools detection
            security_component = security_components[0]
            assert "security_tools" in security_component.metadata
            tools = security_component.metadata["security_tools"]
            assert "vault" in tools
            assert "trivy" in tools
    
    def test_terraform_security_compliance_scan(self):
        """Test scanning Terraform files for both security and compliance issues."""
        manager = InfrastructureScannerManager()
        
        content = '''
# Terraform configuration with security and compliance issues
resource "aws_s3_bucket" "example" {
  bucket = "my-example-bucket"
  acl    = "public-read"  # Compliance issue
}

resource "aws_db_instance" "example" {
  identifier     = "example-db"
  engine         = "mysql"
  username       = "admin"
  password       = "hardcoded-password"  # Security issue
  storage_encrypted = false  # Compliance issue
  publicly_accessible = true  # Compliance issue
}

variable "api_key" {
  description = "API key"
  type        = string
  default     = "sk-1234567890abcdef"  # Security issue
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = manager.scan_file(Path(f.name))
            
            # Should find Terraform, security, and compliance components
            terraform_components = [c for c in components if c.service == "terraform"]
            security_components = [c for c in components if c.service == "security"]
            compliance_components = [c for c in components if c.service == "compliance"]
            
            assert len(terraform_components) >= 1
            assert len(security_components) >= 1
            assert len(compliance_components) >= 1
            
            # Check security findings
            security_component = security_components[0]
            assert "security_findings" in security_component.metadata
            findings = security_component.metadata["security_findings"]
            assert len(findings) >= 2  # Password and API key
            
            # Check compliance violations
            compliance_component = compliance_components[0]
            assert "compliance_violations" in compliance_component.metadata
            violations = compliance_component.metadata["compliance_violations"]
            assert len(violations) >= 1
            
            # Clean up
            Path(f.name).unlink()
    
    def test_directory_scan_with_security_compliance(self):
        """Test directory scanning with security and compliance checks."""
        manager = InfrastructureScannerManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create multiple files with different issues
            env_file = tmpdir_path / ".env"
            env_file.write_text('''
DATABASE_URL=postgresql://user:password123@localhost:5432/db
API_KEY=sk-1234567890abcdef
SECRET_TOKEN=ghp_1234567890abcdef1234567890abcdef12345678
''')
            
            python_file = tmpdir_path / "app.py"
            python_file.write_text('''
# HIPAA violation example
patient_data = {
    "name": "John Doe",
    "ssn": "123-45-6789",
    "medical_record": "MR123456"
}

# Transmit without encryption
requests.post("http://api.example.com/patients", json=patient_data)
''')
            
            terraform_file = tmpdir_path / "main.tf"
            terraform_file.write_text('''
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
}

resource "aws_security_group" "allow_all" {
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
''')
            
            # Scan the directory
            components = manager.scan_directory(tmpdir_path)
            
            # Should find components from all scanners
            terraform_components = [c for c in components if c.service == "terraform"]
            security_components = [c for c in components if c.service == "security"]
            compliance_components = [c for c in components if c.service == "compliance"]
            
            assert len(terraform_components) >= 2  # Instance and security group
            assert len(security_components) >= 2   # From .env and possibly others
            assert len(compliance_components) >= 1  # HIPAA violations
            
            # Verify we found security findings
            total_findings = 0
            for component in security_components:
                if "security_findings" in component.metadata:
                    total_findings += len(component.metadata["security_findings"])
            assert total_findings >= 3  # Multiple secrets found
            
            # Verify we found compliance violations
            total_violations = 0
            for component in compliance_components:
                if "compliance_violations" in component.metadata:
                    total_violations += len(component.metadata["compliance_violations"])
            assert total_violations >= 1  # HIPAA violations
    
    def test_mixed_file_types_scanning(self):
        """Test scanning various file types for security and compliance."""
        manager = InfrastructureScannerManager()
        
        test_cases = [
            ('.env', 'API_KEY=sk-1234567890abcdef'),
            ('.json', '{"aws_access_key_id": "AKIAIOSFODNN7EXAMPLE"}'),
            ('.yaml', 'password: "hardcoded-password"'),
            ('.tf', 'password = "terraform-secret"'),
            ('.py', 'SECRET = "python-secret-key"'),
            ('.js', 'const token = "js-secret-token";'),
            ('.java', 'String apiKey = "java-api-key";'),
            ('.xml', '<password>xml-password</password>')
        ]
        
        for suffix, content in test_cases:
            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
                f.write(content)
                f.flush()
                
                components = manager.scan_file(Path(f.name))
                
                # Each file should be scanned by security scanner
                security_components = [c for c in components if c.service == "security"]
                if security_components:  # Some files might not trigger findings
                    security_component = security_components[0]
                    assert security_component.type == InfrastructureType.SECURITY
                
                # Clean up
                Path(f.name).unlink()
    
    def test_stage6_comprehensive_scan(self):
        """Test comprehensive Stage 6 functionality with realistic project structure."""
        manager = InfrastructureScannerManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create a realistic project structure
            (tmpdir_path / "src").mkdir()
            (tmpdir_path / "config").mkdir()
            (tmpdir_path / "terraform").mkdir()
            
            # Application config with secrets
            config_file = tmpdir_path / "config" / "application.yml"
            config_file.write_text('''
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/mydb
    username: admin
    password: hardcoded-password
  
security:
  oauth2:
    client-id: myapp
    client-secret: sk-1234567890abcdef
''')
            
            # Terraform with compliance issues
            tf_file = tmpdir_path / "terraform" / "main.tf"
            tf_file.write_text('''
resource "aws_s3_bucket" "data" {
  bucket = "sensitive-data-bucket"
  acl    = "public-read"
}

resource "aws_db_instance" "main" {
  identifier = "main-db"
  engine     = "postgres"
  password   = "db-secret-password"
  storage_encrypted = false
  publicly_accessible = true
}
''')
            
            # Docker Compose with security tools
            docker_file = tmpdir_path / "docker-compose.yml"
            docker_file.write_text('''
version: '3.8'
services:
  vault:
    image: hashicorp/vault:latest
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: secret
  
  app:
    image: myapp:latest
    environment:
      - API_KEY=sk-1234567890abcdef
      - DEBUG=true
''')
            
            # Python app with HIPAA data
            python_file = tmpdir_path / "src" / "patient_service.py"
            python_file.write_text('''
import requests

def process_patient(patient_data):
    # HIPAA violation: logging PHI
    logger.info(f"Processing patient: {patient_data['ssn']}")
    
    # HIPAA violation: transmitting without encryption
    response = requests.post("http://api.hospital.com/patients", 
                           json=patient_data)
    return response
''')
            
            # Scan the entire directory
            components = manager.scan_directory(tmpdir_path)
            
            # Organize components by service
            components_by_service = {}
            for component in components:
                service = component.service
                if service not in components_by_service:
                    components_by_service[service] = []
                components_by_service[service].append(component)
            
            # Verify we found components from all relevant scanners
            assert "terraform" in components_by_service
            assert "docker" in components_by_service
            assert "security" in components_by_service
            assert "compliance" in components_by_service
            
            # Count total findings
            total_security_findings = 0
            total_compliance_violations = 0
            security_tools_found = set()
            
            for component in components:
                if component.metadata:
                    if "security_findings" in component.metadata:
                        total_security_findings += len(component.metadata["security_findings"])
                    if "compliance_violations" in component.metadata:
                        total_compliance_violations += len(component.metadata["compliance_violations"])
                    if "security_tools" in component.metadata:
                        security_tools_found.update(component.metadata["security_tools"])
            
            # Verify significant findings
            assert total_security_findings >= 4  # Multiple secrets across files
            assert total_compliance_violations >= 2  # SOC2 and HIPAA violations
            assert len(security_tools_found) >= 1  # Vault detected
            assert "vault" in security_tools_found
            
            print(f"Stage 6 Integration Test Results:")
            print(f"  Security findings: {total_security_findings}")
            print(f"  Compliance violations: {total_compliance_violations}")
            print(f"  Security tools detected: {security_tools_found}")
            print(f"  Components by service: {list(components_by_service.keys())}")