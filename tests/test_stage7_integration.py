"""Integration tests for Stage 7: Monitoring, Visualization, and Advanced Features."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from dependency_scanner_tool.infrastructure_scanners.manager import InfrastructureScannerManager
from dependency_scanner_tool.infrastructure_scanners.monitoring import MonitoringDetector
from dependency_scanner_tool.infrastructure_scanners.stack_visualizer import StackVisualizer
from dependency_scanner_tool.models.infrastructure import InfrastructureType, InfrastructureComponent
from dependency_scanner_tool.scanner import DependencyType, Dependency


class TestStage7Integration:
    """Integration tests for Stage 7 infrastructure scanning."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.manager = InfrastructureScannerManager()
        self.visualizer = StackVisualizer()
    
    def test_monitoring_detector_registration(self):
        """Test that MonitoringDetector is properly registered."""
        registry = self.manager.get_registry()
        
        # Check that monitoring detector is registered
        monitoring_scanner = registry.get("monitoring")
        assert monitoring_scanner is not None
        assert isinstance(monitoring_scanner, MonitoringDetector)
        
        # Verify scanner properties
        assert monitoring_scanner.get_name() == "monitoring"
        assert monitoring_scanner.get_infrastructure_type() == InfrastructureType.MONITORING
    
    def test_comprehensive_monitoring_stack_detection(self):
        """Test detection of a comprehensive monitoring stack."""
        # Create a complex monitoring configuration
        prometheus_config = '''
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
  
  - job_name: 'app-metrics'
    static_configs:
      - targets: ['localhost:8080']
'''
        
        docker_compose_monitoring = '''
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
  
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
  
  logstash:
    image: docker.elastic.co/logstash/logstash:7.15.0
    ports:
      - "5000:5000"
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  
  kibana:
    image: docker.elastic.co/kibana/kibana:7.15.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  grafana-storage:
'''
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write Prometheus config
            prometheus_file = temp_path / "prometheus.yml"
            prometheus_file.write_text(prometheus_config)
            
            # Write Docker Compose config
            compose_file = temp_path / "docker-compose.yml"
            compose_file.write_text(docker_compose_monitoring)
            
            # Scan the directory
            components = self.manager.scan_directory(temp_path)
            
            # Filter monitoring components
            monitoring_components = [
                c for c in components 
                if c.type == InfrastructureType.MONITORING
            ]
            
            assert len(monitoring_components) >= 5  # Prometheus, Grafana, Elasticsearch, Logstash, Kibana
            
            # Check that we detected all major monitoring tools
            component_names = [c.name for c in monitoring_components]
            assert "prometheus" in component_names
            assert "grafana" in component_names
            assert "elasticsearch" in component_names
            assert "logstash" in component_names
            assert "kibana" in component_names
            
            # Verify component details - should have at least one Prometheus component
            prometheus_components = [c for c in monitoring_components if c.name == "prometheus"]
            assert len(prometheus_components) >= 1
            
            # Check if we have a direct config prometheus (from prometheus.yml)
            direct_config_prometheus = [
                c for c in prometheus_components 
                if c.metadata.get("detection_method") == "direct_config"
            ]
            
            if direct_config_prometheus:
                prometheus_component = direct_config_prometheus[0]
                assert "jobs" in prometheus_component.configuration
                assert len(prometheus_component.configuration["jobs"]) >= 2
    
    def test_monitoring_with_other_infrastructure_components(self):
        """Test monitoring detection alongside other infrastructure components."""
        # Create a mixed infrastructure project
        terraform_config = '''
resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t2.micro"
}

resource "aws_s3_bucket" "storage" {
  bucket = "my-app-storage"
}
'''
        
        k8s_config = '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: nginx:1.20
        ports:
        - containerPort: 80
'''
        
        monitoring_config = '''
