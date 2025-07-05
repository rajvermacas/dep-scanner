"""Docker scanner for container technology detection."""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent
)
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class DockerScanner(BaseInfrastructureScanner):
    """Scanner for Docker configuration files."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return supported file patterns for Docker files."""
        return ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.CONTAINER
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a Docker file for infrastructure components."""
        try:
            if file_path.name == "Dockerfile":
                return self._scan_dockerfile(file_path)
            elif file_path.name.startswith("docker-compose"):
                return self._scan_docker_compose(file_path)
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error scanning Docker file {file_path}: {e}")
            return []
    
    def _scan_dockerfile(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a Dockerfile for configuration."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                return []
            
            config = self._parse_dockerfile(content)
            
            if not config:
                return []
            
            component = InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name="dockerfile",
                service="docker",
                subtype="dockerfile",
                configuration=config,
                source_file=str(file_path),
                classification=DependencyType.UNKNOWN
            )
            
            return [component]
            
        except Exception as e:
            logger.error(f"Error parsing Dockerfile {file_path}: {e}")
            return []
    
    def _scan_docker_compose(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a docker-compose file for services and configuration."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f)
            
            if not compose_data:
                return []
            
            components = []
            
            # Add main compose component
            compose_config = {
                "version": compose_data.get("version", "unknown"),
                "services_count": len(compose_data.get("services", {})),
                "volumes": list(compose_data.get("volumes", {}).keys()),
                "networks": list(compose_data.get("networks", {}).keys())
            }
            
            compose_component = InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name="docker-compose",
                service="docker",
                subtype="docker-compose",
                configuration=compose_config,
                source_file=str(file_path),
                classification=DependencyType.UNKNOWN
            )
            components.append(compose_component)
            
            # Add individual services
            services = compose_data.get("services", {})
            for service_name, service_config in services.items():
                service_component = InfrastructureComponent(
                    type=self.get_infrastructure_type(),
                    name=service_name,
                    service="docker",
                    subtype="service",
                    configuration=service_config,
                    source_file=str(file_path),
                    classification=DependencyType.UNKNOWN
                )
                components.append(service_component)
            
            return components
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML in {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing docker-compose file {file_path}: {e}")
            return []
    
    def _parse_dockerfile(self, content: str) -> Dict[str, Any]:
        """Parse Dockerfile content and extract configuration."""
        config = {
            "base_images": [],
            "stages": [],
            "exposed_ports": [],
            "env": {},
            "args": {},
            "volumes": [],
            "workdir": None,
            "user": None,
            "cmd": None,
            "entrypoint": None
        }
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # FROM instruction
            from_match = re.match(r'FROM\s+([^\s]+)(?:\s+AS\s+([^\s]+))?', line, re.IGNORECASE)
            if from_match:
                base_image = from_match.group(1)
                stage_name = from_match.group(2)
                
                config["base_images"].append(base_image)
                if stage_name:
                    config["stages"].append(stage_name)
                
                # For backward compatibility, keep base_image for single-stage
                if len(config["base_images"]) == 1:
                    config["base_image"] = base_image
                continue
            
            # EXPOSE instruction
            expose_match = re.match(r'EXPOSE\s+(.+)', line, re.IGNORECASE)
            if expose_match:
                ports = expose_match.group(1).split()
                config["exposed_ports"].extend(ports)
                continue
            
            # ENV instruction
            env_match = re.match(r'ENV\s+([^\s=]+)(?:=(.+)|\s+(.+))', line, re.IGNORECASE)
            if env_match:
                key = env_match.group(1)
                value = env_match.group(2) or env_match.group(3) or ""
                config["env"][key] = value.strip()
                continue
            
            # ARG instruction
            arg_match = re.match(r'ARG\s+([^\s=]+)(?:=(.+))?', line, re.IGNORECASE)
            if arg_match:
                key = arg_match.group(1)
                value = arg_match.group(2) or ""
                config["args"][key] = value.strip()
                continue
            
            # WORKDIR instruction
            workdir_match = re.match(r'WORKDIR\s+(.+)', line, re.IGNORECASE)
            if workdir_match:
                config["workdir"] = workdir_match.group(1).strip()
                continue
            
            # USER instruction
            user_match = re.match(r'USER\s+(.+)', line, re.IGNORECASE)
            if user_match:
                config["user"] = user_match.group(1).strip()
                continue
            
            # VOLUME instruction
            volume_match = re.match(r'VOLUME\s+(.+)', line, re.IGNORECASE)
            if volume_match:
                volume_spec = volume_match.group(1).strip()
                # Handle both ["vol1", "vol2"] and /path formats
                if volume_spec.startswith('['):
                    # Parse JSON-like array
                    volumes = re.findall(r'"([^"]+)"', volume_spec)
                    config["volumes"].extend(volumes)
                else:
                    config["volumes"].append(volume_spec)
                continue
            
            # CMD instruction
            cmd_match = re.match(r'CMD\s+(.+)', line, re.IGNORECASE)
            if cmd_match:
                config["cmd"] = cmd_match.group(1).strip()
                continue
            
            # ENTRYPOINT instruction
            entrypoint_match = re.match(r'ENTRYPOINT\s+(.+)', line, re.IGNORECASE)
            if entrypoint_match:
                config["entrypoint"] = entrypoint_match.group(1).strip()
                continue
        
        # Clean up empty lists and None values for cleaner output
        cleaned_config = {}
        for key, value in config.items():
            if value is not None and value != [] and value != {}:
                cleaned_config[key] = value
        
        return cleaned_config