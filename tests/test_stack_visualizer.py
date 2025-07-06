"""Tests for StackVisualizer - Stage 7 technology stack visualization."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import json

from dependency_scanner_tool.infrastructure_scanners.stack_visualizer import StackVisualizer
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureComponent, InfrastructureType, TechnologyStack
)
from dependency_scanner_tool.scanner import Dependency, DependencyType


class TestStackVisualizer:
    """Test suite for StackVisualizer."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.visualizer = StackVisualizer()
    
    def test_visualizer_initialization(self):
        """Test StackVisualizer initialization."""
        assert self.visualizer is not None
    
    def test_generate_technology_stack_summary(self):
        """Test generation of technology stack summary."""
        # Mock dependencies
        dependencies = [
            Dependency(name="flask", version="2.0.1", dependency_type=DependencyType.ALLOWED),
            Dependency(name="django", version="4.0.0", dependency_type=DependencyType.ALLOWED),
            Dependency(name="requests", version="2.26.0", dependency_type=DependencyType.ALLOWED),
            Dependency(name="numpy", version="1.21.0", dependency_type=DependencyType.ALLOWED),
        ]
        
        # Mock infrastructure components
        infrastructure = [
            InfrastructureComponent(
                type=InfrastructureType.CONTAINER,
                name="docker",
                service="docker",
                subtype="containerization",
                configuration={},
                source_file="/test/Dockerfile",
                line_number=1,
                classification=DependencyType.ALLOWED,
                metadata={}
            ),
            InfrastructureComponent(
                type=InfrastructureType.DATABASE,
                name="postgresql",
                service="postgresql",
                subtype="relational_database",
                configuration={},
                source_file="/test/docker-compose.yml",
                line_number=5,
                classification=DependencyType.ALLOWED,
                metadata={}
            ),
            InfrastructureComponent(
                type=InfrastructureType.MONITORING,
                name="prometheus",
                service="prometheus",
                subtype="monitoring",
                configuration={},
                source_file="/test/prometheus.yml",
                line_number=1,
                classification=DependencyType.ALLOWED,
                metadata={}
            )
        ]
        
        stack_summary = self.visualizer.generate_technology_stack_summary(
            dependencies, infrastructure
        )
        
        assert isinstance(stack_summary, dict)
        assert "categories" in stack_summary
        assert "backend" in stack_summary["categories"]
        assert "containerization" in stack_summary["categories"]
        assert "databases" in stack_summary["categories"]
        assert "monitoring" in stack_summary["categories"]
        
        # Check categorization
        assert "flask" in stack_summary["categories"]["backend"]
        assert "django" in stack_summary["categories"]["backend"]
        assert "docker" in stack_summary["categories"]["containerization"]
        assert "postgresql" in stack_summary["categories"]["databases"]
        assert "prometheus" in stack_summary["categories"]["monitoring"]
    
    def test_categorize_dependencies(self):
        """Test categorization of programming dependencies."""
        dependencies = [
            Dependency(name="react", version="17.0.0", dependency_type=DependencyType.ALLOWED),
            Dependency(name="express", version="4.17.1", dependency_type=DependencyType.ALLOWED),
            Dependency(name="pytest", version="6.2.4", dependency_type=DependencyType.ALLOWED),
            Dependency(name="boto3", version="1.18.0", dependency_type=DependencyType.ALLOWED),
            Dependency(name="unknown-lib", version="1.0.0", dependency_type=DependencyType.UNKNOWN),
        ]
        
        categories = self.visualizer.categorize_dependencies(dependencies)
        
        assert isinstance(categories, dict)
        assert "frontend" in categories
        assert "backend" in categories
        assert "testing" in categories
        assert "cloud_services" in categories
        assert "uncategorized" in categories
        
        assert "react" in categories["frontend"]
        assert "express" in categories["backend"]
        assert "pytest" in categories["testing"]
        assert "boto3" in categories["cloud_services"]
        assert "unknown-lib" in categories["uncategorized"]
    
    def test_categorize_infrastructure_components(self):
        """Test categorization of infrastructure components."""
        components = [
            InfrastructureComponent(
                type=InfrastructureType.IaC,
                name="terraform",
                service="terraform",
                subtype="infrastructure_as_code",
                configuration={},
                source_file="/test/main.tf",
                line_number=1,
                classification=DependencyType.ALLOWED,
                metadata={}
            ),
            InfrastructureComponent(
                type=InfrastructureType.CICD,
                name="jenkins",
                service="jenkins",
                subtype="ci_cd",
                configuration={},
                source_file="/test/Jenkinsfile",
                line_number=1,
                classification=DependencyType.ALLOWED,
                metadata={}
            ),
            InfrastructureComponent(
                type=InfrastructureType.MESSAGING,
                name="kafka",
                service="kafka",
                subtype="message_queue",
                configuration={},
                source_file="/test/docker-compose.yml",
                line_number=10,
                classification=DependencyType.ALLOWED,
                metadata={}
            )
        ]
        
        categories = self.visualizer.categorize_infrastructure_components(components)
        
        assert isinstance(categories, dict)
        assert "infrastructure_as_code" in categories
        assert "ci_cd" in categories
        assert "messaging" in categories
        
        assert "terraform" in categories["infrastructure_as_code"]
        assert "jenkins" in categories["ci_cd"]
        assert "kafka" in categories["messaging"]
    
    def test_generate_diagram_data(self):
        """Test generation of diagram data for visualization."""
        stack_summary = {
            "categories": {
                "web_frameworks": ["flask", "django"],
                "databases": ["postgresql", "redis"],
                "containerization": ["docker"],
                "monitoring": ["prometheus", "grafana"]
            }
        }
        
        diagram_data = self.visualizer.generate_diagram_data(stack_summary)
        
        assert isinstance(diagram_data, dict)
        assert "nodes" in diagram_data
        assert "edges" in diagram_data
        assert "layers" in diagram_data
        
        # Check nodes
        nodes = diagram_data["nodes"]
        assert len(nodes) > 0
        node_names = [node["name"] for node in nodes]
        assert "flask" in node_names
        assert "postgresql" in node_names
        assert "docker" in node_names
        
        # Check layers
        layers = diagram_data["layers"]
        assert "presentation" in layers
        assert "application" in layers
        assert "data" in layers
        assert "infrastructure" in layers
    
    def test_estimate_cost_tier(self):
        """Test cost tier estimation for components."""
        # Test database cost estimation
        db_component = InfrastructureComponent(
            type=InfrastructureType.DATABASE,
            name="postgresql",
            service="postgresql",
            subtype="relational_database",
            configuration={"instance_type": "db.t3.micro"},
            source_file="/test/terraform.tf",
            line_number=1,
            classification=DependencyType.ALLOWED,
            metadata={}
        )
        
        cost_tier = self.visualizer.estimate_cost_tier(db_component)
        assert cost_tier in ["free", "low", "medium", "high", "unknown"]
        
        # Test monitoring cost estimation
        monitoring_component = InfrastructureComponent(
            type=InfrastructureType.MONITORING,
            name="datadog",
            service="datadog",
            subtype="apm",
            configuration={"host_count": 10},
            source_file="/test/datadog.yml",
            line_number=1,
            classification=DependencyType.ALLOWED,
            metadata={}
        )
        
        cost_tier = self.visualizer.estimate_cost_tier(monitoring_component)
        assert cost_tier in ["free", "low", "medium", "high", "unknown"]
    
    def test_generate_optimization_recommendations(self):
        """Test generation of optimization recommendations."""
        components = [
            InfrastructureComponent(
                type=InfrastructureType.DATABASE,
                name="mysql",
                service="mysql",
                subtype="relational_database",
                configuration={},
                source_file="/test/docker-compose.yml",
                line_number=5,
                classification=DependencyType.ALLOWED,
                metadata={}
            ),
            InfrastructureComponent(
                type=InfrastructureType.DATABASE,
                name="postgresql",
                service="postgresql",
                subtype="relational_database",
                configuration={},
                source_file="/test/docker-compose.yml",
                line_number=15,
                classification=DependencyType.ALLOWED,
                metadata={}
            ),
            InfrastructureComponent(
                type=InfrastructureType.MONITORING,
                name="prometheus",
                service="prometheus",
                subtype="monitoring",
                configuration={},
                source_file="/test/monitoring.yml",
                line_number=1,
                classification=DependencyType.ALLOWED,
                metadata={}
            )
        ]
        
        recommendations = self.visualizer.generate_optimization_recommendations(components)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should detect multiple databases
        db_recommendation = next(
            (r for r in recommendations if "database" in r["issue"].lower()), None
        )
        assert db_recommendation is not None
        assert "multiple" in db_recommendation["issue"].lower()
        assert "consolidat" in db_recommendation["recommendation"].lower()
    
    def test_generate_architecture_layers(self):
        """Test generation of architecture layers."""
        stack_summary = {
            "categories": {
                "web_frameworks": ["react", "angular"],
                "backend": ["spring-boot", "express"],
                "databases": ["postgresql", "mongodb"],
                "containerization": ["docker"],
                "cloud_services": ["aws-s3", "azure-storage"],
                "monitoring": ["prometheus", "grafana"]
            }
        }
        
        layers = self.visualizer.generate_architecture_layers(stack_summary)
        
        assert isinstance(layers, dict)
        assert "presentation" in layers
        assert "application" in layers
        assert "data" in layers
        assert "infrastructure" in layers
        
        # Check layer assignments
        assert "react" in layers["presentation"]
        assert "spring-boot" in layers["application"]
        assert "postgresql" in layers["data"]
        assert "docker" in layers["infrastructure"]
    
    def test_detect_technology_patterns(self):
        """Test detection of common technology patterns."""
        stack_summary = {
            "categories": {
                "web_frameworks": ["react"],
                "backend": ["express"],
                "databases": ["mongodb"],
                "containerization": ["docker"],
                "orchestration": ["kubernetes"]
            }
        }
        
        patterns = self.visualizer.detect_technology_patterns(stack_summary)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        # Should detect MEAN stack pattern
        mean_pattern = next(
            (p for p in patterns if "mean" in p["pattern"].lower()), None
        )
        if mean_pattern:
            assert "mongodb" in mean_pattern["technologies"]
            assert "express" in mean_pattern["technologies"]
            assert "react" in mean_pattern["technologies"]
    
    def test_export_diagram_json(self):
        """Test export of diagram data to JSON."""
        diagram_data = {
            "nodes": [
                {"id": "1", "name": "flask", "category": "web_framework", "layer": "application"},
                {"id": "2", "name": "postgresql", "category": "database", "layer": "data"}
            ],
            "edges": [
                {"source": "1", "target": "2", "relationship": "uses"}
            ],
            "layers": {
                "application": ["flask"],
                "data": ["postgresql"]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            self.visualizer.export_diagram_json(diagram_data, Path(f.name))
            
            # Read back and verify
            with open(f.name, 'r') as read_file:
                exported_data = json.load(read_file)
                
            assert exported_data == diagram_data
            assert "nodes" in exported_data
            assert "edges" in exported_data
            assert len(exported_data["nodes"]) == 2
    
    def test_generate_mermaid_diagram(self):
        """Test generation of Mermaid diagram syntax."""
        diagram_data = {
            "nodes": [
                {"id": "1", "name": "frontend", "category": "web_framework", "layer": "presentation"},
                {"id": "2", "name": "backend", "category": "api", "layer": "application"},
                {"id": "3", "name": "database", "category": "database", "layer": "data"}
            ],
            "edges": [
                {"source": "1", "target": "2", "relationship": "calls"},
                {"source": "2", "target": "3", "relationship": "queries"}
            ]
        }
        
        mermaid_syntax = self.visualizer.generate_mermaid_diagram(diagram_data)
        
        assert isinstance(mermaid_syntax, str)
        assert "graph TD" in mermaid_syntax
        assert "frontend" in mermaid_syntax
        assert "backend" in mermaid_syntax
        assert "database" in mermaid_syntax
        assert "-->" in mermaid_syntax  # Mermaid arrow syntax
    
    def test_empty_inputs_handling(self):
        """Test handling of empty inputs."""
        # Test with empty dependencies and infrastructure
        stack_summary = self.visualizer.generate_technology_stack_summary([], [])
        
        assert isinstance(stack_summary, dict)
        assert "categories" in stack_summary
        
        # Categories should be empty or have empty lists
        for category_name, items in stack_summary["categories"].items():
            assert isinstance(items, list)
            assert len(items) == 0
    
    def test_large_stack_handling(self):
        """Test handling of large technology stacks."""
        # Create large number of dependencies
        dependencies = []
        for i in range(100):
            dependencies.append(
                Dependency(
                    name=f"library-{i}",
                    version="1.0.0",
                    dependency_type=DependencyType.ALLOWED
                )
            )
        
        # Create large number of infrastructure components
        infrastructure = []
        for i in range(50):
            infrastructure.append(
                InfrastructureComponent(
                    type=InfrastructureType.CONTAINER,
                    name=f"service-{i}",
                    service=f"service-{i}",
                    subtype="container",
                    configuration={},
                    source_file=f"/test/service-{i}.yml",
                    line_number=1,
                    classification=DependencyType.ALLOWED,
                    metadata={}
                )
            )
        
        stack_summary = self.visualizer.generate_technology_stack_summary(
            dependencies, infrastructure
        )
        
        assert isinstance(stack_summary, dict)
        assert "categories" in stack_summary
        
        # Should handle large inputs without errors
        total_items = sum(len(items) for items in stack_summary["categories"].values())
        assert total_items > 0