version: '3.8'
services:
  datadog-agent:
    image: datadog/agent:latest
    environment:
      - DD_API_KEY=your-api-key
      - DD_SITE=datadoghq.com
      - DD_LOGS_ENABLED=true
      - DD_APM_ENABLED=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write files
            (temp_path / "main.tf").write_text(terraform_config)
            (temp_path / "deployment.yaml").write_text(k8s_config)
            (temp_path / "monitoring.yml").write_text(monitoring_config)
            
            # Scan the directory
            components = self.manager.scan_directory(temp_path)
            
            # Should have components from multiple stages
            infrastructure_types = {c.type for c in components}
            assert InfrastructureType.IaC in infrastructure_types  # Terraform
            assert InfrastructureType.CONTAINER in infrastructure_types  # Kubernetes
            assert InfrastructureType.MONITORING in infrastructure_types  # Datadog
            
            # Check monitoring components
            monitoring_components = [
                c for c in components 
                if c.type == InfrastructureType.MONITORING
            ]
            assert len(monitoring_components) >= 1
            
            datadog_component = next(c for c in monitoring_components if c.name == "datadog")
            assert datadog_component.subtype == "apm"
            assert datadog_component.service == "datadog"
    
    def test_technology_stack_visualization_integration(self):
        """Test integration of technology stack visualization with infrastructure scanning."""
        # Mock dependencies (would come from dependency scanning)
        dependencies = [
            Dependency(name="flask", version="2.0.1", dependency_type=DependencyType.ALLOWED),
            Dependency(name="react", version="17.0.0", dependency_type=DependencyType.ALLOWED),
            Dependency(name="postgresql", version="13.0", dependency_type=DependencyType.ALLOWED),
            Dependency(name="pytest", version="6.2.4", dependency_type=DependencyType.ALLOWED),
        ]
        
        # Create infrastructure components
        infrastructure_config = '''
version: '3.8'
services:
  web:
    image: nginx:1.20
    ports:
      - "80:80"
  
  api:
    build: .
    ports:
      - "5000:5000"
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
  
  redis:
    image: redis:6
    ports:
      - "6379:6379"
  
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            compose_file = temp_path / "docker-compose.yml"
            compose_file.write_text(infrastructure_config)
            
            # Scan infrastructure
            infrastructure_components = self.manager.scan_directory(temp_path)
            
            # Generate technology stack summary
            stack_summary = self.visualizer.generate_technology_stack_summary(
                dependencies, infrastructure_components
            )
            
            assert isinstance(stack_summary, dict)
            assert "categories" in stack_summary
            
            # Should have categorized both dependencies and infrastructure
            categories = stack_summary["categories"]
            assert "backend" in categories  # Flask
            assert "frontend" in categories  # React
            assert "containerization" in categories  # Docker services
            assert "databases" in categories  # PostgreSQL, Redis
            assert "monitoring" in categories  # Prometheus, Grafana
            
            # Generate diagram data
            diagram_data = self.visualizer.generate_diagram_data(stack_summary)
            
            assert "nodes" in diagram_data
            assert "edges" in diagram_data
            assert "layers" in diagram_data
            
            # Should have nodes for all technologies
            node_names = [node["name"] for node in diagram_data["nodes"]]
            assert "flask" in node_names
            assert "react" in node_names
            assert "prometheus" in node_names
            assert "grafana" in node_names
            
            # Should have architecture layers
            layers = diagram_data["layers"]
            assert "presentation" in layers
            assert "application" in layers
            assert "data" in layers
            assert "monitoring" in layers
    
    def test_stage7_performance_large_monitoring_stack(self):
        """Test Stage 7 performance with large monitoring configurations."""
        # Create a large monitoring configuration
        large_prometheus_config = '''
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
'''
        
        # Add many scrape configs
        for i in range(20):
            large_prometheus_config += f'''
  - job_name: 'service-{i}'
    static_configs:
      - targets: ['service-{i}:8080']
