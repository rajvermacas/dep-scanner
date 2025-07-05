"""Cloud SDK detector for identifying cloud provider SDK usage."""

import json
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Set

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent,
    DependencyType
)


logger = logging.getLogger(__name__)


class CloudSDKDetector(BaseInfrastructureScanner):
    """Detector for cloud SDK usage in source code and dependency files."""
    
    def __init__(self):
        """Initialize the Cloud SDK detector."""
        self._aws_patterns = self._get_aws_patterns()
        self._azure_patterns = self._get_azure_patterns()
        self._gcp_patterns = self._get_gcp_patterns()
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return list of file patterns this scanner can handle."""
        return [
            "*.py",
            "*.java",
            "*.js",
            "*.ts",
            "*.go",
            "*.rb",
            "*.php",
            "*.cs",
            "requirements.txt",
            "package.json",
            "pom.xml",
            "build.gradle",
            "Gemfile",
            "composer.json",
            "go.mod"
        ]
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.CLOUD
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file for cloud SDK usage."""
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            return self._analyze_file_content(content, file_path)
        except UnicodeDecodeError:
            logger.warning(f"Unable to decode file {file_path}, skipping")
            return []
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []
    
    def _analyze_file_content(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze file content for cloud SDK usage."""
        filename = file_path.name.lower()
        
        # Route to appropriate analyzer based on file type
        if filename.endswith(('.py')):
            return self._analyze_python_file(content, file_path)
        elif filename.endswith(('.java')):
            return self._analyze_java_file(content, file_path)
        elif filename.endswith(('.js', '.ts')):
            return self._analyze_javascript_file(content, file_path)
        elif filename == 'requirements.txt':
            return self._analyze_requirements_txt(content, file_path)
        elif filename == 'package.json':
            return self._analyze_package_json(content, file_path)
        elif filename == 'pom.xml':
            return self._analyze_pom_xml(content, file_path)
        elif filename.endswith(('.go')):
            return self._analyze_go_file(content, file_path)
        elif filename.endswith(('.rb')):
            return self._analyze_ruby_file(content, file_path)
        elif filename.endswith(('.php')):
            return self._analyze_php_file(content, file_path)
        elif filename.endswith(('.cs')):
            return self._analyze_csharp_file(content, file_path)
        elif filename == 'build.gradle':
            return self._analyze_gradle_file(content, file_path)
        elif filename == 'gemfile':
            return self._analyze_gemfile(content, file_path)
        elif filename == 'composer.json':
            return self._analyze_composer_json(content, file_path)
        elif filename == 'go.mod':
            return self._analyze_go_mod(content, file_path)
        
        return []
    
    def _analyze_python_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze Python file for cloud SDK imports."""
        components = []
        found_components = set()  # To avoid duplicates
        
        # Find import statements
        import_lines = []
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                import_lines.append(stripped)
        
        # Check for AWS SDK
        for line in import_lines:
            if self._matches_aws_python_import(line):
                # Extract the specific package name
                if line.startswith('import '):
                    package_name = line.replace('import ', '').split()[0]
                elif line.startswith('from '):
                    package_name = line.split()[1]
                else:
                    package_name = line
                
                if package_name not in found_components:
                    component = self._create_aws_component(package_name, file_path)
                    if component:
                        components.append(component)
                        found_components.add(package_name)
        
        # Check for Azure SDK
        for line in import_lines:
            if self._matches_azure_python_import(line):
                # Extract the specific package name
                if line.startswith('import '):
                    package_name = line.replace('import ', '').split()[0]
                elif line.startswith('from '):
                    package_name = line.split()[1]
                else:
                    package_name = line
                
                if package_name not in found_components:
                    component = self._create_azure_component(package_name, file_path)
                    if component:
                        components.append(component)
                        found_components.add(package_name)
        
        # Check for GCP SDK
        for line in import_lines:
            if self._matches_gcp_python_import(line):
                # Extract the specific package name
                if line.startswith('import '):
                    package_name = line.replace('import ', '').split()[0]
                elif line.startswith('from '):
                    package_name = line.split()[1]
                else:
                    package_name = line
                
                if package_name not in found_components:
                    component = self._create_gcp_component(package_name, file_path)
                    if component:
                        components.append(component)
                        found_components.add(package_name)
        
        return components
    
    def _analyze_java_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze Java file for cloud SDK imports."""
        components = []
        
        # Find import statements
        import_lines = []
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('import '):
                import_lines.append(stripped)
        
        # Check for AWS SDK
        for line in import_lines:
            if self._matches_aws_java_import(line):
                component = self._create_aws_component(line, file_path)
                if component:
                    components.append(component)
        
        # Check for Azure SDK
        for line in import_lines:
            if self._matches_azure_java_import(line):
                component = self._create_azure_component(line, file_path)
                if component:
                    components.append(component)
        
        # Check for GCP SDK
        for line in import_lines:
            if self._matches_gcp_java_import(line):
                component = self._create_gcp_component(line, file_path)
                if component:
                    components.append(component)
        
        return components
    
    def _analyze_javascript_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze JavaScript/TypeScript file for cloud SDK imports."""
        components = []
        
        # Find import/require statements - using simpler patterns
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Check for require statements
            require_match = re.search(r'require\([\'"]([^\'"]*)[\'"]', line)
            if require_match:
                module_name = require_match.group(1)
                if self._matches_aws_javascript_import(module_name):
                    component = self._create_aws_component(module_name, file_path)
                    if component:
                        components.append(component)
                elif self._matches_azure_javascript_import(module_name):
                    component = self._create_azure_component(module_name, file_path)
                    if component:
                        components.append(component)
                elif self._matches_gcp_javascript_import(module_name):
                    component = self._create_gcp_component(module_name, file_path)
                    if component:
                        components.append(component)
            
            # Check for import statements
            import_match = re.search(r'import.*from\s+[\'"]([^\'"]*)[\'"]', line)
            if import_match:
                module_name = import_match.group(1)
                if self._matches_aws_javascript_import(module_name):
                    component = self._create_aws_component(module_name, file_path)
                    if component:
                        components.append(component)
                elif self._matches_azure_javascript_import(module_name):
                    component = self._create_azure_component(module_name, file_path)
                    if component:
                        components.append(component)
                elif self._matches_gcp_javascript_import(module_name):
                    component = self._create_gcp_component(module_name, file_path)
                    if component:
                        components.append(component)
        
        return components
    
    def _analyze_requirements_txt(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze requirements.txt for cloud SDK dependencies."""
        components = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Extract package name (before == or >=)
            package_name = re.split(r'[>=<!=]', line)[0].strip()
            
            if package_name in self._aws_patterns['dependencies']:
                component = self._create_aws_component(package_name, file_path)
                if component:
                    components.append(component)
            elif package_name in self._azure_patterns['dependencies']:
                component = self._create_azure_component(package_name, file_path)
                if component:
                    components.append(component)
            elif package_name in self._gcp_patterns['dependencies']:
                component = self._create_gcp_component(package_name, file_path)
                if component:
                    components.append(component)
        
        return components
    
    def _analyze_package_json(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze package.json for cloud SDK dependencies."""
        components = []
        
        try:
            package_data = json.loads(content)
            dependencies = {}
            dependencies.update(package_data.get('dependencies', {}))
            dependencies.update(package_data.get('devDependencies', {}))
            
            for package_name in dependencies.keys():
                if package_name in self._aws_patterns['dependencies']:
                    component = self._create_aws_component(package_name, file_path)
                    if component:
                        components.append(component)
                elif package_name in self._azure_patterns['dependencies']:
                    component = self._create_azure_component(package_name, file_path)
                    if component:
                        components.append(component)
                elif package_name in self._gcp_patterns['dependencies']:
                    component = self._create_gcp_component(package_name, file_path)
                    if component:
                        components.append(component)
        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {file_path}")
        
        return components
    
    def _analyze_pom_xml(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze pom.xml for cloud SDK dependencies."""
        components = []
        
        try:
            # Strip leading/trailing whitespace to avoid XML parsing issues
            content = content.strip()
            root = ET.fromstring(content)
            
            # Try with namespace first
            namespaces = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            dependencies = root.findall('.//maven:dependency', namespaces)
            
            # If no dependencies found with namespace, try without
            if not dependencies:
                dependencies = root.findall('.//dependency')
            
            # Find dependencies
            for dep in dependencies:
                group_id = dep.find('groupId') or dep.find('.//{http://maven.apache.org/POM/4.0.0}groupId')
                artifact_id = dep.find('artifactId') or dep.find('.//{http://maven.apache.org/POM/4.0.0}artifactId')
                
                if group_id is not None and artifact_id is not None:
                    dep_name = f"{group_id.text}:{artifact_id.text}"
                    
                    if self._matches_aws_maven_dependency(dep_name):
                        component = self._create_aws_component(dep_name, file_path)
                        if component:
                            components.append(component)
                    elif self._matches_azure_maven_dependency(dep_name):
                        component = self._create_azure_component(dep_name, file_path)
                        if component:
                            components.append(component)
                    elif self._matches_gcp_maven_dependency(dep_name):
                        component = self._create_gcp_component(dep_name, file_path)
                        if component:
                            components.append(component)
        
        except ET.ParseError as e:
            logger.warning(f"Invalid XML in {file_path}: {e}")
        
        return components
    
    def _analyze_go_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze Go file for cloud SDK imports."""
        # Simplified implementation
        return []
    
    def _analyze_ruby_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze Ruby file for cloud SDK imports."""
        # Simplified implementation
        return []
    
    def _analyze_php_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze PHP file for cloud SDK imports."""
        # Simplified implementation
        return []
    
    def _analyze_csharp_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze C# file for cloud SDK imports."""
        # Simplified implementation
        return []
    
    def _analyze_gradle_file(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze build.gradle for cloud SDK dependencies."""
        # Simplified implementation
        return []
    
    def _analyze_gemfile(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze Gemfile for cloud SDK dependencies."""
        # Simplified implementation
        return []
    
    def _analyze_composer_json(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze composer.json for cloud SDK dependencies."""
        # Simplified implementation
        return []
    
    def _analyze_go_mod(self, content: str, file_path: Path) -> List[InfrastructureComponent]:
        """Analyze go.mod for cloud SDK dependencies."""
        # Simplified implementation
        return []
    
    def _get_aws_patterns(self) -> Dict[str, Set[str]]:
        """Get AWS SDK patterns for different languages."""
        return {
            'python_imports': {
                'boto3', 'botocore', 'aioboto3', 'aws-sam-cli'
            },
            'java_imports': {
                'software.amazon.awssdk', 'com.amazonaws'
            },
            'javascript_imports': {
                'aws-sdk', '@aws-sdk'
            },
            'dependencies': {
                'boto3', 'botocore', 'aioboto3', 'aws-sam-cli',
                'aws-sdk', '@aws-sdk/client-s3', '@aws-sdk/client-dynamodb',
                '@aws-sdk/client-ec2', '@aws-sdk/client-lambda'
            }
        }
    
    def _get_azure_patterns(self) -> Dict[str, Set[str]]:
        """Get Azure SDK patterns for different languages."""
        return {
            'python_imports': {
                'azure', 'azure-storage', 'azure-identity', 'azure-functions'
            },
            'java_imports': {
                'com.azure', 'com.microsoft.azure'
            },
            'javascript_imports': {
                '@azure', 'azure-storage', 'azure-functions-core-tools'
            },
            'dependencies': {
                'azure-storage-blob', 'azure-identity', 'azure-functions',
                'azure-keyvault-secrets', 'azure-servicebus',
                '@azure/storage-blob', '@azure/identity', '@azure/functions'
            }
        }
    
    def _get_gcp_patterns(self) -> Dict[str, Set[str]]:
        """Get GCP SDK patterns for different languages."""
        return {
            'python_imports': {
                'google-cloud', 'google.cloud', 'google.auth', 'google-api-python-client', 'google'
            },
            'java_imports': {
                'com.google.cloud', 'com.google.api'
            },
            'javascript_imports': {
                '@google-cloud', 'google-cloud'
            },
            'dependencies': {
                'google-cloud-storage', 'google-cloud-bigquery', 'google-cloud-pubsub',
                'google-auth', 'google-api-python-client',
                '@google-cloud/storage', '@google-cloud/bigquery', '@google-cloud/pubsub'
            }
        }
    
    def _matches_aws_python_import(self, line: str) -> bool:
        """Check if line matches AWS Python import pattern."""
        return any(pattern in line for pattern in self._aws_patterns['python_imports'])
    
    def _matches_azure_python_import(self, line: str) -> bool:
        """Check if line matches Azure Python import pattern."""
        return any(pattern in line for pattern in self._azure_patterns['python_imports'])
    
    def _matches_gcp_python_import(self, line: str) -> bool:
        """Check if line matches GCP Python import pattern."""
        return any(pattern in line for pattern in self._gcp_patterns['python_imports'])
    
    def _matches_aws_java_import(self, line: str) -> bool:
        """Check if line matches AWS Java import pattern."""
        return any(pattern in line for pattern in self._aws_patterns['java_imports'])
    
    def _matches_azure_java_import(self, line: str) -> bool:
        """Check if line matches Azure Java import pattern."""
        return any(pattern in line for pattern in self._azure_patterns['java_imports'])
    
    def _matches_gcp_java_import(self, line: str) -> bool:
        """Check if line matches GCP Java import pattern."""
        return any(pattern in line for pattern in self._gcp_patterns['java_imports'])
    
    def _matches_aws_javascript_import(self, line: str) -> bool:
        """Check if line matches AWS JavaScript import pattern."""
        return any(pattern in line for pattern in self._aws_patterns['javascript_imports'])
    
    def _matches_azure_javascript_import(self, line: str) -> bool:
        """Check if line matches Azure JavaScript import pattern."""
        return any(pattern in line for pattern in self._azure_patterns['javascript_imports'])
    
    def _matches_gcp_javascript_import(self, line: str) -> bool:
        """Check if line matches GCP JavaScript import pattern."""
        return any(pattern in line for pattern in self._gcp_patterns['javascript_imports'])
    
    def _matches_aws_maven_dependency(self, dep_name: str) -> bool:
        """Check if Maven dependency matches AWS pattern."""
        return 'amazonaws' in dep_name or 'software.amazon.awssdk' in dep_name
    
    def _matches_azure_maven_dependency(self, dep_name: str) -> bool:
        """Check if Maven dependency matches Azure pattern."""
        return 'com.azure' in dep_name or 'com.microsoft.azure' in dep_name
    
    def _matches_gcp_maven_dependency(self, dep_name: str) -> bool:
        """Check if Maven dependency matches GCP pattern."""
        return 'com.google.cloud' in dep_name or 'com.google.api' in dep_name
    
    def _create_aws_component(self, identifier: str, file_path: Path) -> InfrastructureComponent:
        """Create AWS infrastructure component."""
        return InfrastructureComponent(
            type=InfrastructureType.CLOUD,
            name=identifier,
            service="aws",
            subtype="sdk",
            configuration={"identifier": identifier},
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={"provider": "aws", "detected_from": identifier}
        )
    
    def _create_azure_component(self, identifier: str, file_path: Path) -> InfrastructureComponent:
        """Create Azure infrastructure component."""
        return InfrastructureComponent(
            type=InfrastructureType.CLOUD,
            name=identifier,
            service="azure",
            subtype="sdk",
            configuration={"identifier": identifier},
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={"provider": "azure", "detected_from": identifier}
        )
    
    def _create_gcp_component(self, identifier: str, file_path: Path) -> InfrastructureComponent:
        """Create GCP infrastructure component."""
        return InfrastructureComponent(
            type=InfrastructureType.CLOUD,
            name=identifier,
            service="gcp",
            subtype="sdk",
            configuration={"identifier": identifier},
            source_file=str(file_path),
            classification=DependencyType.UNKNOWN,
            metadata={"provider": "gcp", "detected_from": identifier}
        )