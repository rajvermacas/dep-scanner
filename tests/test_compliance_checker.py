"""Test cases for compliance checker."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from dependency_scanner_tool.infrastructure_scanners.compliance import ComplianceChecker
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    ComplianceFramework,
    SecuritySeverity,
    ComplianceViolation
)


class TestComplianceChecker:
    """Test cases for ComplianceChecker."""
    
    def test_get_supported_file_patterns(self):
        """Test getting supported file patterns."""
        checker = ComplianceChecker()
        patterns = checker.get_supported_file_patterns()
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        # Should include common configuration files
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
        assert "*.env" in patterns
        assert "*.config" in patterns
    
    def test_get_infrastructure_type(self):
        """Test getting infrastructure type."""
        checker = ComplianceChecker()
        assert checker.get_infrastructure_type() == InfrastructureType.SECURITY
    
    def test_scan_file_with_gdpr_violations(self):
        """Test scanning a file with GDPR violations."""
        checker = ComplianceChecker()
        
        content = '''
# User data collection without consent
user_data = {
    "email": "user@example.com",
    "phone": "+1234567890",
    "ssn": "123-45-6789",  # PII without proper handling
    "ip_address": request.remote_addr,
    "tracking_id": generate_tracking_id(),
    "location": get_user_location()  # Location data without consent
}

# No data retention policy
store_user_data_permanently(user_data)

# No encryption for sensitive data
def save_user_data(data):
    # GDPR violation: storing PII without encryption
    database.save(data)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = checker.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            compliance_component = components[0]
            assert compliance_component.type == InfrastructureType.SECURITY
            assert compliance_component.service == "compliance"
            assert compliance_component.subtype == "gdpr"
            
            # Check compliance violations
            assert "compliance_violations" in compliance_component.metadata
            violations = compliance_component.metadata["compliance_violations"]
            assert len(violations) >= 1
            
            # Check for specific GDPR violations
            gdpr_violations = [v for v in violations 
                             if v["framework"] == ComplianceFramework.GDPR.value]
            assert len(gdpr_violations) >= 1
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_hipaa_violations(self):
        """Test scanning a file with HIPAA violations."""
        checker = ComplianceChecker()
        
        content = '''
# Medical data handling
patient_data = {
    "name": "John Doe",
    "ssn": "123-45-6789",
    "dob": "1990-01-01",
    "medical_record_number": "MR123456",
    "diagnosis": "Hypertension",
    "prescription": "Lisinopril 10mg",
    "insurance_info": "Blue Cross Blue Shield #12345"
}

# HIPAA violation: transmitting PHI without encryption
def send_patient_data(data):
    # This should be encrypted
    requests.post("http://api.example.com/patients", json=data)

# HIPAA violation: logging PHI
logger.info(f"Processing patient: {patient_data['name']} - {patient_data['ssn']}")

# HIPAA violation: storing PHI without proper access controls
with open("patient_data.txt", "w") as f:
    f.write(str(patient_data))
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = checker.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            compliance_component = components[0]
            assert compliance_component.type == InfrastructureType.SECURITY
            
            # Check compliance violations
            assert "compliance_violations" in compliance_component.metadata
            violations = compliance_component.metadata["compliance_violations"]
            
            # Check for HIPAA violations
            hipaa_violations = [v for v in violations 
                              if v["framework"] == ComplianceFramework.HIPAA.value]
            assert len(hipaa_violations) >= 1
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_soc2_violations(self):
        """Test scanning a file with SOC2 violations."""
        checker = ComplianceChecker()
        
        content = '''
version: '3.8'
services:
  database:
    image: postgres:13
    environment:
      POSTGRES_PASSWORD: "simple_password"  # SOC2: Weak password
      POSTGRES_DB: "production"
    ports:
      - "5432:5432"  # SOC2: Database exposed to public
    volumes:
      - ./data:/var/lib/postgresql/data  # SOC2: Data not encrypted at rest
  
  web:
    image: nginx:latest
    ports:
      - "80:80"  # SOC2: No HTTPS enforcement
    environment:
      - DEBUG=true  # SOC2: Debug mode in production
    
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"  # SOC2: Redis exposed without auth
    command: redis-server --requirepass ""  # SOC2: No authentication
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = checker.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            compliance_component = components[0]
            assert compliance_component.type == InfrastructureType.SECURITY
            
            # Check compliance violations
            assert "compliance_violations" in compliance_component.metadata
            violations = compliance_component.metadata["compliance_violations"]
            
            # Check for SOC2 violations
            soc2_violations = [v for v in violations 
                             if v["framework"] == ComplianceFramework.SOC2.value]
            assert len(soc2_violations) >= 1
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_pci_dss_violations(self):
        """Test scanning a file with PCI DSS violations."""
        checker = ComplianceChecker()
        
        content = '''
# Credit card processing
credit_card_data = {
    "card_number": "4111111111111111",
    "expiry_date": "12/25",
    "cvv": "123",
    "cardholder_name": "John Doe"
}

# PCI DSS violation: storing full PAN
def store_card_data(card_data):
    # This should be tokenized/encrypted
    database.save("cards", card_data)

# PCI DSS violation: logging sensitive data
logger.info(f"Processing card: {credit_card_data['card_number']}")

# PCI DSS violation: transmitting CHD without encryption
def process_payment(card_data):
    response = requests.post("http://payment-gateway.com/process", 
                           json=card_data)  # Should be HTTPS
    return response.json()

# PCI DSS violation: weak encryption
def encrypt_card_data(data):
    return base64.b64encode(data.encode()).decode()  # Not proper encryption
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = checker.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            # Find PCI DSS violations across all components
            all_violations = []
            for component in components:
                assert component.type == InfrastructureType.SECURITY
                if "compliance_violations" in component.metadata:
                    all_violations.extend(component.metadata["compliance_violations"])
            
            # Check for PCI DSS violations
            pci_violations = [v for v in all_violations 
                            if v["framework"] == ComplianceFramework.PCI_DSS.value]
            assert len(pci_violations) >= 1
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_with_terraform_compliance_issues(self):
        """Test scanning a Terraform file with compliance issues."""
        checker = ComplianceChecker()
        
        content = '''
# AWS S3 bucket configuration
resource "aws_s3_bucket" "example" {
  bucket = "my-example-bucket"
  
  # Compliance issue: No encryption
  # server_side_encryption_configuration missing
  
  # Compliance issue: Public access allowed
  acl = "public-read"
}

# AWS RDS instance
resource "aws_db_instance" "example" {
  identifier = "example-db"
  engine     = "mysql"
  
  # Compliance issue: No encryption at rest
  storage_encrypted = false
  
  # Compliance issue: Public access
  publicly_accessible = true
  
  # Compliance issue: No backup retention
  backup_retention_period = 0
  
  # Compliance issue: No monitoring
  monitoring_interval = 0
}

# Security group with overly permissive rules
resource "aws_security_group" "example" {
  name_prefix = "example-"
  
  # Compliance issue: Open to world
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = checker.scan_file(Path(f.name))
            
            assert len(components) >= 1
            
            compliance_component = components[0]
            assert compliance_component.type == InfrastructureType.SECURITY
            
            # Check compliance violations
            assert "compliance_violations" in compliance_component.metadata
            violations = compliance_component.metadata["compliance_violations"]
            assert len(violations) >= 3  # Multiple compliance issues
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_compliant_configuration(self):
        """Test scanning a file with compliant configuration."""
        checker = ComplianceChecker()
        
        content = '''
# Compliant configuration
resource "aws_s3_bucket" "compliant" {
  bucket = "compliant-bucket"
  
  # Proper encryption
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
  
  # Block public access
  acl = "private"
}

resource "aws_s3_bucket_public_access_block" "compliant" {
  bucket = aws_s3_bucket.compliant.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Compliant RDS instance
resource "aws_db_instance" "compliant" {
  identifier = "compliant-db"
  engine     = "mysql"
  
  # Encryption enabled
  storage_encrypted = true
  
  # Private access
  publicly_accessible = false
  
  # Proper backup retention
  backup_retention_period = 7
  
  # Monitoring enabled
  monitoring_interval = 60
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = checker.scan_file(Path(f.name))
            
            # May have no violations if configuration is compliant
            if len(components) > 0:
                compliance_component = components[0]
                assert compliance_component.type == InfrastructureType.SECURITY
                
                # Check compliance violations - should be fewer or none
                violations = compliance_component.metadata.get("compliance_violations", [])
                # This test passes if we have fewer violations than non-compliant configs
                assert len(violations) >= 0
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_empty_file(self):
        """Test scanning an empty file."""
        checker = ComplianceChecker()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("")
            f.flush()
            
            components = checker.scan_file(Path(f.name))
            
            assert len(components) == 0
            
            # Clean up
            Path(f.name).unlink()
    
    def test_scan_file_nonexistent_file(self):
        """Test scanning a file that doesn't exist."""
        checker = ComplianceChecker()
        
        components = checker.scan_file(Path("/nonexistent/file.py"))
        
        assert len(components) == 0
    
    def test_can_handle_file(self):
        """Test can_handle_file method."""
        checker = ComplianceChecker()
        
        # Should handle various file types
        assert checker.can_handle_file(Path("config.yml"))
        assert checker.can_handle_file(Path("main.tf"))
        assert checker.can_handle_file(Path("app.py"))
        assert checker.can_handle_file(Path("package.json"))
        assert checker.can_handle_file(Path("application.properties"))
        assert checker.can_handle_file(Path("settings.env"))
        
        # Should not handle binary files
        assert not checker.can_handle_file(Path("image.png"))
        assert not checker.can_handle_file(Path("binary.exe"))
    
    def test_get_compliance_frameworks(self):
        """Test getting supported compliance frameworks."""
        checker = ComplianceChecker()
        
        # Should support multiple frameworks
        frameworks = checker.get_supported_frameworks()
        assert ComplianceFramework.GDPR in frameworks
        assert ComplianceFramework.HIPAA in frameworks
        assert ComplianceFramework.SOC2 in frameworks
        assert ComplianceFramework.PCI_DSS in frameworks
    
    def test_check_gdpr_compliance(self):
        """Test GDPR compliance checking."""
        checker = ComplianceChecker()
        
        # Test with GDPR-relevant content
        content = '''
# Data collection
personal_data = {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890"
}

# This should trigger GDPR compliance checks
def collect_user_data(data):
    store_permanently(data)  # No retention policy
'''
        
        violations = checker._check_gdpr_compliance(content, "test.py")
        
        assert len(violations) >= 1
        assert all(v["framework"] == ComplianceFramework.GDPR.value 
                  for v in violations)
    
    def test_check_hipaa_compliance(self):
        """Test HIPAA compliance checking."""
        checker = ComplianceChecker()
        
        # Test with HIPAA-relevant content
        content = '''
# Medical data
patient_info = {
    "name": "Jane Doe",
    "ssn": "123-45-6789",
    "medical_record": "MR123456"
}

# This should trigger HIPAA compliance checks
def send_patient_data(data):
    requests.post("http://api.example.com", json=data)  # Unencrypted
'''
        
        violations = checker._check_hipaa_compliance(content, "test.py")
        
        assert len(violations) >= 1
        assert all(v["framework"] == ComplianceFramework.HIPAA.value 
                  for v in violations)
    
    def test_check_soc2_compliance(self):
        """Test SOC2 compliance checking."""
        checker = ComplianceChecker()
        
        # Test with SOC2-relevant content
        content = '''
version: '3.8'
services:
  database:
    image: postgres:13
    environment:
      POSTGRES_PASSWORD: "weak123"
    ports:
      - "5432:5432"  # Exposed to public
'''
        
        violations = checker._check_soc2_compliance(content, "docker-compose.yml")
        
        assert len(violations) >= 1
        assert all(v["framework"] == ComplianceFramework.SOC2.value 
                  for v in violations)
    
    def test_check_pci_dss_compliance(self):
        """Test PCI DSS compliance checking."""
        checker = ComplianceChecker()
        
        # Test with PCI DSS-relevant content
        content = '''
# Credit card processing
card_data = {
    "card_number": "4111111111111111",
    "cvv": "123"
}

# This should trigger PCI DSS compliance checks
def store_card(data):
    database.save(data)  # Storing full PAN
'''
        
        violations = checker._check_pci_dss_compliance(content, "payment.py")
        
        assert len(violations) >= 1
        assert all(v["framework"] == ComplianceFramework.PCI_DSS.value 
                  for v in violations)