'''
        
        large_compose_config = '''
version: '3.8'
services:
'''
        
        # Add many monitoring services
        monitoring_services = [
            "prometheus", "grafana", "alertmanager", "node-exporter",
            "elasticsearch", "logstash", "kibana", "filebeat",
            "jaeger", "zipkin", "tempo", "loki"
        ]
        
        for i, service in enumerate(monitoring_services):
            large_compose_config += f'''
  {service}:
    image: {service}:latest
    ports:
      - "{9000 + i}:{9000 + i}"
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write large configs
            (temp_path / "prometheus.yml").write_text(large_prometheus_config)
            (temp_path / "docker-compose.yml").write_text(large_compose_config)
            
            # Time the scanning
            import time
            start_time = time.time()
            
            components = self.manager.scan_directory(temp_path)
            
            scan_time = time.time() - start_time
            
            # Should complete within reasonable time (< 5 seconds)
            assert scan_time < 5.0
            
            # Should detect many monitoring components
            monitoring_components = [
                c for c in components 
                if c.type == InfrastructureType.MONITORING
            ]
            assert len(monitoring_components) >= 10
    
    def test_optimization_recommendations_generation(self):
        """Test generation of optimization recommendations."""
        # Create infrastructure with potential optimizations
        config_with_redundancy = '''
version: '3.8'
services:
  mysql-primary:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
  
  mysql-secondary:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
  
  postgresql:
    image: postgres:13
    environment:
      - POSTGRES_PASSWORD=password
  
  prometheus-1:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
  
  prometheus-2:
    image: prom/prometheus:latest
    ports:
      - "9091:9091"
  
  datadog-agent:
    image: datadog/agent:latest
    environment:
      - DD_API_KEY=key
  
  newrelic-agent:
    image: newrelic/infrastructure:latest
    environment:
      - NRIA_LICENSE_KEY=key
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            compose_file = temp_path / "docker-compose.yml"
            compose_file.write_text(config_with_redundancy)
            
            # Scan infrastructure
            components = self.manager.scan_directory(temp_path)
            
            # Generate optimization recommendations
            recommendations = self.visualizer.generate_optimization_recommendations(components)
            
            assert isinstance(recommendations, list)
            assert len(recommendations) > 0
            
            # Should detect database redundancy
            db_recommendations = [
                r for r in recommendations 
                if "database" in r["issue"].lower()
            ]
            assert len(db_recommendations) > 0
            
            # Should detect monitoring complexity
            monitoring_recommendations = [
                r for r in recommendations 
                if "monitoring" in r["issue"].lower()
            ]
            assert len(monitoring_recommendations) > 0
    
    def test_stage7_with_ignore_patterns(self):
        """Test Stage 7 scanning with ignore patterns."""
        monitoring_config = '''
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create files in different directories
            main_compose = temp_path / "docker-compose.yml"
            main_compose.write_text(monitoring_config)
            
            # Create ignored directory
            node_modules = temp_path / "node_modules"
            node_modules.mkdir()
            ignored_compose = node_modules / "docker-compose.yml"
            ignored_compose.write_text(monitoring_config)
            
            # Scan with ignore patterns
            ignore_patterns = ["node_modules", "*.tmp"]
            components = self.manager.scan_directory(temp_path, ignore_patterns)
            
            # Should only find components from main file, not ignored directory
            monitoring_components = [
                c for c in components 
                if c.type == InfrastructureType.MONITORING
            ]
            
            assert len(monitoring_components) == 1
            assert monitoring_components[0].source_file == str(main_compose)
    
    def test_mermaid_diagram_generation_integration(self):
        """Test Mermaid diagram generation with real infrastructure data."""
        # Create a realistic tech stack
        stack_config = '''
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
  
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    depends_on:
      - database
      - redis
  
  database:
    image: postgres:13
    environment:
      - POSTGRES_DB=app
  
  redis:
    image: redis:6
  
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
'''
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            compose_file = temp_path / "docker-compose.yml"
            compose_file.write_text(stack_config)
            
            # Scan infrastructure
            components = self.manager.scan_directory(temp_path)
            
            # Create mock dependencies
            dependencies = [
                Dependency(name="react", version="17.0.0", dependency_type=DependencyType.ALLOWED),
                Dependency(name="flask", version="2.0.1", dependency_type=DependencyType.ALLOWED),
            ]
            
            # Generate stack summary and diagram
            stack_summary = self.visualizer.generate_technology_stack_summary(
                dependencies, components
            )
            diagram_data = self.visualizer.generate_diagram_data(stack_summary)
            
            # Generate Mermaid diagram
            mermaid_syntax = self.visualizer.generate_mermaid_diagram(diagram_data)
            
            assert isinstance(mermaid_syntax, str)
            assert "graph TD" in mermaid_syntax
            assert "-->" in mermaid_syntax
            
            # Should include technology names
            assert "react" in mermaid_syntax or "frontend" in mermaid_syntax
            assert "flask" in mermaid_syntax or "backend" in mermaid_syntax
            assert "prometheus" in mermaid_syntax
    
    def test_stage7_comprehensive_scan(self):
        """Test comprehensive Stage 7 scanning with all features."""
        # Create a complex project structure
        project_configs = {
            "docker-compose.yml": '''
version: '3.8'
services:
  web:
    image: nginx:1.20
  api:
    build: .
  db:
    image: postgres:13
  prometheus:
    image: prom/prometheus:latest
  grafana:
    image: grafana/grafana:latest
''',
            "monitoring/prometheus.yml": '''
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['api:5000']
''',
            "monitoring/datadog.json": '''
{
  "api_key": "your-api-key",
  "apm_config": {
    "enabled": true,
    "env": "production"
  }
}
''',
            "k8s/deployment.yaml": '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: web
        image: nginx:1.20
''',
            "terraform/main.tf": '''
resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t2.micro"
}
'''
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create project structure
            for file_path, content in project_configs.items():
                full_path = temp_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            # Scan entire project
            components = self.manager.scan_directory(temp_path)
            
            # Should detect components from all stages including Stage 7
            infrastructure_types = {c.type for c in components}
            assert InfrastructureType.CONTAINER in infrastructure_types
            assert InfrastructureType.MONITORING in infrastructure_types
            assert InfrastructureType.IaC in infrastructure_types
            
            # Verify monitoring components
            monitoring_components = [
                c for c in components 
                if c.type == InfrastructureType.MONITORING
            ]
            assert len(monitoring_components) >= 3  # Prometheus, Grafana, Datadog
            
            monitoring_names = [c.name for c in monitoring_components]
            assert "prometheus" in monitoring_names
            assert "grafana" in monitoring_names
            assert "datadog" in monitoring_names
            
            # Test technology stack analysis
            mock_dependencies = [
                Dependency(name="react", version="17.0.0", dependency_type=DependencyType.ALLOWED),
                Dependency(name="flask", version="2.0.1", dependency_type=DependencyType.ALLOWED),
                Dependency(name="boto3", version="1.18.0", dependency_type=DependencyType.ALLOWED),
            ]
            
            stack_summary = self.visualizer.generate_technology_stack_summary(
                mock_dependencies, components
            )
            
            # Should have comprehensive categorization
            categories = stack_summary["categories"]
            assert len(categories) >= 5
            
            # Should detect technology patterns
            patterns = stack_summary.get("technology_patterns", [])
            microservices_pattern = any(
                "microservices" in p.get("pattern", "").lower() 
                for p in patterns
            )
            # Microservices pattern should be detected due to Kubernetes + Docker + messaging
            
            # Generate optimization recommendations
            recommendations = self.visualizer.generate_optimization_recommendations(components)
            assert isinstance(recommendations, list)