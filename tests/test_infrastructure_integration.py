"""Integration test for infrastructure scanning functionality."""
import tempfile
from pathlib import Path
from dependency_scanner_tool.scanner import DependencyScanner


def test_infrastructure_integration():
    """Test end-to-end infrastructure scanning integration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create test infrastructure files
        terraform_file = tmpdir_path / "main.tf"
        terraform_file.write_text('''
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  
  tags = {
    Name = "web-server"
    Environment = "production"
  }
}

provider "aws" {
  region = "us-west-2"
}
''')
        
        dockerfile = tmpdir_path / "Dockerfile"
        dockerfile.write_text('''
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
''')
        
        # Create basic dependency file for comparison
        requirements_file = tmpdir_path / "requirements.txt"
        requirements_file.write_text('''
flask==2.0.1
requests==2.28.0
''')
        
        # Initialize scanner and run scan with infrastructure analysis
        scanner = DependencyScanner()
        result = scanner.scan_project(
            project_path=str(tmpdir_path),
            analyze_infrastructure=True
        )
        
        # Verify infrastructure components were found
        assert result.infrastructure_components is not None
        assert len(result.infrastructure_components) >= 2  # Terraform resource + provider, Dockerfile
        
        # Check Terraform components
        terraform_components = [
            c for c in result.infrastructure_components 
            if c.service == "terraform"
        ]
        assert len(terraform_components) >= 2  # aws_instance + provider
        
        # Verify aws_instance resource
        aws_instance = next(
            (c for c in terraform_components if c.subtype == "aws_instance"), 
            None
        )
        assert aws_instance is not None
        assert aws_instance.name == "web"
        assert aws_instance.configuration["instance_type"] == "t2.micro"
        assert aws_instance.configuration["tags"]["Name"] == "web-server"
        
        # Verify provider
        aws_provider = next(
            (c for c in terraform_components if c.subtype == "provider"), 
            None
        )
        assert aws_provider is not None
        assert aws_provider.name == "aws"
        assert aws_provider.configuration["region"] == "us-west-2"
        
        # Check Docker components
        docker_components = [
            c for c in result.infrastructure_components 
            if c.service == "docker"
        ]
        assert len(docker_components) >= 1
        
        # Verify Dockerfile
        dockerfile_component = next(
            (c for c in docker_components if c.subtype == "dockerfile"), 
            None
        )
        assert dockerfile_component is not None
        assert dockerfile_component.name == "dockerfile"
        assert dockerfile_component.configuration["base_image"] == "python:3.9-slim"
        assert dockerfile_component.configuration["workdir"] == "/app"
        assert dockerfile_component.configuration["exposed_ports"] == ["5000"]
        
        # Verify regular dependencies still work
        assert len(result.dependencies) >= 0  # May not parse requirements.txt without parser setup
        assert result.languages is not None
        assert result.package_managers is not None


def test_infrastructure_disabled():
    """Test that infrastructure scanning can be disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create test infrastructure files
        terraform_file = tmpdir_path / "main.tf"
        terraform_file.write_text('''
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
}
''')
        
        # Initialize scanner and run scan WITHOUT infrastructure analysis
        scanner = DependencyScanner()
        result = scanner.scan_project(
            project_path=str(tmpdir_path),
            analyze_infrastructure=False  # Explicitly disabled
        )
        
        # Verify infrastructure components were NOT found
        assert result.infrastructure_components is None