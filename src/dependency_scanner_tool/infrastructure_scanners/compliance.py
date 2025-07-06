"""Compliance checker for GDPR, HIPAA, SOC2, and other frameworks."""

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
    ComplianceViolation,
    ComplianceFramework,
    SecuritySeverity
)
from dependency_scanner_tool.scanner import DependencyType


logger = logging.getLogger(__name__)


class ComplianceChecker(BaseInfrastructureScanner):
    """Scanner for compliance violations across multiple frameworks."""
    
    def __init__(self):
        """Initialize ComplianceChecker with framework rules."""
        self._frameworks = [
            ComplianceFramework.GDPR,
            ComplianceFramework.HIPAA,
            ComplianceFramework.SOC2,
            ComplianceFramework.PCI_DSS
        ]
        self._gdpr_rules = self._get_gdpr_rules()
        self._hipaa_rules = self._get_hipaa_rules()
        self._soc2_rules = self._get_soc2_rules()
        self._pci_dss_rules = self._get_pci_dss_rules()
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return supported file patterns for compliance checking."""
        return [
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
            "*.env",
            "*.config",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "requirements.txt",
            "package.json",
            "pom.xml",
            "build.gradle"
        ]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.SECURITY
    
    def get_supported_frameworks(self) -> List[ComplianceFramework]:
        """Return supported compliance frameworks."""
        return self._frameworks
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a file for compliance violations."""
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
            
            # Check compliance for each framework
            all_violations = []
            
            # GDPR compliance
            gdpr_violations = self._check_gdpr_compliance(content, str(file_path))
            all_violations.extend(gdpr_violations)
            
            # HIPAA compliance
            hipaa_violations = self._check_hipaa_compliance(content, str(file_path))
            all_violations.extend(hipaa_violations)
            
            # SOC2 compliance
            soc2_violations = self._check_soc2_compliance(content, str(file_path))
            all_violations.extend(soc2_violations)
            
            # PCI DSS compliance
            pci_violations = self._check_pci_dss_compliance(content, str(file_path))
            all_violations.extend(pci_violations)
            
            if not all_violations:
                return []
            
            # Group violations by framework
            framework_groups = {}
            for violation in all_violations:
                framework = violation["framework"]
                if framework not in framework_groups:
                    framework_groups[framework] = []
                framework_groups[framework].append(violation)
            
            components = []
            for framework, violations in framework_groups.items():
                component = InfrastructureComponent(
                    type=self.get_infrastructure_type(),
                    name=f"{file_path.stem}_{framework}",
                    service="compliance",
                    subtype=framework,
                    configuration={
                        "file_type": file_path.suffix,
                        "framework": framework,
                        "violations_count": len(violations)
                    },
                    source_file=str(file_path),
                    classification=DependencyType.RESTRICTED,
                    metadata={
                        "compliance_violations": violations,
                        "framework": framework
                    }
                )
                components.append(component)
            
            return components
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            return []
    
    def _check_gdpr_compliance(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Check GDPR compliance violations."""
        violations = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Check each GDPR rule
            for rule_id, rule_config in self._gdpr_rules.items():
                pattern = rule_config["pattern"]
                
                if re.search(pattern, line, re.IGNORECASE):
                    violation = {
                        "framework": ComplianceFramework.GDPR.value,
                        "rule_id": rule_id,
                        "title": rule_config["title"],
                        "description": rule_config["description"],
                        "severity": rule_config["severity"].value,
                        "source_file": file_path,
                        "line_number": line_num,
                        "remediation": rule_config.get("remediation", ""),
                        "references": rule_config.get("references", [])
                    }
                    violations.append(violation)
        
        return violations
    
    def _check_hipaa_compliance(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Check HIPAA compliance violations."""
        violations = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Check each HIPAA rule
            for rule_id, rule_config in self._hipaa_rules.items():
                pattern = rule_config["pattern"]
                
                if re.search(pattern, line, re.IGNORECASE):
                    violation = {
                        "framework": ComplianceFramework.HIPAA.value,
                        "rule_id": rule_id,
                        "title": rule_config["title"],
                        "description": rule_config["description"],
                        "severity": rule_config["severity"].value,
                        "source_file": file_path,
                        "line_number": line_num,
                        "remediation": rule_config.get("remediation", ""),
                        "references": rule_config.get("references", [])
                    }
                    violations.append(violation)
        
        return violations
    
    def _check_soc2_compliance(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Check SOC2 compliance violations."""
        violations = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Check each SOC2 rule
            for rule_id, rule_config in self._soc2_rules.items():
                pattern = rule_config["pattern"]
                
                if re.search(pattern, line, re.IGNORECASE):
                    violation = {
                        "framework": ComplianceFramework.SOC2.value,
                        "rule_id": rule_id,
                        "title": rule_config["title"],
                        "description": rule_config["description"],
                        "severity": rule_config["severity"].value,
                        "source_file": file_path,
                        "line_number": line_num,
                        "remediation": rule_config.get("remediation", ""),
                        "references": rule_config.get("references", [])
                    }
                    violations.append(violation)
        
        return violations
    
    def _check_pci_dss_compliance(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Check PCI DSS compliance violations."""
        violations = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Check each PCI DSS rule
            for rule_id, rule_config in self._pci_dss_rules.items():
                pattern = rule_config["pattern"]
                
                if re.search(pattern, line, re.IGNORECASE):
                    violation = {
                        "framework": ComplianceFramework.PCI_DSS.value,
                        "rule_id": rule_id,
                        "title": rule_config["title"],
                        "description": rule_config["description"],
                        "severity": rule_config["severity"].value,
                        "source_file": file_path,
                        "line_number": line_num,
                        "remediation": rule_config.get("remediation", ""),
                        "references": rule_config.get("references", [])
                    }
                    violations.append(violation)
        
        return violations
    
    def _get_gdpr_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get GDPR compliance rules."""
        return {
            "GDPR-001": {
                "title": "Personal Data Collection Without Consent",
                "description": "Collecting personal data without explicit consent mechanism",
                "pattern": r'(?:email|phone|ssn|name|address|dob|birth|personal|user_data|customer_data).*(?:collect|store|save|track)',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Implement explicit consent mechanism before collecting personal data",
                "references": ["GDPR Article 6", "GDPR Article 7"]
            },
            "GDPR-002": {
                "title": "Data Retention Without Policy",
                "description": "Storing personal data without defined retention policy",
                "pattern": r'(?:store|save).*(?:permanently|forever|indefinitely)',
                "severity": SecuritySeverity.MEDIUM,
                "remediation": "Implement data retention policy with automatic deletion",
                "references": ["GDPR Article 5(1)(e)"]
            },
            "GDPR-003": {
                "title": "Location Data Without Consent",
                "description": "Collecting location data without explicit consent",
                "pattern": r'(?:location|gps|coordinates|latitude|longitude|geolocation)',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Obtain explicit consent before collecting location data",
                "references": ["GDPR Article 6", "GDPR Article 7"]
            },
            "GDPR-004": {
                "title": "Unencrypted Personal Data Storage",
                "description": "Storing personal data without encryption",
                "pattern": r'(?:ssn|social.*security|passport|driver.*license|tax.*id).*(?:store|save|database)',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Encrypt personal data at rest and in transit",
                "references": ["GDPR Article 32"]
            },
            "GDPR-005": {
                "title": "Tracking Without Consent",
                "description": "Implementing tracking mechanisms without consent",
                "pattern": r'(?:tracking|analytics|cookie|pixel|fingerprint).*(?:id|identifier)',
                "severity": SecuritySeverity.MEDIUM,
                "remediation": "Implement cookie consent banner and tracking opt-in",
                "references": ["GDPR Article 6", "ePrivacy Directive"]
            }
        }
    
    def _get_hipaa_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get HIPAA compliance rules."""
        return {
            "HIPAA-001": {
                "title": "PHI Transmitted Without Encryption",
                "description": "Protected Health Information transmitted without encryption",
                "pattern": r'requests\.post.*http://',
                "severity": SecuritySeverity.CRITICAL,
                "remediation": "Encrypt all PHI transmissions using TLS 1.2 or higher",
                "references": ["45 CFR 164.312(e)(1)"]
            },
            "HIPAA-002": {
                "title": "PHI in Log Files",
                "description": "Protected Health Information found in log statements",
                "pattern": r'(?:logger|log|print|console).*(?:patient|medical|ssn|medical_record|diagnosis|prescription)',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove PHI from log files or implement secure logging",
                "references": ["45 CFR 164.308(a)(1)"]
            },
            "HIPAA-003": {
                "title": "Unencrypted PHI Storage",
                "description": "Protected Health Information stored without encryption",
                "pattern": r'(?:ssn|social_security|medical_record|patient_id|diagnosis|prescription).*(?:store|save|file|database)',
                "severity": SecuritySeverity.CRITICAL,
                "remediation": "Encrypt PHI at rest using NIST-approved encryption",
                "references": ["45 CFR 164.312(a)(2)(iv)"]
            },
            "HIPAA-004": {
                "title": "PHI Access Without Authorization",
                "description": "Accessing PHI without proper authorization controls",
                "pattern": r'(?:open|read|access).*(?:patient_data|medical_record|phi).*(?:txt|csv|json|xml)',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Implement role-based access controls for PHI",
                "references": ["45 CFR 164.308(a)(4)"]
            },
            "HIPAA-005": {
                "title": "Unsecured PHI Transmission",
                "description": "Transmitting PHI over unsecured channels",
                "pattern": r'http://.*(?:patient|medical|health|phi)',
                "severity": SecuritySeverity.CRITICAL,
                "remediation": "Use HTTPS for all PHI transmissions",
                "references": ["45 CFR 164.312(e)(1)"]
            }
        }
    
    def _get_soc2_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get SOC2 compliance rules."""
        return {
            "SOC2-001": {
                "title": "Database Exposed to Public",
                "description": "Database port exposed to public internet",
                "pattern": r'(?:5432|3306|1433|27017|6379).*(?:0\.0\.0\.0|::)|publicly_accessible.*true|acl.*public-read|cidr_blocks.*\["0\.0\.0\.0/0"\]',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Restrict database access to private networks only",
                "references": ["SOC2 CC6.1"]
            },
            "SOC2-002": {
                "title": "Weak Password Policy",
                "description": "Weak password configuration detected",
                "pattern": r'(?:password|passwd).*(?:weak|simple|123|password|admin)',
                "severity": SecuritySeverity.MEDIUM,
                "remediation": "Implement strong password policy with complexity requirements",
                "references": ["SOC2 CC6.1"]
            },
            "SOC2-003": {
                "title": "No HTTPS Enforcement",
                "description": "HTTP used instead of HTTPS for web services",
                "pattern": r'(?:listen|port|expose).*:80[^0-9]',
                "severity": SecuritySeverity.MEDIUM,
                "remediation": "Enforce HTTPS for all web communications",
                "references": ["SOC2 CC6.1"]
            },
            "SOC2-004": {
                "title": "Debug Mode in Production",
                "description": "Debug mode enabled in production environment",
                "pattern": r'(?:debug|DEBUG).*(?:true|True|1|yes|on)',
                "severity": SecuritySeverity.LOW,
                "remediation": "Disable debug mode in production environments",
                "references": ["SOC2 CC6.1"]
            },
            "SOC2-005": {
                "title": "No Authentication Required",
                "description": "Service configured without authentication",
                "pattern": r'(?:redis|memcached|elasticsearch).*(?:requirepass|auth).*(?:""|\'\')',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Enable authentication for all services",
                "references": ["SOC2 CC6.1"]
            },
            "SOC2-006": {
                "title": "Data Not Encrypted at Rest",
                "description": "Data storage without encryption",
                "pattern": r'(?:storage_encrypted|encrypt).*(?:false|False|0|no|off)',
                "severity": SecuritySeverity.MEDIUM,
                "remediation": "Enable encryption for data at rest",
                "references": ["SOC2 CC6.1"]
            },
            "SOC2-007": {
                "title": "No Backup Retention Policy",
                "description": "Database configured without backup retention",
                "pattern": r'backup_retention_period.*0',
                "severity": SecuritySeverity.MEDIUM,
                "remediation": "Configure appropriate backup retention period",
                "references": ["SOC2 CC3.1"]
            }
        }
    
    def _get_pci_dss_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get PCI DSS compliance rules."""
        return {
            "PCI-001": {
                "title": "Credit Card Number Storage",
                "description": "Storing full credit card numbers (PAN) is prohibited",
                "pattern": r'"4[0-9]{12}(?:[0-9]{3})?"|"5[1-5][0-9]{14}"|"3[47][0-9]{13}"|"3[0-9]{13}"|"6(?:011|5[0-9]{2})[0-9]{12}"',
                "severity": SecuritySeverity.CRITICAL,
                "remediation": "Tokenize or encrypt credit card numbers, never store full PAN",
                "references": ["PCI DSS 3.4"]
            },
            "PCI-002": {
                "title": "CVV Storage",
                "description": "Storing CVV codes is prohibited",
                "pattern": r'(?:cvv|cvv2|cvc|cvc2|cid).*(?:store|save|database|log)|"cvv".*"[0-9]{3,4}"',
                "severity": SecuritySeverity.CRITICAL,
                "remediation": "Never store CVV codes after authorization",
                "references": ["PCI DSS 3.2"]
            },
            "PCI-003": {
                "title": "Cardholder Data in Logs",
                "description": "Cardholder data found in log files",
                "pattern": r'(?:logger|log|print|console).*(?:card_number|pan|cvv|expiry|cardholder)',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Remove cardholder data from logs and implement secure logging",
                "references": ["PCI DSS 10.5"]
            },
            "PCI-004": {
                "title": "Unencrypted Cardholder Data Transmission",
                "description": "Transmitting cardholder data without encryption",
                "pattern": r'http://.*(?:card_number|pan|payment|billing)|requests\.post.*http://.*payment',
                "severity": SecuritySeverity.CRITICAL,
                "remediation": "Use TLS 1.2 or higher for all cardholder data transmissions",
                "references": ["PCI DSS 4.1"]
            },
            "PCI-005": {
                "title": "Weak Encryption for Cardholder Data",
                "description": "Using weak encryption for cardholder data",
                "pattern": r'(?:base64|md5|sha1).*(?:card_number|pan|cardholder)|base64\.b64encode.*card',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Use strong encryption algorithms like AES-256",
                "references": ["PCI DSS 3.4"]
            },
            "PCI-006": {
                "title": "Default Passwords on Payment Systems",
                "description": "Default passwords used on payment processing systems",
                "pattern": r'(?:payment|pos|terminal).*(?:password|passwd).*(?:admin|default|123|password)',
                "severity": SecuritySeverity.HIGH,
                "remediation": "Change all default passwords and use strong authentication",
                "references": ["PCI DSS 2.1"]
            }
        }