"""Messaging infrastructure scanner for detecting messaging systems."""

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


class MessagingScanner(BaseInfrastructureScanner):
    """Scanner for detecting messaging systems in configuration files and dependencies."""
    
    def __init__(self):
        """Initialize the MessagingScanner."""
        # Messaging system patterns for different languages
        self.messaging_patterns = {
            # Apache Kafka
            'kafka': {
                'drivers': ['kafka-python', 'kafkajs', 'spring-kafka', 'kafka-clients', 'confluent-kafka'],
                'connection_patterns': [
                    r'kafka://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)kafka[\._-]',
                    r'(?i)bootstrap[._-]servers',
                    r'(?i)kafka[._-]brokers',
                    r'(?i)producer[._-]kafka',
                    r'(?i)consumer[._-]kafka',
                ],
                'subtype': 'streaming_platform'
            },
            # RabbitMQ
            'rabbitmq': {
                'drivers': ['pika', 'amqplib', 'spring-rabbit', 'spring-amqp', 'amqp', 'rabbitmq-client'],
                'connection_patterns': [
                    r'amqp://[^"\s]+',
                    r'amqps://[^"\s]+',
                    r'rabbitmq://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)(rabbitmq|rabbit|amqp)[\._-]',
                    r'(?i)amqp[._-]url',
                    r'(?i)rabbit[._-]host',
                    r'(?i)queue[._-]name',
                ],
                'subtype': 'message_queue'
            },
            # Redis (when used for messaging)
            'redis': {
                'drivers': ['redis', 'redis-py', 'ioredis', 'jedis', 'lettuce'],
                'connection_patterns': [
                    r'redis://[^"\s]+',
                    r'rediss://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)redis[\._-]',
                    r'(?i)pub[._-]sub',
                    r'(?i)redis[._-]channel',
                    r'(?i)message[._-]redis',
                ],
                'subtype': 'pub_sub_system'
            },
            # Apache ActiveMQ
            'activemq': {
                'drivers': ['activemq-client', 'stomp', 'stompit', 'activemq-spring'],
                'connection_patterns': [
                    r'tcp://[^"\s]+:61616',
                    r'activemq://[^"\s]+',
                    r'stomp://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)activemq[\._-]',
                    r'(?i)stomp[._-]',
                    r'(?i)jms[._-]broker',
                    r'(?i)broker[._-]url',
                ],
                'subtype': 'message_queue'
            },
            # Apache Pulsar
            'pulsar': {
                'drivers': ['pulsar-client', 'pulsar-client-py', 'pulsar-functions'],
                'connection_patterns': [
                    r'pulsar://[^"\s]+',
                    r'pulsar\+ssl://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)pulsar[\._-]',
                    r'(?i)pulsar[._-]service',
                    r'(?i)pulsar[._-]url',
                ],
                'subtype': 'streaming_platform'
            },
            # NATS
            'nats': {
                'drivers': ['nats', 'nats-streaming', 'asyncio-nats', 'java-nats'],
                'connection_patterns': [
                    r'nats://[^"\s]+',
                    r'nats\+ssl://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)nats[\._-]',
                    r'(?i)nats[._-]server',
                    r'(?i)nats[._-]url',
                ],
                'subtype': 'message_queue'
            },
            # Amazon SQS
            'sqs': {
                'drivers': ['boto3', 'aws-sdk', '@aws-sdk/client-sqs'],
                'connection_patterns': [
                    r'sqs://[^"\s]+',
                    r'https://sqs\.[^".\s]+\.amazonaws\.com',
                ],
                'config_patterns': [
                    r'(?i)sqs[\._-]',
                    r'(?i)aws[._-]sqs',
                    r'(?i)queue[._-]url.*sqs',
                ],
                'subtype': 'cloud_queue'
            },
            # Amazon SNS
            'sns': {
                'drivers': ['boto3', 'aws-sdk', '@aws-sdk/client-sns'],
                'connection_patterns': [
                    r'sns://[^"\s]+',
                    r'arn:aws:sns:[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)sns[\._-]',
                    r'(?i)aws[._-]sns',
                    r'(?i)topic[._-]arn',
                ],
                'subtype': 'cloud_pub_sub'
            },
            # Azure Service Bus
            'azure_servicebus': {
                'drivers': ['azure-servicebus', '@azure/service-bus', 'azure-messaging-servicebus'],
                'connection_patterns': [
                    r'sb://[^"\s]+\.servicebus\.windows\.net',
                    r'Endpoint=sb://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)servicebus[\._-]',
                    r'(?i)azure[._-]servicebus',
                    r'(?i)service[._-]bus',
                ],
                'subtype': 'cloud_queue'
            },
            # Google Pub/Sub
            'google_pubsub': {
                'drivers': ['google-cloud-pubsub', '@google-cloud/pubsub', 'google-cloud-messaging'],
                'connection_patterns': [
                    r'projects/[^/]+/topics/[^"\s]+',
                    r'projects/[^/]+/subscriptions/[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)pubsub[\._-]',
                    r'(?i)google[._-]pubsub',
                    r'(?i)gcp[._-]pubsub',
                ],
                'subtype': 'cloud_pub_sub'
            },
            # Apache RocketMQ
            'rocketmq': {
                'drivers': ['rocketmq-client-python', 'rocketmq-spring-boot-starter'],
                'connection_patterns': [
                    r'rocketmq://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)rocketmq[\._-]',
                    r'(?i)rocket[._-]mq',
                ],
                'subtype': 'message_queue'
            },
            # ZeroMQ
            'zeromq': {
                'drivers': ['pyzmq', 'zeromq', 'jzmq', 'zmq'],
                'connection_patterns': [
                    r'tcp://[^"\s]+:[0-9]+',
                    r'ipc://[^"\s]+',
                    r'inproc://[^"\s]+',
                ],
                'config_patterns': [
                    r'(?i)(zeromq|zmq)[\._-]',
                    r'(?i)zmq[._-]socket',
                ],
                'subtype': 'message_queue'
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
        return InfrastructureType.MESSAGING
    
    def scan_file(self, file_path: Path) -> List[InfrastructureComponent]:
        """Scan a single file for messaging components."""
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
        """Scan JSON file for messaging dependencies."""
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
        """Scan YAML file for messaging configuration."""
        components = []
        
        try:
            data = yaml.safe_load(content)
            
            if data:
                # Look for messaging configuration sections
                components.extend(self._scan_yaml_data(file_path, data))
            
            # Also scan the raw content for connection strings
            components.extend(self._scan_text_file(file_path, content))
            
        except yaml.YAMLError:
            # If YAML is invalid, try text-based scanning
            components.extend(self._scan_text_file(file_path, content))
        
        return components
    
    def _scan_xml_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan XML file (like pom.xml) for messaging dependencies."""
        components = []
        
        try:
            root = ET.fromstring(content)
            
            # Look for Maven dependencies
            for dependency in root.findall('.//dependency'):
                group_id = dependency.find('groupId')
                artifact_id = dependency.find('artifactId')
                
                if group_id is not None and artifact_id is not None:
                    dep_string = f"{group_id.text}:{artifact_id.text}"
                    messaging_type = self._identify_messaging_from_dependency(dep_string)
                    
                    if messaging_type:
                        components.append(self._create_messaging_component(
                            file_path, messaging_type, {
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
        """Scan requirements.txt file for messaging dependencies."""
        components = []
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse requirement line (package==version or package>=version, etc.)
                package_name = re.split(r'[<>=!]', line)[0].strip()
                messaging_type = self._identify_messaging_from_dependency(package_name)
                
                if messaging_type:
                    components.append(self._create_messaging_component(
                        file_path, messaging_type, {
                            'dependency': line,
                            'type': 'python_requirement'
                        }
                    ))
        
        return components
    
    def _scan_properties_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan properties/env file for messaging configuration."""
        components = []
        detected_types = set()  # Track detected types to avoid duplicates
        
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                # Look for messaging configuration patterns
                for messaging_type, patterns in self.messaging_patterns.items():
                    if messaging_type in detected_types:
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
                            components.append(self._create_messaging_component(
                                file_path, messaging_type, config, line_num
                            ))
                            detected_types.add(messaging_type)
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
                                components.append(self._create_messaging_component(
                                    file_path, messaging_type, config, line_num
                                ))
                                detected_types.add(messaging_type)
                                break
        
        return components
    
    def _scan_text_file(self, file_path: Path, content: str) -> List[InfrastructureComponent]:
        """Scan any text file for messaging connection strings."""
        components = []
        
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Look for connection strings
            for messaging_type, patterns in self.messaging_patterns.items():
                for pattern in patterns['connection_patterns']:
                    if re.search(pattern, line):
                        connection_url = re.search(pattern, line).group(0)
                        components.append(self._create_messaging_component(
                            file_path, messaging_type, {
                                'connection_url': connection_url,
                                'type': 'connection_string'
                            }, line_num
                        ))
                        break
        
        return components
    
    def _scan_dependencies_dict(self, file_path: Path, dependencies: Dict[str, str]) -> List[InfrastructureComponent]:
        """Scan a dependencies dictionary for messaging packages."""
        components = []
        
        for package_name, version in dependencies.items():
            messaging_type = self._identify_messaging_from_dependency(package_name)
            
            if messaging_type:
                components.append(self._create_messaging_component(
                    file_path, messaging_type, {
                        'dependency': f"{package_name}@{version}",
                        'type': 'package_dependency'
                    }
                ))
        
        return components
    
    def _scan_yaml_data(self, file_path: Path, data: Any) -> List[InfrastructureComponent]:
        """Recursively scan YAML data for messaging configuration."""
        components = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                key_lower = key.lower()
                
                # Check for messaging configuration sections
                for messaging_type, patterns in self.messaging_patterns.items():
                    if messaging_type in key_lower or any(pattern.replace(r'(?i)', '').replace(r'[\._-]', '') in key_lower for pattern in patterns['config_patterns']):
                        # Found messaging config section
                        if isinstance(value, dict):
                            config = self._extract_messaging_config(value)
                            components.append(self._create_messaging_component(
                                file_path, messaging_type, config
                            ))
                        elif isinstance(value, str):
                            # Single value config
                            components.append(self._create_messaging_component(
                                file_path, messaging_type, {
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
    
    def _extract_messaging_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract messaging configuration from YAML section."""
        extracted = {'type': 'yaml_configuration'}
        
        # Common messaging config keys
        config_keys = {
            'host': 'host',
            'port': 'port',
            'url': 'connection_url',
            'uri': 'connection_url',
            'broker_url': 'connection_url',
            'bootstrap_servers': 'bootstrap_servers',
            'username': 'username',
            'password': 'password',
            'vhost': 'vhost',
            'topic': 'topic',
            'queue': 'queue',
            'group_id': 'group_id',
            'consumer_group': 'group_id'
        }
        
        for key, value in config.items():
            if key.lower() in config_keys:
                extracted[config_keys[key.lower()]] = value
        
        # Construct connection URL if possible
        if 'host' in extracted and 'port' in extracted:
            extracted['connection_url'] = f"{extracted['host']}:{extracted['port']}"
            
        return extracted
    
    def _identify_messaging_from_dependency(self, dependency: str) -> Optional[str]:
        """Identify messaging type from dependency name."""
        dependency_lower = dependency.lower()
        
        for messaging_type, patterns in self.messaging_patterns.items():
            for driver in patterns['drivers']:
                if driver.lower() in dependency_lower:
                    return messaging_type
        
        return None
    
    def _extract_connection_details(self, connection_url: str) -> Dict[str, Any]:
        """Extract details from messaging connection URL."""
        details = {}
        
        # Parse common connection URL patterns
        if '://' in connection_url:
            try:
                # Extract host:port for messaging systems
                if 'amqp://' in connection_url or 'amqps://' in connection_url:
                    # amqp://user:pass@host:port/vhost
                    match = re.search(r'//(?:[^:@]+(?::[^@]+)?@)?([^:/]+):?(\d+)?/?(.+)?', connection_url)
                    if match:
                        details['host'] = match.group(1)
                        if match.group(2):
                            details['port'] = match.group(2)
                        if match.group(3):
                            details['vhost'] = match.group(3)
                elif 'redis://' in connection_url or 'rediss://' in connection_url:
                    match = re.search(r'//(?:[^:@]+(?::[^@]+)?@)?([^:/]+):?(\d+)?/?(\d+)?', connection_url)
                    if match:
                        details['host'] = match.group(1)
                        if match.group(2):
                            details['port'] = match.group(2)
                        if match.group(3):
                            details['database'] = match.group(3)
                elif 'tcp://' in connection_url:
                    # tcp://host:port for ActiveMQ, ZeroMQ
                    match = re.search(r'//([^:/]+):?(\d+)?', connection_url)
                    if match:
                        details['host'] = match.group(1)
                        if match.group(2):
                            details['port'] = match.group(2)
                else:
                    # Generic pattern
                    match = re.search(r'//(?:[^:@]+(?::[^@]+)?@)?([^:/]+):?(\d+)?', connection_url)
                    if match:
                        details['host'] = match.group(1)
                        if match.group(2):
                            details['port'] = match.group(2)
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
            
            if 'url' in key or 'servers' in key:
                if 'bootstrap' in key and 'servers' in key:
                    details['bootstrap_servers'] = value
                else:
                    details.update(self._extract_connection_details(value))
            elif 'host' in key:
                details['host'] = value
            elif 'port' in key:
                details['port'] = value
            elif 'topic' in key:
                details['topic'] = value
            elif 'queue' in key:
                details['queue'] = value
            elif 'group' in key:
                details['group_id'] = value
        
        return details
    
    def _create_messaging_component(self, file_path: Path, messaging_type: str, 
                                    configuration: Dict[str, Any], 
                                    line_number: Optional[int] = None) -> InfrastructureComponent:
        """Create a messaging infrastructure component."""
        return InfrastructureComponent(
            type=InfrastructureType.MESSAGING,
            name=messaging_type,
            service=messaging_type,
            subtype=self.messaging_patterns[messaging_type]['subtype'],
            configuration=configuration,
            source_file=str(file_path),
            line_number=line_number
        )