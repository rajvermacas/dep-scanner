"""Integration tests for Stage 4 Database and Messaging Detection."""
import pytest
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.manager import InfrastructureScannerManager
from dependency_scanner_tool.models.infrastructure import InfrastructureType


class TestStage4Integration:
    """Integration tests for Stage 4 functionality."""
    
    def test_database_scanner_registration(self):
        """Test that database scanner is properly registered."""
        manager = InfrastructureScannerManager()
        registry = manager.get_registry()
        
        # Check that database scanner is registered
        scanner = registry.get("database")
        assert scanner is not None
        assert scanner.get_infrastructure_type() == InfrastructureType.DATABASE
    
    def test_messaging_scanner_registration(self):
        """Test that messaging scanner is properly registered."""
        manager = InfrastructureScannerManager()
        registry = manager.get_registry()
        
        # Check that messaging scanner is registered
        scanner = registry.get("messaging")
        assert scanner is not None
        assert scanner.get_infrastructure_type() == InfrastructureType.MESSAGING
    
    def test_multi_file_project_scanning(self, tmp_path):
        """Test scanning a project with multiple database and messaging files."""
        manager = InfrastructureScannerManager()
        
        # Create test project structure
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        
        # Database configuration file
        db_config = project_dir / "application.properties"
        db_config.write_text("""
spring.datasource.url=jdbc:postgresql://localhost:5432/myapp
spring.jpa.hibernate.ddl-auto=update
spring.kafka.bootstrap-servers=localhost:9092
""")
        
        # Python requirements with database and messaging
        requirements = project_dir / "requirements.txt"
        requirements.write_text("""
Django==4.2.0
psycopg2-binary==2.9.5
redis==4.5.4
celery==5.2.7
pika==1.3.1
""")
        
        # Docker compose with databases
        docker_compose = project_dir / "docker-compose.yml"
        docker_compose.write_text("""
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
      
  redis:
    image: redis:7
    ports:
      - "6379:6379"
      
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
""")
        
        # Scan all files
        all_components = []
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                components = manager.scan_file(file_path)
                all_components.extend(components)
        
        # Verify we detected both database and messaging components
        db_components = [c for c in all_components if c.type == InfrastructureType.DATABASE]
        messaging_components = [c for c in all_components if c.type == InfrastructureType.MESSAGING]
        
        assert len(db_components) > 0, "Should detect database components"
        assert len(messaging_components) > 0, "Should detect messaging components"
        
        # Check specific technologies were detected
        db_names = {c.name for c in db_components}
        messaging_names = {c.name for c in messaging_components}
        
        assert "postgresql" in db_names
        assert "redis" in db_names or "redis" in messaging_names
        
    def test_database_messaging_overlap_handling(self, tmp_path):
        """Test that Redis is properly handled as both database and messaging."""
        manager = InfrastructureScannerManager()
        
        # Create file with Redis configuration
        redis_config = tmp_path / "redis.yml"
        redis_config.write_text("""
redis:
  host: localhost
  port: 6379
  db: 0
  
cache:
  redis_url: redis://localhost:6379/1
  
messaging:
  redis_url: redis://localhost:6379/2
""")
        
        # Scan the file
        components = manager.scan_file(redis_config)
        
        # Should detect Redis as both database and messaging
        db_components = [c for c in components if c.type == InfrastructureType.DATABASE]
        messaging_components = [c for c in components if c.type == InfrastructureType.MESSAGING]
        
        # Redis can appear in both categories depending on usage
        redis_in_db = any(c.name == "redis" for c in db_components)
        redis_in_messaging = any(c.name == "redis" for c in messaging_components)
        
        assert redis_in_db or redis_in_messaging, "Should detect Redis in at least one category"
    
    def test_large_project_performance(self, tmp_path):
        """Test scanning performance with many files."""
        manager = InfrastructureScannerManager()
        
        # Create many configuration files
        project_dir = tmp_path / "large_project"
        project_dir.mkdir()
        
        for i in range(20):
            # Create multiple config files
            config_file = project_dir / f"config_{i}.properties"
            config_file.write_text(f"""
database.url=jdbc:postgresql://db{i}.example.com:5432/app{i}
redis.host=redis{i}.example.com
kafka.servers=kafka{i}.example.com:9092
""")
        
        # Measure scanning time
        import time
        start_time = time.time()
        
        all_components = []
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                components = manager.scan_file(file_path)
                all_components.extend(components)
        
        end_time = time.time()
        scan_time = end_time - start_time
        
        # Should complete within reasonable time (adjust as needed)
        assert scan_time < 10.0, f"Scanning took too long: {scan_time:.2f} seconds"
        
        # Should detect components from multiple files
        assert len(all_components) > 0, "Should detect components in large project"
    
    def test_invalid_file_handling(self, tmp_path):
        """Test that invalid files are handled gracefully."""
        manager = InfrastructureScannerManager()
        
        # Create invalid JSON file
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{invalid json content")
        
        # Create invalid YAML file
        invalid_yaml = tmp_path / "invalid.yml"
        invalid_yaml.write_text("""
invalid: yaml: content:
  - broken
    - structure
""")
        
        # Create invalid XML file
        invalid_xml = tmp_path / "pom.xml"
        invalid_xml.write_text("<xml><unclosed><tag></xml>")
        
        # Scanning should not raise exceptions
        components = []
        for file_path in [invalid_json, invalid_yaml, invalid_xml]:
            try:
                file_components = manager.scan_file(file_path)
                components.extend(file_components)
            except Exception as e:
                pytest.fail(f"Scanner should handle invalid files gracefully, but got: {e}")
        
        # Invalid files should return empty results, not errors
        assert isinstance(components, list), "Should return list even for invalid files"
    
    def test_cross_scanner_compatibility(self, tmp_path):
        """Test that Stage 4 scanners work alongside existing scanners."""
        manager = InfrastructureScannerManager()
        
        # Create multi-technology project
        project_dir = tmp_path / "multi_tech_project"
        project_dir.mkdir()
        
        # Terraform with database resources
        terraform_file = project_dir / "main.tf"
        terraform_file.write_text("""
resource "aws_db_instance" "main" {
  identifier = "myapp-db"
  engine     = "postgres"
  instance_class = "db.t3.micro"
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id = "myapp-redis"
  engine     = "redis"
}
""")
        
        # Docker with database services
        dockerfile = project_dir / "Dockerfile"
        dockerfile.write_text("""
FROM python:3.9
RUN pip install psycopg2-binary redis celery
COPY . /app
WORKDIR /app
""")
        
        # Application config
        app_config = project_dir / "config.yml"
        app_config.write_text("""
database:
  url: postgresql://localhost:5432/myapp
  
messaging:
  redis_url: redis://localhost:6379
  rabbitmq_url: amqp://localhost:5672
""")
        
        # Scan all files
        all_components = []
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                components = manager.scan_file(file_path)
                all_components.extend(components)
        
        # Should detect components from multiple scanner types
        component_types = {c.type for c in all_components}
        
        # Should have multiple infrastructure types
        assert len(component_types) > 1, "Should detect multiple infrastructure types"
        
        # Check for Stage 4 types
        assert InfrastructureType.DATABASE in component_types, "Should detect database components"
        assert InfrastructureType.MESSAGING in component_types, "Should detect messaging components"
        
        # Should also have existing types
        expected_existing_types = {InfrastructureType.IaC, InfrastructureType.CONTAINER}
        detected_existing = component_types.intersection(expected_existing_types)
        assert len(detected_existing) > 0, "Should also detect existing infrastructure types"