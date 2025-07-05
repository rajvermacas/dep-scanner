"""Test cases for database infrastructure scanner."""
import pytest
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.database import DatabaseScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType, InfrastructureComponent


class TestDatabaseScanner:
    """Test cases for DatabaseScanner."""
    
    def test_supported_file_patterns(self):
        """Test that DatabaseScanner returns correct file patterns."""
        scanner = DatabaseScanner()
        patterns = scanner.get_supported_file_patterns()
        
        expected_patterns = [
            "*.properties",
            "*.yaml",
            "*.yml",
            "*.json",
            "*.env",
            "*.conf",
            "*.ini",
            "requirements.txt",
            "pom.xml",
            "build.gradle",
            "package.json",
            "go.mod",
            "Gemfile",
            "composer.json"
        ]
        
        assert all(pattern in patterns for pattern in expected_patterns)
    
    def test_infrastructure_type(self):
        """Test that DatabaseScanner returns correct infrastructure type."""
        scanner = DatabaseScanner()
        assert scanner.get_infrastructure_type() == InfrastructureType.DATABASE
    
    def test_scan_properties_file_with_database_config(self, tmp_path):
        """Test scanning properties file with database configuration."""
        scanner = DatabaseScanner()
        
        # Create test properties file
        properties_content = """
# Database configuration
spring.datasource.url=jdbc:postgresql://localhost:5432/mydb
spring.datasource.username=user
spring.datasource.password=password
spring.datasource.driver-class-name=org.postgresql.Driver
spring.jpa.hibernate.ddl-auto=update
"""
        
        properties_file = tmp_path / "application.properties"
        properties_file.write_text(properties_content)
        
        # Scan the file
        components = scanner.scan_file(properties_file)
        
        # Should detect PostgreSQL database
        assert len(components) == 1
        
        component = components[0]
        assert component.type == InfrastructureType.DATABASE
        assert component.name == "postgresql"
        assert component.service == "postgresql"
        assert component.subtype == "relational_database"
        assert component.source_file == str(properties_file)
        assert "connection_url" in component.configuration
        assert "localhost:5432" in component.configuration["connection_url"]
        assert "mydb" in component.configuration["database_name"]
    
    def test_scan_yaml_file_with_database_config(self, tmp_path):
        """Test scanning YAML file with database configuration."""
        scanner = DatabaseScanner()
        
        # Create test YAML file
        yaml_content = """
database:
  host: localhost
  port: 3306
  name: myapp
  user: admin
  adapter: mysql2
  
redis:
  host: redis.example.com
  port: 6379
  db: 0
"""
        
        yaml_file = tmp_path / "database.yml"
        yaml_file.write_text(yaml_content)
        
        # Scan the file
        components = scanner.scan_file(yaml_file)
        
        # Should detect MySQL and Redis
        assert len(components) == 2
        
        # Check MySQL component
        mysql_component = next((c for c in components if c.name == "mysql"), None)
        assert mysql_component is not None
        assert mysql_component.type == InfrastructureType.DATABASE
        assert mysql_component.service == "mysql"
        assert mysql_component.subtype == "relational_database"
        assert "localhost:3306" in mysql_component.configuration["connection_url"]
        
        # Check Redis component
        redis_component = next((c for c in components if c.name == "redis"), None)
        assert redis_component is not None
        assert redis_component.type == InfrastructureType.DATABASE
        assert redis_component.service == "redis"
        assert redis_component.subtype == "cache_database"
        assert "redis.example.com:6379" in redis_component.configuration["connection_url"]
    
    def test_scan_package_json_with_database_dependencies(self, tmp_path):
        """Test scanning package.json for database dependencies."""
        scanner = DatabaseScanner()
        
        # Create test package.json
        package_content = """{
  "name": "my-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0",
    "mysql2": "^3.2.0",
    "redis": "^4.0.0",
    "mongoose": "^7.0.0",
    "pg": "^8.7.0"
  }
}"""
        
        package_file = tmp_path / "package.json"
        package_file.write_text(package_content)
        
        # Scan the file
        components = scanner.scan_file(package_file)
        
        # Should detect multiple database drivers
        assert len(components) >= 3
        
        db_names = [c.name for c in components]
        assert "mysql" in db_names
        assert "redis" in db_names
        assert "mongodb" in db_names
        assert "postgresql" in db_names
    
    def test_scan_requirements_txt_with_database_dependencies(self, tmp_path):
        """Test scanning requirements.txt for database dependencies."""
        scanner = DatabaseScanner()
        
        # Create test requirements.txt
        requirements_content = """
Django==4.2.0
psycopg2-binary==2.9.5
redis==4.5.4
pymongo==4.3.3
SQLAlchemy==2.0.10
mysql-connector-python==8.0.33
"""
        
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(requirements_content)
        
        # Scan the file
        components = scanner.scan_file(requirements_file)
        
        # Should detect multiple database drivers
        assert len(components) >= 4
        
        db_names = [c.name for c in components]
        assert "postgresql" in db_names
        assert "redis" in db_names
        assert "mongodb" in db_names
        assert "mysql" in db_names
    
    def test_scan_pom_xml_with_database_dependencies(self, tmp_path):
        """Test scanning pom.xml for database dependencies."""
        scanner = DatabaseScanner()
        
        # Create test pom.xml
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-app</artifactId>
    <version>1.0.0</version>
    
    <dependencies>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <version>42.5.4</version>
        </dependency>
        <dependency>
            <groupId>redis.clients</groupId>
            <artifactId>jedis</artifactId>
            <version>4.3.1</version>
        </dependency>
        <dependency>
            <groupId>org.mongodb</groupId>
            <artifactId>mongodb-driver-sync</artifactId>
            <version>4.9.1</version>
        </dependency>
        <dependency>
            <groupId>mysql</groupId>
            <artifactId>mysql-connector-java</artifactId>
            <version>8.0.33</version>
        </dependency>
    </dependencies>
