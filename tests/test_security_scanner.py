"""Test cases for security scanner."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from dependency_scanner_tool.infrastructure_scanners.security import SecurityScanner
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    SecurityFindingType,
    SecuritySeverity,
    SecurityFinding
)


class TestSecurityScanner:
    """Test cases for SecurityScanner."""
    
    def test_get_supported_file_patterns(self):
        """Test getting supported file patterns."""
        scanner = SecurityScanner()
        patterns = scanner.get_supported_file_patterns()
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        # Should include common files where secrets might be found
        assert "*.env" in patterns
        assert "*.config" in patterns
        assert "*.yml" in patterns
        assert "*.yaml" in patterns
        assert "*.json" in patterns
        assert "*.tf" in patterns
        assert "*.py" in patterns
        assert "*.js" in patterns
        assert "*.ts" in patterns
        assert "*.java" in patterns
        assert "*.xml" in patterns
        assert "*.properties" in patterns
    
    def test_get_infrastructure_type(self):
        """Test getting infrastructure type."""
        scanner = SecurityScanner()
        assert scanner.get_infrastructure_type() == InfrastructureType.SECURITY
    
    def test_scan_file_with_hardcoded_password(self):
        """Test scanning a file with hardcoded password."""
        scanner = SecurityScanner()
        
        content = '''
# Configuration file
DATABASE_URL = "postgresql://user:password123@localhost:5432/db"
API_KEY = "sk-1234567890abcdef"
SECRET_KEY = "super-secret-key-123"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = scanner.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            # Check that we found security findings
            security_component = components[0]
            assert security_component.type == InfrastructureType.SECURITY
            assert security_component.service == "security"
            assert security_component.subtype == "secrets"
            
            # Check security findings in metadata
            assert "security_findings" in security_component.metadata
            findings = security_component.metadata["security_findings"]
            assert len(findings) >= 2  # Should find API_KEY and SECRET_KEY
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_api_keys(self):
        """Test scanning a file with API keys."""
        scanner = SecurityScanner()
        
        content = '''
{
    "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "github_token": "ghp_1234567890abcdef1234567890abcdef12345678"
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = scanner.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            security_component = components[0]
            assert security_component.type == InfrastructureType.SECURITY
            
            # Check security findings
            assert "security_findings" in security_component.metadata
            findings = security_component.metadata["security_findings"]
            assert len(findings) >= 2  # Should find AWS keys and GitHub token
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_private_keys(self):
        """Test scanning a file with private keys."""
        scanner = SecurityScanner()
        
        content = '''
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7VJTUt9Us8cKB
wjXVKWuuXiD4cSIzCQoHiJFUdAQAG
-----END PRIVATE KEY-----

-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btNiS
M5KPpQ2vFjDkKZSvLGr0nGNhXo5/FGlNWq4QMqLNZ4BjVAz5VScuJP6M+gkWmvGE
-----END RSA PRIVATE KEY-----
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = scanner.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            security_component = components[0]
            assert security_component.type == InfrastructureType.SECURITY
            
            # Check security findings
            assert "security_findings" in security_component.metadata
            findings = security_component.metadata["security_findings"]
            assert len(findings) >= 2  # Should find both private keys
            
            # Check severity
            for finding in findings:
                assert finding["severity"] == SecuritySeverity.HIGH.value
                assert finding["finding_type"] == SecurityFindingType.PRIVATE_KEY.value
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_certificates(self):
        """Test scanning a file with certificates."""
        scanner = SecurityScanner()
        
        content = '''
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAJC1HiIAZAiIMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMTYwODMwMDUzNDI3WhcNMjYwODI4MDUzNDI3WjBF
-----END CERTIFICATE-----
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = scanner.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            security_component = components[0]
            assert security_component.type == InfrastructureType.SECURITY
            
            # Check security findings
            assert "security_findings" in security_component.metadata
            findings = security_component.metadata["security_findings"]
            assert len(findings) >= 1  # Should find certificate
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_security_tools_config(self):
        """Test scanning a file with security tools configuration."""
        scanner = SecurityScanner()
        
        content = '''
version: '3.8'
services:
  vault:
    image: vault:latest
    ports:
      - "8200:8200"
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: myroot
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
  
  consul:
    image: consul:latest
    ports:
      - "8500:8500"
  
  security-scanner:
    image: aquasec/trivy:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = scanner.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            security_component = components[0]
            assert security_component.type == InfrastructureType.SECURITY
            
            # Check detected security tools
            assert "security_tools" in security_component.metadata
            tools = security_component.metadata["security_tools"]
            assert "vault" in tools
            assert "consul" in tools
            assert "trivy" in tools
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_empty_file(self):
        """Test scanning an empty file."""
        scanner = SecurityScanner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("")
            f.flush()
            
            components = scanner.scan_file(Path(f.name))
            
            assert len(components) == 0
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_nonexistent_file(self):
        """Test scanning a file that doesn't exist."""
        scanner = SecurityScanner()
        
        components = scanner.scan_file(Path("/nonexistent/file.env"))
        
        assert len(components) == 0
    
    def test_scan_file_with_terraform_secrets(self):
        """Test scanning a Terraform file with potential secrets."""
        scanner = SecurityScanner()
        
        content = '''
resource "aws_instance" "example" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  
  tags = {
    Name = "example-instance"
    Environment = "production"
  }
}

# BAD: Hardcoded credentials
resource "aws_db_instance" "example" {
  identifier = "example-db"
  engine     = "mysql"
  username   = "admin"
  password   = "super-secret-password"  # This should be detected
  
  db_name  = "example"
  allocated_storage = 20
  storage_type = "gp2"
  
  tags = {
    Name = "example-db"
  }
}

variable "api_key" {
  description = "API key for third-party service"
  type        = string
  default     = "sk-1234567890abcdef"  # This should be detected
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = scanner.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            security_component = components[0]
            assert security_component.type == InfrastructureType.SECURITY
            
            # Check security findings
            assert "security_findings" in security_component.metadata
            findings = security_component.metadata["security_findings"]
            assert len(findings) >= 2  # Should find hardcoded password and API key
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_insecure_urls(self):
        """Test scanning a file with insecure URLs."""
        scanner = SecurityScanner()
        
        content = '''
# Application configuration
API_ENDPOINT = "http://api.example.com"  # Should be HTTPS
DATABASE_URL = "postgres://user:pass@db.example.com:5432/db"  # No SSL
WEBHOOK_URL = "http://webhook.example.com/callback"  # Should be HTTPS
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = scanner.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            security_component = components[0]
            assert security_component.type == InfrastructureType.SECURITY
            
            # Check security findings
            assert "security_findings" in security_component.metadata
            findings = security_component.metadata["security_findings"]
            
            # Should find insecure URLs
            insecure_findings = [f for f in findings 
                               if f["finding_type"] == SecurityFindingType.INSECURE_CONFIG.value]
            assert len(insecure_findings) >= 1
            
            # Clean up
            Path(f.name).unlink()
    
    def test_can_handle_file(self):
        """Test can_handle_file method."""
        scanner = SecurityScanner()
        
        # Should handle various file types
        assert scanner.can_handle_file(Path("config.env"))
        assert scanner.can_handle_file(Path("docker-compose.yml"))
        assert scanner.can_handle_file(Path("main.tf"))
        assert scanner.can_handle_file(Path("app.py"))
        assert scanner.can_handle_file(Path("package.json"))
        assert scanner.can_handle_file(Path("application.properties"))
        
        # Should not handle binary files
        assert not scanner.can_handle_file(Path("image.png"))
        assert not scanner.can_handle_file(Path("binary.exe"))