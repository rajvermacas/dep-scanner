"""Tests for MonitoringDetector - Stage 7 monitoring and observability tool detection."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import json

from dependency_scanner_tool.infrastructure_scanners.monitoring import MonitoringDetector
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType


class TestMonitoringDetector:
    """Test suite for MonitoringDetector."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.detector = MonitoringDetector()
    
    def test_detector_initialization(self):
        """Test MonitoringDetector initialization."""
        assert self.detector is not None
        assert self.detector.get_name() == "monitoring"
        assert self.detector.get_infrastructure_type() == InfrastructureType.MONITORING
    
    def test_supported_file_patterns(self):
        """Test supported file patterns for monitoring detection."""
        patterns = self.detector.get_supported_file_patterns()
        
        # Should support common monitoring configuration files
        expected_patterns = [
            "*.yml", "*.yaml", "*.json", "*.properties", "*.xml", "*.conf", "*.config"
        ]
        
        for pattern in expected_patterns:
            assert pattern in patterns
    
    def test_can_scan_monitoring_files(self):
        """Test that detector can scan monitoring configuration files."""
        # Test YAML files
        assert self.detector.can_scan_file(Path("docker-compose.yml"))
        assert self.detector.can_scan_file(Path("prometheus.yml"))
        assert self.detector.can_scan_file(Path("grafana.yml"))
        
        # Test JSON files
        assert self.detector.can_scan_file(Path("newrelic.json"))
        assert self.detector.can_scan_file(Path("datadog.json"))
        
        # Test properties files
        assert self.detector.can_scan_file(Path("application.properties"))
        assert self.detector.can_scan_file(Path("log4j.properties"))
        
        # Should not scan non-monitoring files
        assert not self.detector.can_scan_file(Path("test.txt"))
        assert not self.detector.can_scan_file(Path("README.md"))
    
    def test_detect_prometheus_monitoring(self):
        """Test detection of Prometheus monitoring configuration."""
        content = '''
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
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            
            assert len(components) == 1
            component = components[0]
            
            assert component.name == "prometheus"
            assert component.service == "prometheus"
            assert component.subtype == "monitoring"
            assert component.type == InfrastructureType.MONITORING
            assert "scrape_configs" in component.configuration
            assert component.configuration["jobs"] == ["prometheus", "node-exporter"]
    
    def test_detect_grafana_monitoring(self):
        """Test detection of Grafana monitoring configuration."""
        content = '''
version: '3.8'
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
      
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  grafana-storage:
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            
            # Should detect both Grafana and Prometheus
            assert len(components) == 2
            
            grafana_component = next(c for c in components if c.name == "grafana")
            prometheus_component = next(c for c in components if c.name == "prometheus")
            
            assert grafana_component.service == "grafana"
            assert prometheus_component.service == "prometheus"
            assert grafana_component.subtype == "visualization"
            assert prometheus_component.subtype == "monitoring"
    
    def test_detect_datadog_apm(self):
        """Test detection of Datadog APM configuration."""
        content = '''
{
  "api_key": "your-api-key",
  "app_key": "your-app-key",
  "site": "datadoghq.com",
  "logs_enabled": true,
  "log_level": "info",
  "apm_config": {
    "enabled": true,
    "env": "production",
    "service": "my-app"
  }
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            
            assert len(components) == 1
            component = components[0]
            
            assert component.name == "datadog"
            assert component.service == "datadog"
            assert component.subtype == "apm"
            assert component.type == InfrastructureType.MONITORING
            assert "apm_config" in component.configuration
    
    def test_detect_elk_stack(self):
        """Test detection of ELK (Elasticsearch, Logstash, Kibana) stack."""
        content = '''
version: '3.8'
services:
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
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            
            # Should detect all three ELK components
            assert len(components) == 3
            
            component_names = [c.name for c in components]
            assert "elasticsearch" in component_names
            assert "logstash" in component_names
            assert "kibana" in component_names
            
            # Check component types
            for component in components:
                assert component.type == InfrastructureType.MONITORING
                if component.name == "elasticsearch":
                    assert component.subtype == "search"
                elif component.name == "logstash":
                    assert component.subtype == "log_processing"
                elif component.name == "kibana":
                    assert component.subtype == "visualization"
    
    def test_detect_newrelic_apm(self):
        """Test detection of New Relic APM configuration."""
        content = '''
# New Relic Java Agent Configuration
app_name: My Application
license_key: your_license_key_here
log_level: info
audit_mode: false

# Application Logging
application_logging:
  enabled: true
  forwarding:
    enabled: true
    max_samples_stored: 10000
  local_decorating:
    enabled: true
    
# Distributed Tracing
distributed_tracing:
  enabled: true
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            
            assert len(components) == 1
            component = components[0]
            
            assert component.name == "newrelic"
            assert component.service == "newrelic"
            assert component.subtype == "apm"
            assert component.type == InfrastructureType.MONITORING
            assert "distributed_tracing" in component.configuration
    
    def test_detect_splunk_logging(self):
        """Test detection of Splunk logging configuration."""
        content = '''
# Splunk Universal Forwarder Configuration
[tcpout]
defaultGroup = splunk_servers

[tcpout:splunk_servers]
server = splunk.example.com:9997
compressed = true

[monitor:///var/log/app/]
sourcetype = app_logs
index = application

[monitor:///var/log/nginx/]
sourcetype = nginx_access
index = web_logs
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            
            assert len(components) == 1
            component = components[0]
            
            assert component.name == "splunk"
            assert component.service == "splunk"
            assert component.subtype == "logging"
            assert component.type == InfrastructureType.MONITORING
            assert "monitor_paths" in component.configuration
    
    def test_detect_jaeger_tracing(self):
        """Test detection of Jaeger distributed tracing."""
        content = '''
version: '3.8'
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
    volumes:
      - jaeger-data:/badger
      
volumes:
  jaeger-data:
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            
            assert len(components) == 1
            component = components[0]
            
            assert component.name == "jaeger"
            assert component.service == "jaeger"
            assert component.subtype == "distributed_tracing"
            assert component.type == InfrastructureType.MONITORING
            assert "ports" in component.configuration
    
    def test_detect_multiple_monitoring_tools(self):
        """Test detection of multiple monitoring tools in same file."""
        content = '''
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
  
  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
  
  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            
            assert len(components) == 4
            
            component_names = [c.name for c in components]
            assert "prometheus" in component_names
            assert "grafana" in component_names
            assert "alertmanager" in component_names
            assert "node-exporter" in component_names
            
            # All should be monitoring type
            for component in components:
                assert component.type == InfrastructureType.MONITORING
    
    def test_invalid_file_handling(self):
        """Test handling of invalid or non-monitoring files."""
        # Test with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            assert len(components) == 0
        
        # Test with non-monitoring content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("version: '3.8'\nservices:\n  web:\n    image: nginx")
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            assert len(components) == 0
    
    def test_nonexistent_file_handling(self):
        """Test handling of non-existent files."""
        components = self.detector.scan_file(Path("nonexistent.yml"))
        assert len(components) == 0
    
    def test_empty_file_handling(self):
        """Test handling of empty files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("")
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            assert len(components) == 0
    
    @patch('dependency_scanner_tool.infrastructure_scanners.monitoring.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged."""
        # Test with truly invalid YAML that will cause an error
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml:\n  - item\n    - invalid indentation")
            f.flush()
            
            components = self.detector.scan_file(Path(f.name))
            assert len(components) == 0
            
            # Should log debug message for YAML parsing failure
            mock_logger.debug.assert_called()