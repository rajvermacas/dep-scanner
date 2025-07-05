"""Database infrastructure scanner for detecting database technologies."""

import json
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

import yaml

from dependency_scanner_tool.infrastructure_scanners.base import BaseInfrastructureScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType, InfrastructureComponent

logger = logging.getLogger(__name__)


class DatabaseScanner(BaseInfrastructureScanner):
    """Scanner for detecting database technologies in configuration files and dependencies."""
    
    def __init__(self):
        """Initialize the DatabaseScanner."""
        # Database driver patterns for different languages
        self.database_patterns = {
            # PostgreSQL
            'postgresql': {
                'drivers': ['postgresql', 'psycopg2', 'psycopg2-binary', 'pg', 'postgres'],
                'connection_patterns': [
                    r'postgresql://[^"\s]+',
                    r'postgres://[^"\s]+',
                    r'jdbc:postgresql://[^"\s]+',
                    r'postgresql\+[^:]+://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)(postgresql|postgres|pg)[\._-]',
                    r'(?i)datasource\.url.*postgresql',
                    r'(?i)adapter.*postgresql',
                    r'(?i)database.*postgresql',
                ],
                'subtype': 'relational_database'
            },
            # MySQL
            'mysql': {
                'drivers': ['mysql', 'mysql2', 'mysql-connector-java', 'mysql-connector-python', 'PyMySQL'],
                'connection_patterns': [
                    r'mysql://[^"\s]+',
                    r'jdbc:mysql://[^"\s]+',
                    r'mysql\+[^:]+://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)mysql[\._-]',
                    r'(?i)datasource\.url.*mysql',
                    r'(?i)adapter.*mysql',
                    r'(?i)database.*mysql',
                ],
                'subtype': 'relational_database'
            },
            # MongoDB
            'mongodb': {
                'drivers': ['mongoose', 'pymongo', 'mongodb-driver-sync', 'mongodb-driver-core', 'mongo'],
                'connection_patterns': [
                    r'mongodb://[^"\s]+',
                    r'mongodb\+srv://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)(mongodb|mongo)[\._-]',
                    r'(?i)mongo_uri',
                    r'(?i)database.*mongo',
                ],
                'subtype': 'document_database'
            },
            # Redis
            'redis': {
                'drivers': ['redis', 'jedis', 'redis-py', 'ioredis', 'hiredis'],
                'connection_patterns': [
                    r'redis://[^"\s]+',
                    r'rediss://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)redis[\._-]',
                    r'(?i)cache.*redis',
                    r'(?i)session.*redis',
                ],
                'subtype': 'cache_database'
            },
            # SQLite
            'sqlite': {
                'drivers': ['sqlite', 'sqlite3', 'sqlite-jdbc'],
                'connection_patterns': [
                    r'sqlite://[^"\s]+',
                    r'jdbc:sqlite:[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)sqlite[\._-]',
                    r'(?i)datasource\.url.*sqlite',
                    r'(?i)database.*sqlite',
                ],
                'subtype': 'relational_database'
            },
            # Oracle
            'oracle': {
                'drivers': ['oracledb', 'cx_Oracle', 'ojdbc', 'oracle-database-driver'],
                'connection_patterns': [
                    r'oracle://[^"\s]+',
                    r'jdbc:oracle:[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)oracle[\._-]',
                    r'(?i)datasource\.url.*oracle',
                    r'(?i)database.*oracle',
                ],
                'subtype': 'relational_database'
            },
            # SQL Server
            'sqlserver': {
                'drivers': ['mssql', 'pymssql', 'pyodbc', 'mssql-jdbc', 'sqlserver-jdbc'],
                'connection_patterns': [
                    r'mssql://[^"\s]+',
                    r'jdbc:sqlserver://[^"\s]+',
                    r'sqlserver://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)(mssql|sqlserver)[\._-]',
                    r'(?i)datasource\.url.*sqlserver',
                    r'(?i)database.*sqlserver',
                ],
                'subtype': 'relational_database'
            },
            # Cassandra
            'cassandra': {
                'drivers': ['cassandra-driver', 'datastax-driver', 'cassandra-java-driver'],
                'connection_patterns': [
                    r'cassandra://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)cassandra[\._-]',
                    r'(?i)database.*cassandra',
                ],
                'subtype': 'column_database'
            },
            # ElasticSearch
            'elasticsearch': {
                'drivers': ['elasticsearch', 'elastic-search', 'elasticsearch-dsl'],
                'connection_patterns': [
                    r'elasticsearch://[^"\s]+',
                    r'elastic://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)(elasticsearch|elastic)[\._-]',
                    r'(?i)search.*elastic',
                ],
                'subtype': 'search_database'
            }
        }
    
    def get_supported_file_patterns(self) -> List[str]:
        """Return list of file patterns this scanner can handle."""
        return [
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
    
    def get_infrastructure_type(self) -> InfrastructureType:
        """Return the infrastructure type this scanner handles."""
        return InfrastructureType.DATABASE
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file for database components."""
        components = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Try different parsing strategies based on file type
            if file_path.suffix.lower() in ['.json']:
                components.extend(self._scan_json_file(file_path, content))
            elif file_path.suffix.lower() in ['.yaml', '.yml']:
                components.extend(self._scan_yaml_file(file_path, content))
            elif file_path.suffix.lower() in ['.xml']:
                components.extend(self._scan_xml_file(file_path, content))
            elif file_path.name.lower() in ['requirements.txt']:
                components.extend(self._scan_requirements_file(file_path, content))
            elif file_path.suffix.lower() in ['.properties', '.env', '.conf', '.ini']:
                components.extend(self._scan_properties_file(file_path, content))
            else:
                # Fallback to text-based scanning
                components.extend(self._scan_text_file(file_path, content))
                
        except Exception as e:
            logger.debug(f"Error scanning file {file_path}: {e}")
            # Return empty list for invalid files
            return []
        
        return components
    
    def _scan_json_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan JSON file for database dependencies."""
        components = []
        
        try:
            data = json.loads(content)
            
            # Check for dependencies sections
            if 'dependencies' in data:
                components.extend(self._scan_dependencies_dict(file_path, data['dependencies']))
            
            if 'devDependencies' in data:
                components.extend(self._scan_dependencies_dict(file_path, data['devDependencies']))
            
            # Also scan the raw content for connection strings
            components.extend(self._scan_text_file(file_path, content))
            
        except json.JSONDecodeError:
            # If JSON is invalid, try text-based scanning
            components.extend(self._scan_text_file(file_path, content))
        
        return components
    
    def _scan_yaml_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan YAML file for database configuration."""
        components = []
        
        try:
            data = yaml.safe_load(content)
            
            if data:
                # Look for database configuration sections
                components.extend(self._scan_yaml_data(file_path, data))
            
            # Also scan the raw content for connection strings
            components.extend(self._scan_text_file(file_path, content))
            
        except yaml.YAMLError:
            # If YAML is invalid, try text-based scanning
            components.extend(self._scan_text_file(file_path, content))
        
        return components
    
    def _scan_xml_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan XML file (like pom.xml) for database dependencies."""
        components = []
        
        try:
            root = ET.fromstring(content)
            
            # Look for Maven dependencies
            for dependency in root.findall('.//dependency'):
                group_id = dependency.find('groupId')
                artifact_id = dependency.find('artifactId')
                
                if group_id is not None and artifact_id is not None:
                    dep_string = f"{group_id.text}:{artifact_id.text}"
                    db_type = self._identify_database_from_dependency(dep_string)
                    
                    if db_type:
                        components.append(self._create_database_component(
                            file_path, db_type, {
                                'dependency': dep_string,
                                'type': 'maven_dependency'
                            }
                        ))
            
            # Also scan the raw content for connection strings
            components.extend(self._scan_text_file(file_path, content))
            
        except ET.ParseError:
            # If XML is invalid, try text-based scanning
            components.extend(self._scan_text_file(file_path, content))
        
        return components
    
    def _scan_requirements_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan requirements.txt file for database dependencies."""
        components = []
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse requirement line (package==version or package>=version, etc.)
                package_name = re.split(r'[<>=!]', line)[0].strip()
                db_type = self._identify_database_from_dependency(package_name)
                
                if db_type:
                    components.append(self._create_database_component(
                        file_path, db_type, {
                            'dependency': line,
                            'type': 'python_requirement'
                        }
                    ))
        
        return components
    
    def _scan_properties_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan properties/env file for database configuration."""
        components = []
        detected_types = set()  # Track detected types to avoid duplicates
        
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                # Look for database configuration patterns
                for db_type, patterns in self.database_patterns.items():
                    if db_type in detected_types:
                        continue  # Already detected this type
                    
                    # Check connection patterns first (more specific)
                    connection_found = False
                    for pattern in patterns['connection_patterns']:
                        if re.search(pattern, line):
                            connection_url = re.search(pattern, line).group(0)
                            config = self._extract_connection_details(connection_url)
                            config.update({
                                'connection_url': connection_url,
                                'type': 'connection_string'
                            })
                            components.append(self._create_database_component(
                                file_path, db_type, config, line_num
                            ))
                            detected_types.add(db_type)
                            connection_found = True
                            break
                    
                    # Only check config patterns if connection not found
                    if not connection_found:
                        for pattern in patterns['config_patterns']:
                            if re.search(pattern, line):
                                config = self._extract_config_details(line)
                                config.update({
                                    'config_line': line,
                                    'type': 'configuration'
                                })
                                components.append(self._create_database_component(
                                    file_path, db_type, config, line_num
                                ))
                                detected_types.add(db_type)
                                break
        
        return components
    
    def _scan_text_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan any text file for database connection strings."""
        components = []
        
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Look for connection strings
            for db_type, patterns in self.database_patterns.items():
                for pattern in patterns['connection_patterns']:
                    if re.search(pattern, line):
                        connection_url = re.search(pattern, line).group(0)
                        components.append(self._create_database_component(
                            file_path, db_type, {
                                'connection_url': connection_url,
                                'type': 'connection_string'
                            }, line_num
                        ))
                        break
        
        return components
    
    def _scan_dependencies_dict(self, file_path: Path, dependencies: Dict[str, str]) -> List[InfrastructureComponent]:
        """Scan a dependencies dictionary for database packages."""
        components = []
        
        for package_name, version in dependencies.items():
            db_type = self._identify_database_from_dependency(package_name)
            
            if db_type:
                components.append(self._create_database_component(
                    file_path, db_type, {
                        'dependency': f"{package_name}@{version}",
                        'type': 'package_dependency'
                    }
                ))
        
        return components
    
    def _scan_yaml_data(self, file_path: Path, data: Any) -> List[InfrastructureComponent]:
        """Recursively scan YAML data for database configuration."""
        components = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                key_lower = key.lower()
                
                # Check for database configuration sections
                for db_type, patterns in self.database_patterns.items():
                    if db_type in key_lower or any(pattern.replace(r'(?i)', '').replace(r'[\._-]', '') in key_lower for pattern in patterns['config_patterns']):
                        # Found database config section
                        if isinstance(value, dict):
                            config = self._extract_database_config(value)
                            components.append(self._create_database_component(
                                file_path, db_type, config
                            ))
                        elif isinstance(value, str):
                            # Single value config
                            components.append(self._create_database_component(
                                file_path, db_type, {
                                    'config_value': value,
                                    'type': 'yaml_configuration'
                                }
                            ))
                
                # Recursively scan nested structures
                if isinstance(value, (dict, list)):
                    components.extend(self._scan_yaml_data(file_path, value))
        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    components.extend(self._scan_yaml_data(file_path, item))
        
        return components
    
    def _extract_database_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract database configuration from YAML section."""
        extracted = {'type': 'yaml_configuration'}
        
        # Common database config keys
        config_keys = {
            'host': 'host',
            'port': 'port',
            'database': 'database_name',
            'name': 'database_name',
            'user': 'username',
            'username': 'username',
            'password': 'password',
            'url': 'connection_url',
            'uri': 'connection_url',
            'adapter': 'adapter'
        }
        
        for key, value in config.items():
            if key.lower() in config_keys:
                extracted[config_keys[key.lower()]] = value
        
        # Construct connection URL if possible
        if 'host' in extracted and 'port' in extracted:
            extracted['connection_url'] = f"{extracted['host']}:{extracted['port']}"
            
        return extracted
    
    def _identify_database_from_dependency(self, dependency: str) -> Optional[str]:
        """Identify database type from dependency name."""
        dependency_lower = dependency.lower()
        
        for db_type, patterns in self.database_patterns.items():
            for driver in patterns['drivers']:
                if driver.lower() in dependency_lower:
                    return db_type
        
        return None
    
    def _extract_connection_details(self, connection_url: str) -> Dict[str, Any]:
        """Extract details from database connection URL."""
        details = {}
        
        # Parse common connection URL patterns
        if '://' in connection_url:
            try:
                # Extract host:port and database name
                if 'postgresql://' in connection_url or 'postgres://' in connection_url:
                    # postgresql://user:pass@host:port/dbname
                    match = re.search(r'//(?:[^:@]+(?::[^@]+)?@)?([^:/]+):?(\d+)?/(.+)', connection_url)
                    if match:
                        details['host'] = match.group(1)
                        if match.group(2):
                            details['port'] = match.group(2)
                        details['database_name'] = match.group(3)
                elif 'mysql://' in connection_url:
                    match = re.search(r'//(?:[^:@]+(?::[^@]+)?@)?([^:/]+):?(\d+)?/(.+)', connection_url)
                    if match:
                        details['host'] = match.group(1)
                        if match.group(2):
                            details['port'] = match.group(2)
                        details['database_name'] = match.group(3)
                elif 'mongodb://' in connection_url:
                    match = re.search(r'//(?:[^:@]+(?::[^@]+)?@)?([^:/]+):?(\d+)?/(.+)', connection_url)
                    if match:
                        details['host'] = match.group(1)
                        if match.group(2):
                            details['port'] = match.group(2)
                        details['database_name'] = match.group(3)
                elif 'redis://' in connection_url:
                    match = re.search(r'//(?:[^:@]+(?::[^@]+)?@)?([^:/]+):?(\d+)?/(\d+)?', connection_url)
                    if match:
                        details['host'] = match.group(1)
                        if match.group(2):
                            details['port'] = match.group(2)
                        if match.group(3):
                            details['database_name'] = match.group(3)
            except Exception:
                pass
        
        return details
    
    def _extract_config_details(self, config_line: str) -> Dict[str, Any]:
        """Extract details from configuration line."""
        details = {}
        
        # Extract key-value pairs from properties format
        if '=' in config_line:
            key, value = config_line.split('=', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if 'url' in key:
                details.update(self._extract_connection_details(value))
            elif 'host' in key:
                details['host'] = value
            elif 'port' in key:
                details['port'] = value
            elif 'database' in key or 'db' in key:
                details['database_name'] = value
            elif 'user' in key:
                details['username'] = value
        
        return details
    
    def _create_database_component(self, file_path: Path, db_type: str, 
                                   configuration: Dict[str, Any], 
                                   line_number: Optional[int] = None) -> InfrastructureComponent:
        """Create a database infrastructure component."""
        return InfrastructureComponent(
            type=InfrastructureType.DATABASE,
            name=db_type,
            service=db_type,
            subtype=self.database_patterns[db_type]['subtype'],
            configuration=configuration,
            source_file=str(file_path),
            line_number=line_number
        )