"""Test cases for infrastructure scanner manager."""
import pytest
import tempfile
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.manager import InfrastructureScannerManager
from dependency_scanner_tool.models.infrastructure import InfrastructureType


def test_infrastructure_manager_initialization():
    """Test InfrastructureScannerManager initialization."""
    manager = InfrastructureScannerManager()
    
    # Should have registered scanners
    registry = manager.get_registry()
    scanners = registry.get_all()
    
    assert "terraform" in scanners
    assert "docker" in scanners


def test_infrastructure_manager_scan_directory():
    """Test scanning a directory with infrastructure files."""
    manager = InfrastructureScannerManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create test files
        terraform_file = tmpdir_path / "main.tf"
        terraform_file.write_text('''
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
}
''')
        
        dockerfile = tmpdir_path / "Dockerfile"
        dockerfile.write_text('''
FROM nginx:latest
EXPOSE 80
''')
        
        compose_file = tmpdir_path / "docker-compose.yml"
        compose_file.write_text('''
version: '3.8'
services:
  app:
    image: myapp:latest
    ports:
      - "3000:3000"
''')
        
        # Scan directory
        components = manager.scan_directory(tmpdir_path)
        
        # Should find components from all scanners
        assert len(components) >= 3  # Terraform resource, Dockerfile, docker-compose + service
        
        # Check we have different types
        terraform_components = [c for c in components if c.service == "terraform"]
        docker_components = [c for c in components if c.service == "docker"]
        
        assert len(terraform_components) >= 1
        assert len(docker_components) >= 2


def test_infrastructure_manager_scan_single_file():
    """Test scanning a single infrastructure file."""
    manager = InfrastructureScannerManager()
    
    terraform_content = '''
resource "aws_s3_bucket" "example" {
  bucket = "my-example-bucket"
}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tf', delete=False) as f:
        f.write(terraform_content)
        f.flush()
        
        components = manager.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.service == "terraform"
        assert component.subtype == "aws_s3_bucket"
        assert component.name == "example"
        
        # Clean up
        Path(f.name).unlink()


def test_infrastructure_manager_scan_unsupported_file():
    """Test scanning a file that no scanner supports."""
    manager = InfrastructureScannerManager()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is just a text file")
        f.flush()
        
        components = manager.scan_file(Path(f.name))
        
        assert len(components) == 0
        
        # Clean up
        Path(f.name).unlink()


def test_infrastructure_manager_scan_directory_with_ignore():
    """Test scanning directory with ignore patterns."""
    manager = InfrastructureScannerManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create test files
        terraform_file = tmpdir_path / "main.tf"
        terraform_file.write_text('''
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
}
''')
        
        # Create ignored file
        ignored_dir = tmpdir_path / ".terraform"
        ignored_dir.mkdir()
        ignored_terraform = ignored_dir / "terraform.tf"
        ignored_terraform.write_text('''
resource "aws_instance" "ignored" {
  ami           = "ami-ignore"
  instance_type = "t2.nano"
}
''')
        
        # Scan with ignore patterns
        components = manager.scan_directory(tmpdir_path, ignore_patterns=[".terraform"])
        
        # Should find main.tf but not the ignored file
        assert len(components) == 1
        component = components[0]
        assert component.name == "web"  # Not "ignored"


def test_infrastructure_manager_get_supported_extensions():
    """Test getting supported file extensions."""
    manager = InfrastructureScannerManager()
    
    extensions = manager.get_supported_extensions()
    
    assert ".tf" in extensions
    assert ".tfvars" in extensions
    assert "Dockerfile" in extensions or any("Dockerfile" in ext for ext in extensions)


def test_infrastructure_manager_scan_nonexistent_file():
    """Test scanning a file that doesn't exist."""
    manager = InfrastructureScannerManager()
    
    components = manager.scan_file(Path("/nonexistent/file.tf"))
    
    assert len(components) == 0


def test_infrastructure_manager_scan_empty_directory():
    """Test scanning an empty directory."""
    manager = InfrastructureScannerManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        components = manager.scan_directory(Path(tmpdir))
        
        assert len(components) == 0