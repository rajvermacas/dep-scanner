"""Test cases for messaging infrastructure scanner."""
import pytest
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.messaging import MessagingScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType, InfrastructureComponent


class TestMessagingScanner:
    """Test cases for MessagingScanner."""
    
    def test_supported_file_patterns(self):
        """Test that MessagingScanner returns correct file patterns."""
        scanner = MessagingScanner()
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
        """Test that MessagingScanner returns correct infrastructure type."""
        scanner = MessagingScanner()
        assert scanner.get_infrastructure_type() == InfrastructureType.MESSAGING
    
    def test_scan_properties_file_with_kafka_config(self, tmp_path):
        """Test scanning properties file with Kafka configuration."""
        scanner = MessagingScanner()
        
        # Create test properties file
        properties_content = """
# Kafka configuration
spring.kafka.bootstrap-servers=localhost:9092
spring.kafka.consumer.group-id=my-group
spring.kafka.consumer.auto-offset-reset=earliest
spring.kafka.producer.key-serializer=org.apache.kafka.common.serialization.StringSerializer
spring.kafka.producer.value-serializer=org.apache.kafka.common.serialization.StringSerializer
"""
        
        properties_file = tmp_path / "application.properties"
        properties_file.write_text(properties_content)
        
        # Scan the file
        components = scanner.scan_file(properties_file)
        
        # Should detect Kafka
        assert len(components) == 1
        
        component = components[0]
        assert component.type == InfrastructureType.MESSAGING
        assert component.name == "kafka"
        assert component.service == "kafka"
        assert component.subtype == "streaming_platform"
        assert component.source_file == str(properties_file)
        assert "bootstrap_servers" in component.configuration
        assert "localhost:9092" in component.configuration["bootstrap_servers"]
    
    def test_scan_yaml_file_with_messaging_config(self, tmp_path):
        """Test scanning YAML file with messaging configuration."""
        scanner = MessagingScanner()
        
        # Create test YAML file
        yaml_content = """
messaging:
  rabbitmq:
    host: rabbitmq.example.com
    port: 5672
    username: admin
    password: password
    vhost: /
  
  kafka:
    bootstrap_servers: kafka1.example.com:9092,kafka2.example.com:9092
    
  activemq:
    broker_url: tcp://activemq.example.com:61616
"""
        
        yaml_file = tmp_path / "messaging.yml"
        yaml_file.write_text(yaml_content)
        
        # Scan the file
        components = scanner.scan_file(yaml_file)
        
        # Should detect RabbitMQ, Kafka, and ActiveMQ
        assert len(components) == 3
        
        # Check RabbitMQ component
        rabbitmq_component = next((c for c in components if c.name == "rabbitmq"), None)
        assert rabbitmq_component is not None
        assert rabbitmq_component.type == InfrastructureType.MESSAGING
        assert rabbitmq_component.service == "rabbitmq"
        assert rabbitmq_component.subtype == "message_queue"
        assert "rabbitmq.example.com:5672" in rabbitmq_component.configuration["connection_url"]
        
        # Check Kafka component
        kafka_component = next((c for c in components if c.name == "kafka"), None)
        assert kafka_component is not None
        assert kafka_component.type == InfrastructureType.MESSAGING
        assert kafka_component.service == "kafka"
        assert kafka_component.subtype == "streaming_platform"
        
        # Check ActiveMQ component
        activemq_component = next((c for c in components if c.name == "activemq"), None)
        assert activemq_component is not None
        assert activemq_component.type == InfrastructureType.MESSAGING
        assert activemq_component.service == "activemq"
        assert activemq_component.subtype == "message_queue"
    
    def test_scan_package_json_with_messaging_dependencies(self, tmp_path):
        """Test scanning package.json for messaging dependencies."""
        scanner = MessagingScanner()
        
        # Create test package.json
        package_content = """{
  "name": "my-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0",
    "amqplib": "^0.10.3",
    "kafkajs": "^2.2.4",
    "redis": "^4.0.0",
    "bull": "^4.10.4",
    "stompit": "^1.0.0"
  }
}"""
        
        package_file = tmp_path / "package.json"
        package_file.write_text(package_content)
        
        # Scan the file
        components = scanner.scan_file(package_file)
        
        # Should detect multiple messaging systems
        assert len(components) >= 3
        
        messaging_names = [c.name for c in components]
        assert "rabbitmq" in messaging_names  # from amqplib
        assert "kafka" in messaging_names  # from kafkajs
        assert "redis" in messaging_names  # from redis (can be used for messaging)
    
    def test_scan_requirements_txt_with_messaging_dependencies(self, tmp_path):
        """Test scanning requirements.txt for messaging dependencies."""
        scanner = MessagingScanner()
        
        # Create test requirements.txt
        requirements_content = """
Django==4.2.0
celery==5.2.7
redis==4.5.4
pika==1.3.1
kafka-python==2.0.2
kombu==5.2.4
"""
        
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(requirements_content)
        
        # Scan the file
        components = scanner.scan_file(requirements_file)
        
        # Should detect multiple messaging systems
        assert len(components) >= 3
        
        messaging_names = [c.name for c in components]
        assert "rabbitmq" in messaging_names  # from pika
        assert "kafka" in messaging_names  # from kafka-python
        assert "redis" in messaging_names  # from redis
    
    def test_scan_pom_xml_with_messaging_dependencies(self, tmp_path):
        """Test scanning pom.xml for messaging dependencies."""
        scanner = MessagingScanner()
        
        # Create test pom.xml
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-app</artifactId>
    <version>1.0.0</version>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.kafka</groupId>
            <artifactId>spring-kafka</artifactId>
            <version>2.9.7</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.amqp</groupId>
            <artifactId>spring-rabbit</artifactId>
            <version>2.4.10</version>
        </dependency>
        <dependency>
            <groupId>redis.clients</groupId>
            <artifactId>jedis</artifactId>
            <version>4.3.1</version>
        </dependency>
        <dependency>
            <groupId>org.apache.activemq</groupId>
            <artifactId>activemq-client</artifactId>
            <version>5.17.4</version>
        </dependency>
    </dependencies>
