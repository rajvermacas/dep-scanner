"""Monitoring and observability tool detector for Stage 7."""

import json
import logging
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureComponent, InfrastructureType
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class MonitoringDetector(BaseInfrastructureScanner):
    """Detector for monitoring and observability tools."""
    
    # Monitoring tool patterns for detection
    MONITORING_PATTERNS = {
        # APM Tools
        "datadog": {
            "patterns": [r"datadog", r"dd-agent", r"api_key", r"app_key"],
            "subtype": "apm",
            "service": "datadog"
        },
        "newrelic": {
            "patterns": [r"newrelic", r"license_key", r"app_name"],
            "subtype": "apm", 
            "service": "newrelic"
        },
        "dynatrace": {
            "patterns": [r"dynatrace", r"dt_api_token", r"tenant"],
            "subtype": "apm",
            "service": "dynatrace"
        },
        "appdynamics": {
            "patterns": [r"appdynamics", r"controller-host", r"application-name"],
            "subtype": "apm",
            "service": "appdynamics"
        },
        
        # Metrics and Monitoring
        "prometheus": {
            "patterns": [r"prometheus", r"scrape_configs", r"scrape_interval"],
            "subtype": "monitoring",
            "service": "prometheus"
        },
        "grafana": {
            "patterns": [r"grafana", r"GF_SECURITY", r"grafana/grafana"],
            "subtype": "visualization",
            "service": "grafana"
        },
        "alertmanager": {
            "patterns": [r"alertmanager", r"prom/alertmanager"],
            "subtype": "alerting",
            "service": "alertmanager"
        },
        "node-exporter": {
            "patterns": [r"node-exporter", r"prom/node-exporter"],
            "subtype": "metrics_collection",
            "service": "node-exporter"
        },
        
        # Logging Solutions
        "elasticsearch": {
            "patterns": [r"elasticsearch", r"elastic\.co/elasticsearch"],
            "subtype": "search",
            "service": "elasticsearch"
        },
        "logstash": {
            "patterns": [r"logstash", r"elastic\.co/logstash"],
            "subtype": "log_processing",
            "service": "logstash"
        },
        "kibana": {
            "patterns": [r"kibana", r"elastic\.co/kibana"],
            "subtype": "visualization",
            "service": "kibana"
        },
        "splunk": {
            "patterns": [r"splunk", r"tcpout", r"monitor://"],
            "subtype": "logging",
            "service": "splunk"
        },
        "fluentd": {
            "patterns": [r"fluentd", r"fluent/fluentd"],
            "subtype": "log_collection",
            "service": "fluentd"
        },
        "filebeat": {
            "patterns": [r"filebeat", r"elastic\.co/beats/filebeat"],
            "subtype": "log_collection",
            "service": "filebeat"
        },
        
        # Distributed Tracing
        "jaeger": {
            "patterns": [r"jaeger", r"jaegertracing", r"COLLECTOR_OTLP"],
            "subtype": "distributed_tracing",
            "service": "jaeger"
        },
        "zipkin": {
            "patterns": [r"zipkin", r"openzipkin"],
            "subtype": "distributed_tracing",
            "service": "zipkin"
        },
        
        # Cloud Monitoring
        "cloudwatch": {
            "patterns": [r"cloudwatch", r"aws-cloudwatch", r"logs-group"],
            "subtype": "cloud_monitoring",
            "service": "cloudwatch"
        },
        "azure-monitor": {
            "patterns": [r"azure.*monitor", r"application-insights"],
            "subtype": "cloud_monitoring",
            "service": "azure-monitor"
        },
        "stackdriver": {
            "patterns": [r"stackdriver", r"google.*monitoring"],
            "subtype": "cloud_monitoring", 
            "service": "stackdriver"
        }
    }
    
    def get_name(self) -> str:
        """Get the scanner name."""
        return "monitoring"
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Get the infrastructure type this scanner handles."""
        return InfrastructureType.MONITORING
    
    def get_supported_file_patterns(self) -> List[str]:
        """Get list of supported file patterns."""
        return [
            "*.yml", "*.yaml", "*.json", "*.properties", "*.xml", 
            "*.conf", "*.config", "docker-compose.yml", "docker-compose.yaml"
        ]
    
    def can_scan_file(self, file_path: Path) -> bool:
        """Check if this scanner can process the given file."""
        # Check file extension and name patterns (don't require existence for pattern check)
        supported_patterns = self.get_supported_file_patterns()
        
        for pattern in supported_patterns:
            if pattern.startswith("*."):
                # Extension pattern
                ext = pattern[1:]  # Remove the *
                if file_path.suffix == ext:
                    return True
            else:
                # Literal filename pattern
                if file_path.name == pattern:
                    return True
        
        return False
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a file for monitoring tool configurations."""
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Try to parse as YAML first, then JSON
            config_data = None
            try:
                config_data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                logger.debug(f"Failed to parse as YAML: {e}")
                try:
                    config_data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse as JSON: {e}")
                    # Try to parse as properties or config file
                    config_data = self._parse_config_file(content)
            
            if not config_data:
                logger.debug(f"No parseable configuration found in {file_path}")
                return []
            
            return self._analyze_config_for_monitoring(config_data, file_path, content)
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            return []
    
    def _parse_config_file(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse configuration files like .properties or .conf files."""
        config = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
        
        return config if config else None
    
    def _analyze_config_for_monitoring(
        self, 
        config_data: Dict[str, Any], 
        file_path: Path,
        content: str
    ) -> List[InfrastructureComponent]:
        """Analyze configuration data for monitoring tools."""
        components = []
        
        # Check for Docker Compose services
        if isinstance(config_data, dict) and "services" in config_data:
            components.extend(self._scan_docker_compose_services(config_data["services"], file_path))
        else:
            # Only check for direct monitoring configurations if it's not a Docker Compose file
            components.extend(self._scan_direct_monitoring_config(config_data, file_path, content))
        
        return components
    
    def _scan_docker_compose_services(
        self, 
        services: Dict[str, Any], 
        file_path: Path
    ) -> List[InfrastructureComponent]:
        """Scan Docker Compose services for monitoring tools."""
        components = []
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue
                
            image = service_config.get("image", "")
            environment = service_config.get("environment", [])
            
            # Check service name and image for monitoring patterns
            for tool_name, tool_config in self.MONITORING_PATTERNS.items():
                if self._matches_monitoring_tool(
                    service_name, image, environment, tool_config["patterns"]
                ):
                    component = InfrastructureComponent(
                        type=self.get_infrastructure_type(),
                        name=tool_name,
                        service=tool_config["service"],
                        subtype=tool_config["subtype"],
                        configuration=self._extract_service_config(service_config),
                        source_file=str(file_path),
                        line_number=None,
                        classification=DependencyType.UNKNOWN,
                        metadata={
                            "docker_service": service_name,
                            "image": image,
                            "detection_method": "docker_compose"
                        }
                    )
                    components.append(component)
                    break
        
        return components
    
    def _scan_direct_monitoring_config(
        self, 
        config_data: Dict[str, Any], 
        file_path: Path,
        content: str
    ) -> List[InfrastructureComponent]:
        """Scan for direct monitoring tool configurations."""
        components = []
        
        # Convert config to string for pattern matching
        config_str = json.dumps(config_data, default=str).lower()
        
        # Prioritize certain tools over others to avoid duplicates
        # Prometheus config files should only be detected as Prometheus, not node-exporter
        tool_priority = ["prometheus", "datadog", "newrelic", "splunk", "jaeger"]
        
        found_primary_tool = False
        
        # Check high-priority tools first
        for tool_name in tool_priority:
            if tool_name in self.MONITORING_PATTERNS:
                tool_config = self.MONITORING_PATTERNS[tool_name]
                if self._matches_monitoring_patterns(config_str, content, tool_config["patterns"]):
                    component = InfrastructureComponent(
                        type=self.get_infrastructure_type(),
                        name=tool_name,
                        service=tool_config["service"],
                        subtype=tool_config["subtype"],
                        configuration=self._extract_tool_specific_config(
                            config_data, tool_name, content
                        ),
                        source_file=str(file_path),
                        line_number=None,
                        classification=DependencyType.UNKNOWN,
                        metadata={
                            "detection_method": "direct_config",
                            "config_type": self._determine_config_type(file_path)
                        }
                    )
                    components.append(component)
                    found_primary_tool = True
                    break  # Only return the first primary tool found
        
        # If no primary tool found, check other tools
        if not found_primary_tool:
            for tool_name, tool_config in self.MONITORING_PATTERNS.items():
                if tool_name not in tool_priority:
                    if self._matches_monitoring_patterns(config_str, content, tool_config["patterns"]):
                        component = InfrastructureComponent(
                            type=self.get_infrastructure_type(),
                            name=tool_name,
                            service=tool_config["service"],
                            subtype=tool_config["subtype"],
                            configuration=self._extract_tool_specific_config(
                                config_data, tool_name, content
                            ),
                            source_file=str(file_path),
                            line_number=None,
                            classification=DependencyType.UNKNOWN,
                            metadata={
                                "detection_method": "direct_config",
                                "config_type": self._determine_config_type(file_path)
                            }
                        )
                        components.append(component)
                        break  # Only return the first tool found
        
        return components
    
    def _matches_monitoring_tool(
        self, 
        service_name: str, 
        image: str, 
        environment: List[str], 
        patterns: List[str]
    ) -> bool:
        """Check if service matches monitoring tool patterns."""
        text_to_check = f"{service_name} {image} {' '.join(environment)}".lower()
        
        for pattern in patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True
        
        return False
    
    def _matches_monitoring_patterns(
        self, 
        config_str: str, 
        content: str, 
        patterns: List[str]
    ) -> bool:
        """Check if content matches monitoring patterns."""
        text_to_check = f"{config_str} {content}".lower()
        
        for pattern in patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_service_config(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant configuration from Docker service."""
        extracted_config = {}
        
        # Extract key configuration elements
        if "ports" in service_config:
            extracted_config["ports"] = service_config["ports"]
        if "environment" in service_config:
            extracted_config["environment"] = service_config["environment"]
        if "volumes" in service_config:
            extracted_config["volumes"] = service_config["volumes"]
        if "image" in service_config:
            extracted_config["image"] = service_config["image"]
        
        return extracted_config
    
    def _extract_tool_specific_config(
        self, 
        config_data: Dict[str, Any], 
        tool_name: str,
        content: str
    ) -> Dict[str, Any]:
        """Extract tool-specific configuration."""
        extracted_config = {}
        
        if tool_name == "prometheus":
            if "scrape_configs" in config_data:
                extracted_config["scrape_configs"] = config_data["scrape_configs"]
                # Extract job names
                jobs = []
                for scrape_config in config_data["scrape_configs"]:
                    if isinstance(scrape_config, dict) and "job_name" in scrape_config:
                        jobs.append(scrape_config["job_name"])
                extracted_config["jobs"] = jobs
            if "global" in config_data:
                extracted_config["global"] = config_data["global"]
                
        elif tool_name == "datadog":
            if "apm_config" in config_data:
                extracted_config["apm_config"] = config_data["apm_config"]
            if "logs_enabled" in config_data:
                extracted_config["logs_enabled"] = config_data["logs_enabled"]
                
        elif tool_name == "newrelic":
            if "distributed_tracing" in config_data:
                extracted_config["distributed_tracing"] = config_data["distributed_tracing"]
            if "application_logging" in config_data:
                extracted_config["application_logging"] = config_data["application_logging"]
                
        elif tool_name == "splunk":
            # Extract monitor paths from Splunk configuration
            monitor_paths = []
            for line in content.split('\n'):
                if line.strip().startswith('[monitor:'):
                    path = line.strip()[9:-1]  # Extract path from [monitor:path]
                    monitor_paths.append(path)
            if monitor_paths:
                extracted_config["monitor_paths"] = monitor_paths
        
        # Add any remaining relevant config
        for key, value in config_data.items():
            if key not in extracted_config and not key.startswith('_'):
                extracted_config[key] = value
        
        return extracted_config
    
    def _determine_config_type(self, file_path: Path) -> str:
        """Determine the type of configuration file."""
        if file_path.suffix in ['.yml', '.yaml']:
            return "yaml"
        elif file_path.suffix == '.json':
            return "json"
        elif file_path.suffix in ['.properties', '.conf', '.config']:
            return "properties"
        else:
            return "unknown"