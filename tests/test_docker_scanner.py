"""Test cases for Docker scanner."""
import pytest
import tempfile
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.docker import DockerScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType


def test_docker_scanner_initialization():
    """Test DockerScanner initialization."""
    scanner = DockerScanner()
    
    assert scanner.get_infrastructure_type() == InfrastructureType.CONTAINER
    assert "Dockerfile" in scanner.get_supported_file_patterns()
    assert "docker-compose.yml" in scanner.get_supported_file_patterns()
    assert "docker-compose.yaml" in scanner.get_supported_file_patterns()


def test_docker_scanner_can_handle_file():
    """Test DockerScanner file handling."""
    scanner = DockerScanner()
    
    assert scanner.can_handle_file(Path("Dockerfile")) is True
    assert scanner.can_handle_file(Path("docker-compose.yml")) is True
    assert scanner.can_handle_file(Path("docker-compose.yaml")) is True
    assert scanner.can_handle_file(Path("test.txt")) is False
    assert scanner.can_handle_file(Path("main.tf")) is False


def test_docker_scanner_basic_dockerfile():
    """Test scanning basic Dockerfile."""
    scanner = DockerScanner()
    
    dockerfile_content = '''
FROM nginx:latest
WORKDIR /app
COPY . /app
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as f:
        # Create file with specific name
        dockerfile_path = Path(f.name).parent / "Dockerfile"
        with open(dockerfile_path, 'w') as df:
            df.write(dockerfile_content)
        
        components = scanner.scan_file(dockerfile_path)
        
        assert len(components) == 1
        component = components[0]
        
        assert component.type == InfrastructureType.CONTAINER
        assert component.name == "dockerfile"
        assert component.service == "docker"
        assert component.subtype == "dockerfile"
        assert component.source_file == str(dockerfile_path)
        assert component.configuration["base_image"] == "nginx:latest"
        assert component.configuration["workdir"] == "/app"
        assert component.configuration["exposed_ports"] == ["80"]
        assert "nginx" in component.configuration["cmd"]
        
        # Clean up
        dockerfile_path.unlink()


def test_docker_scanner_dockerfile_multi_stage():
    """Test scanning multi-stage Dockerfile."""
    scanner = DockerScanner()
    
    dockerfile_content = '''
# Build stage
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install

# Production stage
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80 443
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as f:
        # Create file with specific name
        dockerfile_path = Path(f.name).parent / "Dockerfile"
        with open(dockerfile_path, 'w') as df:
            df.write(dockerfile_content)
        
        components = scanner.scan_file(dockerfile_path)
        
        assert len(components) == 1
        component = components[0]
        
        assert component.configuration["base_images"] == ["node:16", "nginx:alpine"]
        assert component.configuration["exposed_ports"] == ["80", "443"]
        assert "builder" in component.configuration["stages"]
        assert "production" in component.configuration["stages"]
        
        # Clean up
        dockerfile_path.unlink()


def test_docker_scanner_docker_compose():
    """Test scanning docker-compose.yml file."""
    scanner = DockerScanner()
    
    compose_content = '''
version: '3.8'

services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./html:/usr/share/nginx/html
    environment:
      - NODE_ENV=production
    
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        compose_path = Path(f.name).parent / "docker-compose.yml"
        with open(compose_path, 'w') as cf:
            cf.write(compose_content)
        
        components = scanner.scan_file(compose_path)
        
        assert len(components) == 3  # 2 services + 1 compose file
        
        # Find compose component
        compose_component = next(c for c in components if c.subtype == "docker-compose")
        assert compose_component.name == "docker-compose"
        assert compose_component.configuration["version"] == "3.8"
        
        # Find web service
        web_component = next(c for c in components if c.name == "web")
        assert web_component.subtype == "service"
        assert web_component.configuration["image"] == "nginx:latest"
        assert "80:80" in web_component.configuration["ports"]
        
        # Find db service
        db_component = next(c for c in components if c.name == "db")
        assert db_component.subtype == "service"
        assert db_component.configuration["image"] == "postgres:13"
        assert db_component.configuration["environment"]["POSTGRES_DB"] == "myapp"
        
        # Clean up
        compose_path.unlink()


def test_docker_scanner_empty_dockerfile():
    """Test scanning empty Dockerfile."""
    scanner = DockerScanner()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as f:
        dockerfile_path = Path(f.name).parent / "Dockerfile"
        with open(dockerfile_path, 'w') as df:
            df.write("")
        
        components = scanner.scan_file(dockerfile_path)
        
        assert len(components) == 0
        
        # Clean up
        dockerfile_path.unlink()


def test_docker_scanner_invalid_compose():
    """Test scanning invalid docker-compose file."""
    scanner = DockerScanner()
    
    compose_content = '''
version: '3.8'
services:
  web:
    image: nginx
    # Invalid YAML - missing closing bracket
    ports:
      - "80:80
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        compose_path = Path(f.name).parent / "docker-compose.yml"
        with open(compose_path, 'w') as cf:
            cf.write(compose_content)
        
        components = scanner.scan_file(compose_path)
        
        # Should return empty list for invalid YAML
        assert len(components) == 0
        
        # Clean up
        compose_path.unlink()


def test_docker_scanner_dockerfile_with_args():
    """Test scanning Dockerfile with build arguments."""
    scanner = DockerScanner()
    
    dockerfile_content = '''
ARG NODE_VERSION=16
FROM node:${NODE_VERSION}
ARG BUILD_ENV=production
ENV NODE_ENV=${BUILD_ENV}
WORKDIR /app
COPY package*.json ./
RUN npm install --only=production
COPY . .
EXPOSE 3000
USER node
CMD ["npm", "start"]
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as f:
        dockerfile_path = Path(f.name).parent / "Dockerfile"
        with open(dockerfile_path, 'w') as df:
            df.write(dockerfile_content)
        
        components = scanner.scan_file(dockerfile_path)
        
        assert len(components) == 1
        component = components[0]
        
        assert "NODE_VERSION" in component.configuration["args"]
        assert component.configuration["args"]["NODE_VERSION"] == "16"
        assert component.configuration["args"]["BUILD_ENV"] == "production"
        assert component.configuration["exposed_ports"] == ["3000"]
        assert component.configuration["user"] == "node"
        assert component.configuration["env"]["NODE_ENV"] == "${BUILD_ENV}"
        
        # Clean up
        dockerfile_path.unlink()