</project>"""
        
        pom_file = tmp_path / "pom.xml"
        pom_file.write_text(pom_content)
        
        # Scan the file
        components = scanner.scan_file(pom_file)
        
        # Should detect multiple messaging systems
        assert len(components) >= 4
        
        messaging_names = [c.name for c in components]
        assert "kafka" in messaging_names
        assert "rabbitmq" in messaging_names
        assert "redis" in messaging_names
        assert "activemq" in messaging_names
    
    def test_scan_env_file_with_messaging_urls(self, tmp_path):
        """Test scanning .env file with messaging URLs."""
        scanner = MessagingScanner()
        
        # Create test .env file
        env_content = """
RABBITMQ_URL=amqp://user:pass@localhost:5672/
KAFKA_BOOTSTRAP_SERVERS=kafka1.example.com:9092,kafka2.example.com:9092
REDIS_URL=redis://localhost:6379/0
ACTIVEMQ_URL=tcp://activemq.example.com:61616
"""
        
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        
        # Scan the file
        components = scanner.scan_file(env_file)
        
        # Should detect all messaging URLs
        assert len(components) == 4
        
        messaging_names = [c.name for c in components]
        assert "rabbitmq" in messaging_names
        assert "kafka" in messaging_names
        assert "redis" in messaging_names
        assert "activemq" in messaging_names
    
    def test_scan_file_with_no_messaging_config(self, tmp_path):
        """Test scanning file with no messaging configuration."""
        scanner = MessagingScanner()
        
        # Create test file without messaging config
        test_content = """
# Some random configuration
app.name=MyApp
app.version=1.0.0
logging.level=INFO
database.url=jdbc:postgresql://localhost:5432/mydb
"""
        
        test_file = tmp_path / "application.properties"
        test_file.write_text(test_content)
        
        # Scan the file
        components = scanner.scan_file(test_file)
        
        # Should detect no messaging components
        assert len(components) == 0
    
    def test_scan_invalid_file(self, tmp_path):
        """Test scanning invalid or malformed file."""
        scanner = MessagingScanner()
        
        # Create invalid JSON file
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{invalid json content")
        
        # Scan the file - should not raise exception
        components = scanner.scan_file(invalid_file)
        
        # Should return empty list for invalid files
        assert len(components) == 0
    
    def test_can_handle_file(self, tmp_path):
        """Test file handling capability."""
        scanner = MessagingScanner()
        
        # Test supported files
        properties_file = tmp_path / "application.properties"
        yaml_file = tmp_path / "messaging.yml"
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