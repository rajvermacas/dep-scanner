"""Test cases for Terraform scanner."""
import pytest
import tempfile
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.terraform import TerraformScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType


def test_terraform_scanner_initialization():
    """Test TerraformScanner initialization."""
    scanner = TerraformScanner()
    
    assert scanner.get_infrastructure_type() == InfrastructureType.IaC
    assert "*.tf" in scanner.get_supported_file_patterns()
    assert "*.tfvars" in scanner.get_supported_file_patterns()


def test_terraform_scanner_can_handle_file():
    """Test TerraformScanner file handling."""
    scanner = TerraformScanner()
    
    assert scanner.can_handle_file(Path("main.tf")) is True
    assert scanner.can_handle_file(Path("variables.tfvars")) is True
    assert scanner.can_handle_file(Path("terraform.tfvars")) is True
    assert scanner.can_handle_file(Path("test.txt")) is False
    assert scanner.can_handle_file(Path("docker-compose.yml")) is False


def test_terraform_scanner_basic_aws_resource():
    """Test scanning basic AWS Terraform resource."""
    scanner = TerraformScanner()
    
    terraform_content = '''
resource "aws_instance" "example" {
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = "t2.micro"
  
  tags = {
    Name = "example-instance"
  }
}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
        f.write(terraform_content)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.type == InfrastructureType.IaC
        assert component.name == "example"
        assert component.service == "terraform"
        assert component.subtype == "aws_instance"
        assert component.source_file == f.name
        assert component.configuration["ami"] == "ami-0c55b159cbfafe1d0"
        assert component.configuration["instance_type"] == "t2.micro"
        assert component.configuration["tags"]["Name"] == "example-instance"
        
        # Clean up
        Path(f.name).unlink()


def test_terraform_scanner_multiple_resources():
    """Test scanning multiple Terraform resources."""
    scanner = TerraformScanner()
    
    terraform_content = '''
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = "t2.micro"
}

resource "aws_s3_bucket" "backup" {
  bucket = "my-backup-bucket"
}

resource "azurerm_resource_group" "main" {
  name     = "my-rg"
  location = "West US"
}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
        f.write(terraform_content)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 3
        
        # Check AWS instance
        aws_instance = next(c for c in components if c.subtype == "aws_instance")
        assert aws_instance.name == "web"
        assert aws_instance.configuration["instance_type"] == "t2.micro"
        
        # Check S3 bucket
        s3_bucket = next(c for c in components if c.subtype == "aws_s3_bucket")
        assert s3_bucket.name == "backup"
        assert s3_bucket.configuration["bucket"] == "my-backup-bucket"
        
        # Check Azure resource group
        azure_rg = next(c for c in components if c.subtype == "azurerm_resource_group")
        assert azure_rg.name == "main"
        assert azure_rg.configuration["location"] == "West US"
        
        # Clean up
        Path(f.name).unlink()


def test_terraform_scanner_provider_detection():
    """Test scanning Terraform provider configurations."""
    scanner = TerraformScanner()
    
    terraform_content = '''
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-west-2"
}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
        f.write(terraform_content)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.type == InfrastructureType.IaC
        assert component.name == "aws"
        assert component.service == "terraform"
        assert component.subtype == "provider"
        assert component.configuration["region"] == "us-west-2"
        
        # Clean up
        Path(f.name).unlink()


def test_terraform_scanner_invalid_syntax():
    """Test scanning Terraform file with invalid syntax."""
    scanner = TerraformScanner()
    
    terraform_content = '''
resource "aws_instance" "example" {
  ami = "ami-123"
  # Missing closing brace
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
        f.write(terraform_content)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for invalid syntax
        assert len(components) == 0
        
        # Clean up
        Path(f.name).unlink()


def test_terraform_scanner_empty_file():
    """Test scanning empty Terraform file."""
    scanner = TerraformScanner()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
        f.write("")
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 0
        
        # Clean up
        Path(f.name).unlink()


def test_terraform_scanner_tfvars_file():
    """Test scanning Terraform variables file."""
    scanner = TerraformScanner()
    
    tfvars_content = '''
instance_type = "t2.micro"
region        = "us-west-2"
environment   = "production"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tfvars', delete=False) as f:
        f.write(tfvars_content)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        
        assert component.type == InfrastructureType.IaC
        assert component.name == "variables"
        assert component.service == "terraform"
        assert component.subtype == "tfvars"
        assert component.configuration["instance_type"] == "t2.micro"
        assert component.configuration["region"] == "us-west-2"
        assert component.configuration["environment"] == "production"
        
        # Clean up
        Path(f.name).unlink()