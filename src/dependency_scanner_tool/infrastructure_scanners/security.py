"""Security scanner for detecting secrets, security tools, and vulnerabilities."""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

import yaml
import json

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent,
    SecurityFinding,
    SecurityFindingType,
    SecuritySeverity
)
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class SecurityScanner(BaseInfrastructureScanner):
    """Scanner for security-related findings and tools."""
    
    def __init__(self):
        """Initialize SecurityScanner with patterns and configurations."""
        self._secret_patterns = self._get_secret_patterns()
        self._security_tools = self._get_security_tools()
        self._insecure_patterns = self._get_insecure_patterns()
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return supported file patterns for security scanning."""
        return [
            "*.env",
            "*.config",
            "*.yml",
            "*.yaml",
            "*.json",
            "*.tf",
            "*.tfvars",
            "*.py",
            "*.js",
            "*.ts",
            "*.java",
            "*.xml",
            "*.properties",
            "*.key",
            "*.pem",
            "*.crt",
            "*.cert",
            "*.p12",
            "*.jks",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "requirements.txt",
            "package.json",
            "pom.xml",
            "build.gradle",
            "Gemfile",
            "Pipfile",
            "poetry.lock",
            "composer.json"
        ]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.SECURITY
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a file for security findings."""
        try:
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return []
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Skip binary files
                logger.debug(f"Skipping binary file: {file_path}")
                return []
            
            if not content.strip():
                return []
            
            # Perform security scanning
            security_findings = self._scan_for_secrets(content, file_path)
            security_tools = self._scan_for_security_tools(content, file_path)
            insecure_configs = self._scan_for_insecure_configs(content, file_path)
            
            # Combine all findings
            all_findings = security_findings + insecure_configs
            
            if not all_findings and not security_tools:
                return []
            
            # Create security component
            component = InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name=file_path.stem,
                service="security",
                subtype="secrets" if all_findings else "tools",
                configuration={
                    "file_type": file_path.suffix,
                    "findings_count": len(all_findings),
                    "tools_count": len(security_tools)
                },
                source_file=str(file_path),
                classification=DependencyType.RESTRICTED if all_findings else DependencyType.UNKNOWN,
                metadata={
                    "security_findings": [self._finding_to_dict(f) for f in all_findings],
                    "security_tools": security_tools
                }
            )
            
            return [component]
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            return []
    
    def _scan_for_secrets(self, content: str, file_path: Path) -> List[SecurityFinding]:
        """Scan content for secrets and sensitive information."""
        findings = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Check each secret pattern
            for pattern_name, pattern_config in self._secret_patterns.items():
                pattern = pattern_config["pattern"]
                finding_type = pattern_config["type"]
                severity = pattern_config["severity"]
                
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Skip if it's a placeholder or example
                    matched_text = match.group(0)
                    if self._is_placeholder(matched_text):
                        logger.debug(f"Skipping placeholder: {matched_text}")
                        continue
                    
                    finding = SecurityFinding(
                        finding_type=finding_type,
                        severity=severity,
                        title=f"{pattern_name} detected",
                        description=f"Potential {pattern_name.lower()} found in file",
                        source_file=str(file_path),
                        line_number=line_num,
                        matched_text=matched_text,
                        pattern=pattern_name,
                        remediation=pattern_config.get("remediation", "Remove or secure this sensitive information"),
                        confidence=pattern_config.get("confidence", 0.8)
                    )
                    findings.append(finding)
        
        return findings
    
    def _scan_for_security_tools(self, content: str, file_path: Path) -> List[str]:
        """Scan content for security tools and configurations."""
        detected_tools = []
        
        # Check for security tools in different file types
        if file_path.suffix.lower() in ['.yml', '.yaml']:
            detected_tools.extend(self._scan_yaml_for_security_tools(content))
        elif file_path.suffix.lower() == '.json':
            detected_tools.extend(self._scan_json_for_security_tools(content))
        elif file_path.suffix.lower() == '.tf':
            detected_tools.extend(self._scan_terraform_for_security_tools(content))
        
        # Check for security tool mentions in any file
        for tool_name, tool_patterns in self._security_tools.items():
            for pattern in tool_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected_tools.append(tool_name)
                    break
        
        return list(set(detected_tools))  # Remove duplicates
    
    def _scan_for_insecure_configs(self, content: str, file_path: Path) -> List[SecurityFinding]:
        """Scan content for insecure configurations."""
        findings = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Check each insecure pattern
            for pattern_name, pattern_config in self._insecure_patterns.items():
                pattern = pattern_config["pattern"]
                
                if re.search(pattern, line, re.IGNORECASE):
                    finding = SecurityFinding(
                        finding_type=SecurityFindingType.INSECURE_CONFIG,
                        severity=pattern_config["severity"],
                        title=f"Insecure configuration: {pattern_name}",
                        description=pattern_config["description"],
                        source_file=str(file_path),
                        line_number=line_num,
                        matched_text=line_stripped,
                        pattern=pattern_name,
                        remediation=pattern_config.get("remediation", "Review and secure this configuration"),
                        confidence=pattern_config.get("confidence", 0.7)
                    )
                    findings.append(finding)
        
        return findings
    
    def _scan_yaml_for_security_tools(self, content: str) -> List[str]:
        """Scan YAML content for security tools."""
        tools = []
        
        try:
            yaml_data = yaml.safe_load(content)
            if not yaml_data:
                return tools
            
            # Check Docker Compose services
            if isinstance(yaml_data, dict) and "services" in yaml_data:
                services = yaml_data["services"]
                for service_name, service_config in services.items():
                    if isinstance(service_config, dict):
                        # Check service name
                        if service_name.lower() in self._security_tools:
                            tools.append(service_name.lower())
                        
                        # Check image name
                        image = service_config.get("image", "")
                        if isinstance(image, str):
                            for tool_name in self._security_tools:
                                if tool_name in image.lower():
                                    tools.append(tool_name)
            
            # Check Kubernetes resources
            if isinstance(yaml_data, dict) and "kind" in yaml_data:
                kind = yaml_data.get("kind", "").lower()
                if "security" in kind or "policy" in kind:
                    tools.append("kubernetes-security")
        
        except yaml.YAMLError:
            pass
        
        return tools
    
    def _scan_json_for_security_tools(self, content: str) -> List[str]:
        """Scan JSON content for security tools."""
        tools = []
        
        try:
            json_data = json.loads(content)
            if not isinstance(json_data, dict):
                return tools
            
            # Check package.json dependencies
            if "dependencies" in json_data or "devDependencies" in json_data:
                all_deps = {}
                all_deps.update(json_data.get("dependencies", {}))
                all_deps.update(json_data.get("devDependencies", {}))
                
                for dep_name in all_deps:
                    for tool_name in self._security_tools:
                        if tool_name in dep_name.lower():
                            tools.append(tool_name)
        
        except json.JSONDecodeError:
            pass
        
        return tools
    
    def _scan_terraform_for_security_tools(self, content: str) -> List[str]:
        """Scan Terraform content for security tools."""
        tools = []
        
        # Check for security-related resources
        security_resources = [
            "aws_security_group",
            "aws_iam_role",
            "aws_iam_policy",
            "aws_kms_key",
            "azure_key_vault",
            "google_kms_crypto_key",
            "vault_",
            "consul_"
        ]
        
        for resource_type in security_resources:
            if resource_type in content:
                if resource_type.startswith("vault_"):
                    tools.append("vault")
                elif resource_type.startswith("consul_"):
                    tools.append("consul")
                elif "security_group" in resource_type:
                    tools.append("security-groups")
                elif "iam" in resource_type:
                    tools.append("iam")
                elif "kms" in resource_type:
                    tools.append("kms")
                elif "key_vault" in resource_type:
                    tools.append("key-vault")
        
        return tools
    
    def _is_placeholder(self, text: str) -> bool:
        """Check if text appears to be a placeholder or example."""
        # For AWS keys and similar, don't filter based on "example" if it looks like a real key format
        if re.match(r'AKIA[0-9A-Z]{16}', text):
            return False
        if re.match(r'ghp_[0-9A-Za-z]{36}', text):
            return False
        if re.match(r'[A-Za-z0-9/+=]{40}', text):
            return False
            
        placeholder_patterns = [
            r'xxx+',
            r'^example$',
            r'^placeholder$',
            r'your[_-]?key',
            r'your[_-]?token',
            r'your[_-]?secret',
            r'<[^>]+>',
            r'\{[^}]+\}',
            r'^123+$',
            r'^abc+$',
            r'test[_-]?key',
            r'^dummy$',
            r'^sample$',
            r'changeme',
            r'replace'
        ]
        
        text_lower = text.lower()
        # Don't filter out real-looking values unless they're clearly placeholders
        for pattern in placeholder_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Special case: if it's too short to be real, it might be a placeholder
        if len(text) < 6:
            return True
            
        return False
    
    def _finding_to_dict(self, finding: SecurityFinding) -> Dict[str, Any]:
        """Convert SecurityFinding to dictionary for JSON serialization."""
        return {
            "finding_type": finding.finding_type.value,
            "severity": finding.severity.value,
            "title": finding.title,
            "description": finding.description,
            "source_file": finding.source_file,
            "line_number": finding.line_number,
            "column_number": finding.column_number,
            "matched_text": finding.matched_text,
            "pattern": finding.pattern,
            "remediation": finding.remediation,
            "cve_id": finding.cve_id,
            "confidence": finding.confidence,
            "metadata": finding.metadata
        }
    
    def _get_secret_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get patterns for detecting secrets."""
        return {
            "AWS Access Key": {
                "pattern": r'(?:aws_access_key_id["\']?\s*[:=]\s*["\']?|AKIA)[0-9A-Z]{16,20}',
                "type": SecurityFindingType.API_KEY,
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove AWS access key and use IAM roles or AWS credentials file"
            },
            "AWS Secret Key": {
                "pattern": r'aws_secret_access_key["\']?\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})["\']?',
                "type": SecurityFindingType.API_KEY,
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove AWS secret key and use IAM roles or AWS credentials file"
            },
            "GitHub Token": {
                "pattern": r'ghp_[0-9A-Za-z]{36}',
                "type": SecurityFindingType.API_KEY,
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove GitHub token and use GitHub Actions secrets"
            },
            "Generic API Key": {
                "pattern": r'(?:api[_-]?key|apikey|access[_-]?key|secret[_-]?key|default)\s*[:=]\s*["\']?([A-Za-z0-9\-_]{10,})["\']?',
                "type": SecurityFindingType.API_KEY,
                "severity": SecuritySeverity.MEDIUM,
                "remediation": "Remove hardcoded API key and use environment variables or secret management"
            },
            "Hardcoded Password": {
                "pattern": r'(?:password|passwd|pwd)\s*[:=]\s*["\']?([A-Za-z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>?]{6,})["\']?',
                "type": SecurityFindingType.HARDCODED_PASSWORD,
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove hardcoded password and use environment variables or secret management"
            },
            "Private Key": {
                "pattern": r'-----BEGIN (?:RSA )?PRIVATE KEY-----',
                "type": SecurityFindingType.PRIVATE_KEY,
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove private key from source code and use secure key management"
            },
            "Certificate": {
                "pattern": r'-----BEGIN CERTIFICATE-----',
                "type": SecurityFindingType.CERTIFICATE,
                "severity": SecuritySeverity.MEDIUM,
                "remediation": "Consider if certificate should be in source code or use secure storage"
            },
            "JWT Token": {
                "pattern": r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
                "type": SecurityFindingType.API_KEY,
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove JWT token and use secure token management"
            },
            "Database URL with Password": {
                "pattern": r'(?:postgresql|mysql|mongodb)://[^:]+:([^@]+)@[^/]+',
                "type": SecurityFindingType.HARDCODED_PASSWORD,
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove password from database URL and use environment variables"
            },
            "Generic Secret": {
                "pattern": r'(?:secret|token|key)\s*[:=]\s*["\']?([A-Za-z0-9\-_]{32,})["\']?',
                "type": SecurityFindingType.SECRET,
                "severity": SecuritySeverity.MEDIUM,
                "confidence": 0.6,
                "remediation": "Review if this is a secret and use secure storage if so"
            }
        }
    
    def _get_security_tools(self) -> Dict[str, List[str]]:
        """Get patterns for detecting security tools."""
        return {
            "vault": [r'vault:', r'hashicorp/vault', r'vault_'],
            "consul": [r'consul:', r'hashicorp/consul', r'consul_'],
            "cert-manager": [r'cert-manager', r'jetstack/cert-manager'],
            "external-secrets": [r'external-secrets', r'external-secrets-operator'],
            "sealed-secrets": [r'sealed-secrets', r'bitnami-labs/sealed-secrets'],
            "oauth2-proxy": [r'oauth2-proxy', r'oauth2_proxy'],
            "keycloak": [r'keycloak', r'jboss/keycloak'],
            "trivy": [r'trivy', r'aquasec/trivy'],
            "clair": [r'clair', r'coreos/clair'],
            "falco": [r'falco', r'sysdig/falco'],
            "istio": [r'istio', r'istio/'],
            "linkerd": [r'linkerd', r'linkerd/'],
            "envoy": [r'envoy', r'envoyproxy/envoy'],
            "traefik": [r'traefik', r'traefik:'],
            "nginx-ingress": [r'nginx-ingress', r'ingress-nginx'],
            "kustomize": [r'kustomize', r'kustomization'],
            "helm": [r'helm', r'chart\.yaml'],
            "terraform": [r'terraform', r'\.tf$'],
            "ansible": [r'ansible', r'playbook\.yml'],
            "docker": [r'dockerfile', r'docker-compose']
        }
    
    def _get_insecure_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get patterns for detecting insecure configurations."""
        return {
            "HTTP URL": {
                "pattern": r'http://[^\s"\'>]+',
                "severity": SecuritySeverity.MEDIUM,
                "description": "HTTP URL detected, should use HTTPS for security",
                "remediation": "Replace HTTP with HTTPS"
            },
            "Insecure Database Connection": {
                "pattern": r'(?:postgresql|mysql|mongodb)://[^?]*(?:\?.*)?$',
                "severity": SecuritySeverity.MEDIUM,
                "description": "Database connection without SSL parameters",
                "remediation": "Add SSL/TLS parameters to database connection string"
            },
            "Debug Mode Enabled": {
                "pattern": r'(?:debug|DEBUG)\s*[:=]\s*(?:true|True|1|yes|Yes|on|On)',
                "severity": SecuritySeverity.LOW,
                "description": "Debug mode enabled, should be disabled in production",
                "remediation": "Disable debug mode in production environments"
            },
            "Weak Password": {
                "pattern": r'(?:password|passwd|pwd)\s*[:=]\s*["\']?(?:123|password|admin|root|test)["\']?',
                "severity": SecuritySeverity.HIGH,
                "description": "Weak or default password detected",
                "remediation": "Use strong, unique passwords and store securely"
            },
            "Public Port Binding": {
                "pattern": r'(?:0\.0\.0\.0|::):\d+',
                "severity": SecuritySeverity.MEDIUM,
                "description": "Service bound to all interfaces, may be exposed publicly",
                "remediation": "Bind to specific interfaces or use firewall rules"
            },
            "Insecure Docker Configuration": {
                "pattern": r'--privileged|--cap-add=SYS_ADMIN|--cap-add=ALL',
                "severity": SecuritySeverity.HIGH,
                "description": "Insecure Docker container configuration",
                "remediation": "Avoid privileged containers and excessive capabilities"
            }
        }