</project>"""
        
        pom_file = tmp_path / "pom.xml"
        pom_file.write_text(pom_content)
        
        # Scan the file
        components = scanner.scan_file(pom_file)
        
        # Should detect multiple database drivers
        assert len(components) >= 4
        
        db_names = [c.name for c in components]
        assert "postgresql" in db_names
        assert "redis" in db_names
        assert "mongodb" in db_names
        assert "mysql" in db_names
    
    def test_scan_env_file_with_database_urls(self, tmp_path):
        """Test scanning .env file with database URLs."""
        scanner = DatabaseScanner()
        
        # Create test .env file
        env_content = """
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
REDIS_URL=redis://localhost:6379/0
MONGODB_URI=mongodb://localhost:27017/myapp
MYSQL_DATABASE_URL=mysql://user:pass@localhost:3306/mydb
"""
        
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        
        # Scan the file
        components = scanner.scan_file(env_file)
        
        # Should detect all database URLs
        assert len(components) == 4
        
        db_names = [c.name for c in components]
        assert "postgresql" in db_names
        assert "redis" in db_names
        assert "mongodb" in db_names
        assert "mysql" in db_names
    
    def test_scan_file_with_no_database_config(self, tmp_path):
        """Test scanning file with no database configuration."""
        scanner = DatabaseScanner()
        
        # Create test file without database config
        test_content = """
# Some random configuration
app.name=MyApp
app.version=1.0.0
logging.level=INFO
"""
        
        test_file = tmp_path / "application.properties"
        test_file.write_text(test_content)
        
        # Scan the file
        components = scanner.scan_file(test_file)
        
        # Should detect no database components
        assert len(components) == 0
    
    def test_scan_invalid_file(self, tmp_path):
        """Test scanning invalid or malformed file."""
        scanner = DatabaseScanner()
        
        # Create invalid JSON file
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{invalid json content")
        
        # Scan the file - should not raise exception
        components = scanner.scan_file(invalid_file)
        
        # Should return empty list for invalid files
        assert len(components) == 0
    
    def test_can_handle_file(self, tmp_path):
        """Test file handling capability."""
        scanner = DatabaseScanner()
        
        # Test supported files
        properties_file = tmp_path / "application.properties"
        yaml_file = tmp_path / "database.yml"
        json_file = tmp_path / "package.json"
        env_file = tmp_path / ".env"
        
        properties_file.touch()
        yaml_file.touch()
        json_file.touch()
        env_file.touch()
        
        assert scanner.can_handle_file(properties_file)
        assert scanner.can_handle_file(yaml_file)
        assert scanner.can_handle_file(json_file)
        assert scanner.can_handle_file(env_file)
        
        # Test unsupported file
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.touch()
        
        assert not scanner.can_handle_file(unsupported_file)