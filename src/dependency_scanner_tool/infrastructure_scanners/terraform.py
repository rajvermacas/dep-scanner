"""Terraform scanner for Infrastructure as Code detection."""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent
)
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class TerraformScanner(BaseInfrastructureScanner):
    """Scanner for Terraform configuration files."""
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return supported file patterns for Terraform files."""
        return ["*.tf", "*.tfvars"]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.IaC
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a Terraform file for infrastructure components."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if file_path.suffix == '.tfvars':
                return self._scan_tfvars_file(content, file_path)
            else:
                return self._scan_tf_file(content, file_path)
                
        except Exception as e:
            logger.error(f"Error scanning Terraform file {file_path}: {e}")
            return []
    
    def _scan_tf_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a .tf file for resources and providers."""
        components = []
        
        # Extract resources
        resources = self._extract_resources(content)
        for resource in resources:
            component = InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name=resource["name"],
                service="terraform",
                subtype=resource["type"],
                configuration=resource["config"],
                source_file=str(file_path),
                line_number=resource.get("line_number"),
                classification=DependencyType.UNKNOWN
            )
            components.append(component)
        
        # Extract providers
        providers = self._extract_providers(content)
        for provider in providers:
            component = InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name=provider["name"],
                service="terraform",
                subtype="provider",
                configuration=provider["config"],
                source_file=str(file_path),
                line_number=provider.get("line_number"),
                classification=DependencyType.UNKNOWN
            )
            components.append(component)
        
        return components
    
    def _scan_tfvars_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a .tfvars file for variable definitions."""
        variables = self._extract_variables(content)
        
        if not variables:
            return []
        
        component = InfrastructureComponent(
            type=self.get_infrastructure_type(),
            name="variables",
            service="terraform",
            subtype="tfvars",
            configuration=variables,
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN
        )
        
        return [component]
    
    def _extract_resources(self, content: str) -> List[Dict[str, Any]]:
        """Extract resource definitions from Terraform content."""
        resources = []
        
        # Pattern to match resource blocks
        resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
        
        for match in re.finditer(resource_pattern, content):
            resource_type = match.group(1)
            resource_name = match.group(2)
            start_pos = match.end()
            
            # Find the matching closing brace
            brace_count = 1
            pos = start_pos
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            
            if brace_count == 0:
                # Extract the resource block content
                resource_content = content[start_pos:pos-1]
                config = self._parse_block_content(resource_content)
                
                resources.append({
                    "type": resource_type,
                    "name": resource_name,
                    "config": config,
                    "line_number": content[:match.start()].count('\n') + 1
                })
        
        return resources
    
    def _extract_providers(self, content: str) -> List[Dict[str, Any]]:
        """Extract provider definitions from Terraform content."""
        providers = []
        
        # Pattern to match provider blocks
        provider_pattern = r'provider\s+"([^"]+)"\s*\{'
        
        for match in re.finditer(provider_pattern, content):
            provider_name = match.group(1)
            start_pos = match.end()
            
            # Find the matching closing brace
            brace_count = 1
            pos = start_pos
            while pos < len(content) and brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            
            if brace_count == 0:
                # Extract the provider block content
                provider_content = content[start_pos:pos-1]
                config = self._parse_block_content(provider_content)
                
                providers.append({
                    "name": provider_name,
                    "config": config,
                    "line_number": content[:match.start()].count('\n') + 1
                })
        
        return providers
    
    def _extract_variables(self, content: str) -> Dict[str, Any]:
        """Extract variable assignments from tfvars content."""
        variables = {}
        
        # Pattern to match variable assignments
        # Supports: var = "value", var = 123, var = true, var = ["a", "b"]
        var_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([^#\n]+)'
        
        for match in re.finditer(var_pattern, content):
            var_name = match.group(1).strip()
            var_value = match.group(2).strip()
            
            # Parse the value
            parsed_value = self._parse_value(var_value)
            variables[var_name] = parsed_value
        
        return variables
    
    def _parse_block_content(self, content: str) -> Dict[str, Any]:
        """Parse the content of a Terraform block."""
        config = {}
        
        # Use a simpler approach - find key-value pairs and nested blocks
        # Split by lines but be careful about nested structures
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                i += 1
                continue
            
            # Check for assignments that have opening braces (multi-line blocks)
            assignment_block_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\{', line)
            if assignment_block_match:
                key = assignment_block_match.group(1)
                # Find the closing brace for this block
                brace_count = 1
                j = i + 1
                block_lines = []
                
                while j < len(lines) and brace_count > 0:
                    block_line = lines[j]
                    if '{' in block_line:
                        brace_count += block_line.count('{')
                    if '}' in block_line:
                        brace_count -= block_line.count('}')
                    
                    if brace_count > 0:
                        block_lines.append(block_line)
                    j += 1
                
                # Parse the block content recursively
                block_content = '\n'.join(block_lines)
                config[key] = self._parse_block_content(block_content)
                i = j
                continue
            
            # Check for nested blocks (e.g., tags { ... }) without assignment
            block_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\{', line)
            if block_match:
                block_name = block_match.group(1)
                # Find the closing brace for this block
                brace_count = 1
                j = i + 1
                block_lines = []
                
                while j < len(lines) and brace_count > 0:
                    block_line = lines[j]
                    if '{' in block_line:
                        brace_count += block_line.count('{')
                    if '}' in block_line:
                        brace_count -= block_line.count('}')
                    
                    if brace_count > 0:
                        block_lines.append(block_line)
                    j += 1
                
                # Parse the block content recursively
                block_content = '\n'.join(block_lines)
                config[block_name] = self._parse_block_content(block_content)
                i = j
                continue
            
            # Check for simple assignments
            assignment_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)', line)
            if assignment_match:
                key = assignment_match.group(1)
                value = assignment_match.group(2).strip()
                
                # Handle inline blocks like: tags = { Name = "value" }
                if value.startswith('{') and value.endswith('}'):
                    inline_content = value[1:-1].strip()
                    config[key] = self._parse_block_content(inline_content)
                else:
                    config[key] = self._parse_value(value)
            
            i += 1
        
        return config
    
    def _parse_value(self, value: str) -> Any:
        """Parse a Terraform value string."""
        value = value.strip()
        
        # Remove trailing commas
        if value.endswith(','):
            value = value[:-1].strip()
        
        # String values
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        
        # Boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Number values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # List values
        if value.startswith('[') and value.endswith(']'):
            list_content = value[1:-1].strip()
            if not list_content:
                return []
            
            # Simple list parsing (strings only for now)
            items = []
            for item in list_content.split(','):
                item = item.strip()
                if item.startswith('"') and item.endswith('"'):
                    items.append(item[1:-1])
                else:
                    items.append(item)
            return items
        
        # Return as string if no other pattern matches
        return value