"""Technology stack visualizer for Stage 7."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

from dependency_scanner_tool.models.infrastructure import (
    InfrastructureComponent, InfrastructureType, TechnologyStack
)
from dependency_scanner_tool.scanner import Dependency, DependencyType


logger = logging.getLogger(__name__)


class StackVisualizer:
    """Visualizer for technology stack analysis and diagram generation."""
    
    # Dependency categorization patterns
    DEPENDENCY_CATEGORIES = {
        "frontend": {
            "patterns": ["react", "angular", "vue", "svelte", "jquery", "bootstrap", "material-ui"],
            "description": "Frontend frameworks and libraries"
        },
        "backend": {
            "patterns": [
                "spring", "django", "flask", "fastapi", "express", "koa", "gin", "echo",
                "rails", "laravel", "symfony", "codeigniter"
            ],
            "description": "Backend frameworks and web servers"
        },
        "database": {
            "patterns": [
                "mysql", "postgresql", "sqlite", "mongodb", "redis", "elasticsearch",
                "cassandra", "neo4j", "influxdb", "dynamodb"
            ],
            "description": "Database drivers and clients"
        },
        "testing": {
            "patterns": [
                "pytest", "unittest", "jest", "mocha", "jasmine", "junit", "testng",
                "cypress", "selenium", "playwright"
            ],
            "description": "Testing frameworks and tools"
        },
        "cloud_services": {
            "patterns": [
                "boto3", "azure", "google-cloud", "aws-sdk", "gcp", "azure-sdk"
            ],
            "description": "Cloud service SDKs and clients"
        },
        "data_processing": {
            "patterns": [
                "pandas", "numpy", "scipy", "spark", "hadoop", "kafka", "airflow",
                "celery", "rq"
            ],
            "description": "Data processing and analytics libraries"
        },
        "ml_ai": {
            "patterns": [
                "tensorflow", "pytorch", "scikit-learn", "keras", "transformers",
                "opencv", "spacy", "nltk"
            ],
            "description": "Machine learning and AI libraries"
        },
        "devops": {
            "patterns": [
                "ansible", "terraform", "pulumi", "puppet", "chef", "saltstack"
            ],
            "description": "DevOps and infrastructure automation tools"
        }
    }
    
    # Infrastructure categorization
    INFRASTRUCTURE_CATEGORIES = {
        "infrastructure_as_code": ["terraform", "cloudformation", "arm", "pulumi"],
        "containerization": ["docker", "podman", "containerd"],
        "orchestration": ["kubernetes", "docker-compose", "docker-swarm", "openshift"],
        "ci_cd": ["jenkins", "github-actions", "gitlab-ci", "azure-devops", "circleci"],
        "databases": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch"],
        "messaging": ["kafka", "rabbitmq", "activemq", "pulsar", "nats"],
        "monitoring": ["prometheus", "grafana", "datadog", "newrelic", "splunk"],
        "security": ["vault", "consul", "cert-manager", "falco"],
        "cloud_providers": ["aws", "azure", "gcp", "digitalocean", "linode"]
    }
    
    # Architecture layers mapping
    ARCHITECTURE_LAYERS = {
        "presentation": ["frontend", "web_frameworks", "ui"],
        "application": ["backend", "api", "microservices", "application_server"],
        "data": ["databases", "cache", "search", "storage"],
        "infrastructure": ["containerization", "orchestration", "cloud_providers", "networking"],
        "monitoring": ["monitoring", "logging", "alerting", "observability"],
        "security": ["security", "authentication", "authorization", "compliance"]
    }
    
    def generate_technology_stack_summary(
        self, 
        dependencies: List[Dependency], 
        infrastructure: List[InfrastructureComponent]
    ) -> Dict[str, Any]:
        """Generate a comprehensive technology stack summary."""
        logger.info("Generating technology stack summary")
        
        # Categorize dependencies
        dependency_categories = self.categorize_dependencies(dependencies)
        
        # Categorize infrastructure components
        infrastructure_categories = self.categorize_infrastructure_components(infrastructure)
        
        # Merge categories
        all_categories = {**dependency_categories, **infrastructure_categories}
        
        # Remove empty categories
        all_categories = {k: v for k, v in all_categories.items() if v}
        
        return {
            "categories": all_categories,
            "total_dependencies": len(dependencies),
            "total_infrastructure_components": len(infrastructure),
            "technology_patterns": self.detect_technology_patterns({"categories": all_categories}),
            "architecture_layers": self.generate_architecture_layers({"categories": all_categories})
        }
    
    def categorize_dependencies(self, dependencies: List[Dependency]) -> Dict[str, List[str]]:
        """Categorize programming language dependencies."""
        categories = {}
        
        # Initialize categories
        for category_name in self.DEPENDENCY_CATEGORIES.keys():
            categories[category_name] = []
        categories["uncategorized"] = []
        
        for dependency in dependencies:
            dep_name_lower = dependency.name.lower()
            categorized = False
            
            # Check against each category
            for category_name, category_config in self.DEPENDENCY_CATEGORIES.items():
                for pattern in category_config["patterns"]:
                    if pattern in dep_name_lower:
                        categories[category_name].append(dependency.name)
                        categorized = True
                        break
                
                if categorized:
                    break
            
            # Add to uncategorized if not matched
            if not categorized:
                categories["uncategorized"].append(dependency.name)
        
        return categories
    
    def categorize_infrastructure_components(
        self, 
        components: List[InfrastructureComponent]
    ) -> Dict[str, List[str]]:
        """Categorize infrastructure components."""
        categories = {}
        
        # Initialize categories
        for category_name in self.INFRASTRUCTURE_CATEGORIES.keys():
            categories[category_name] = []
        categories["uncategorized_infrastructure"] = []
        
        for component in components:
            component_name_lower = component.name.lower()
            categorized = False
            
            # Check against each category
            for category_name, patterns in self.INFRASTRUCTURE_CATEGORIES.items():
                for pattern in patterns:
                    if pattern in component_name_lower:
                        categories[category_name].append(component.name)
                        categorized = True
                        break
                
                if categorized:
                    break
            
            # Add to uncategorized if not matched
            if not categorized:
                categories["uncategorized_infrastructure"].append(component.name)
        
        return categories
    
    def generate_diagram_data(self, stack_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate diagram data for visualization."""
        logger.info("Generating diagram data for visualization")
        
        nodes = []
        edges = []
        node_id = 1
        
        categories = stack_summary.get("categories", {})
        
        # Create nodes for each technology
        for category_name, items in categories.items():
            for item in items:
                nodes.append({
                    "id": str(node_id),
                    "name": item,
                    "category": category_name,
                    "layer": self._determine_layer(category_name),
                    "cost_tier": self._estimate_category_cost(category_name)
                })
                node_id += 1
        
        # Generate relationships/edges
        edges = self._generate_relationships(nodes)
        
        # Generate architecture layers
        layers = self.generate_architecture_layers(stack_summary)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "layers": layers,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "complexity_score": self._calculate_complexity_score(nodes, edges)
            }
        }
    
    def estimate_cost_tier(self, component: InfrastructureComponent) -> str:
        """Estimate cost tier for an infrastructure component."""
        component_name = component.name.lower()
        component_type = component.type
        
        # High-cost services
        high_cost_patterns = [
            "datadog", "newrelic", "dynatrace", "splunk",  # APM/Monitoring
            "elasticsearch", "kafka", "rabbitmq",         # Data services
            "eks", "aks", "gke"                          # Managed Kubernetes
        ]
        
        # Medium-cost services
        medium_cost_patterns = [
            "rds", "aurora", "cosmosdb", "cloudformation",
            "azure-sql", "cloud-sql", "ec2", "vm"
        ]
        
        # Low-cost or free services
        low_cost_patterns = [
            "s3", "blob-storage", "cloud-storage",
            "prometheus", "grafana", "jenkins"
        ]
        
        if any(pattern in component_name for pattern in high_cost_patterns):
            return "high"
        elif any(pattern in component_name for pattern in medium_cost_patterns):
            return "medium"
        elif any(pattern in component_name for pattern in low_cost_patterns):
            return "low"
        else:
            return "unknown"
    
    def generate_optimization_recommendations(
        self, 
        components: List[InfrastructureComponent]
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on technology stack."""
        recommendations = []
        
        # Analyze for redundancies
        type_counts = {}
        for component in components:
            comp_type = f"{component.type.value}:{component.subtype}"
            if comp_type not in type_counts:
                type_counts[comp_type] = []
            type_counts[comp_type].append(component)
        
        # Check for multiple databases
        db_components = [c for c in components if c.type == InfrastructureType.DATABASE]
        if len(db_components) > 1:
            db_names = [c.name for c in db_components]
            recommendations.append({
                "type": "redundancy",
                "severity": "medium",
                "issue": f"Multiple database technologies detected: {', '.join(db_names)}",
                "recommendation": "Consider consolidating to a single database technology to reduce complexity and maintenance overhead",
                "components": db_names
            })
        
        # Check for monitoring overlap
        monitoring_components = [c for c in components if c.type == InfrastructureType.MONITORING]
        if len(monitoring_components) > 2:
            monitoring_names = [c.name for c in monitoring_components]
            recommendations.append({
                "type": "complexity",
                "severity": "low",
                "issue": f"Multiple monitoring tools detected: {', '.join(monitoring_names)}",
                "recommendation": "Consider consolidating monitoring tools to reduce operational complexity",
                "components": monitoring_names
            })
        
        # Check for missing monitoring
        if len(monitoring_components) == 0:
            recommendations.append({
                "type": "missing_capability",
                "severity": "high",
                "issue": "No monitoring tools detected",
                "recommendation": "Add monitoring capabilities (e.g., Prometheus, Grafana) for better observability",
                "components": []
            })
        
        return recommendations
    
    def generate_architecture_layers(self, stack_summary: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate architecture layers mapping."""
        layers = {layer: [] for layer in self.ARCHITECTURE_LAYERS.keys()}
        
        categories = stack_summary.get("categories", {})
        
        for category_name, items in categories.items():
            layer = self._determine_layer(category_name)
            layers[layer].extend(items)
        
        # Remove duplicates
        for layer in layers:
            layers[layer] = list(set(layers[layer]))
        
        return layers
    
    def detect_technology_patterns(self, stack_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect common technology patterns and stacks."""
        patterns = []
        categories = stack_summary.get("categories", {})
        
        # MEAN/MERN Stack detection
        has_mongodb = any("mongodb" in item.lower() for items in categories.values() for item in items)
        has_express = any("express" in item.lower() for items in categories.values() for item in items)
        has_react = any("react" in item.lower() for items in categories.values() for item in items)
        has_angular = any("angular" in item.lower() for items in categories.values() for item in items)
        has_node = any("node" in item.lower() for items in categories.values() for item in items)
        
        if has_mongodb and has_express:
            if has_react:
                patterns.append({
                    "pattern": "MERN Stack",
                    "confidence": 0.9,
                    "technologies": ["mongodb", "express", "react", "node"],
                    "description": "MongoDB, Express, React, Node.js stack"
                })
            elif has_angular:
                patterns.append({
                    "pattern": "MEAN Stack", 
                    "confidence": 0.9,
                    "technologies": ["mongodb", "express", "angular", "node"],
                    "description": "MongoDB, Express, Angular, Node.js stack"
                })
        
        # Microservices pattern detection
        has_kubernetes = any("kubernetes" in item.lower() for items in categories.values() for item in items)
        has_docker = any("docker" in item.lower() for items in categories.values() for item in items)
        has_messaging = any(item for item in categories.get("messaging", []))
        
        if has_kubernetes or (has_docker and has_messaging):
            patterns.append({
                "pattern": "Microservices Architecture",
                "confidence": 0.8,
                "technologies": ["kubernetes", "docker"] + categories.get("messaging", []),
                "description": "Container-based microservices architecture"
            })
        
        return patterns
    
    def export_diagram_json(self, diagram_data: Dict[str, Any], output_path: Path) -> None:
        """Export diagram data to JSON file."""
        logger.info(f"Exporting diagram data to {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(diagram_data, f, indent=2, ensure_ascii=False)
    
    def generate_mermaid_diagram(self, diagram_data: Dict[str, Any]) -> str:
        """Generate Mermaid diagram syntax from diagram data."""
        logger.info("Generating Mermaid diagram syntax")
        
        mermaid_lines = ["graph TD"]
        
        # Add nodes
        for node in diagram_data.get("nodes", []):
            node_id = node["id"]
            node_name = node["name"]
            category = node.get("category", "")
            
            # Style nodes based on category
            if "frontend" in category:
                mermaid_lines.append(f'    {node_id}["{node_name}"]:::frontend')
            elif "backend" in category:
                mermaid_lines.append(f'    {node_id}["{node_name}"]:::backend')
            elif "database" in category:
                mermaid_lines.append(f'    {node_id}["{node_name}"]:::database')
            else:
                mermaid_lines.append(f'    {node_id}["{node_name}"]')
        
        # Add edges
        for edge in diagram_data.get("edges", []):
            source = edge["source"]
            target = edge["target"]
            relationship = edge.get("relationship", "")
            
            if relationship:
                mermaid_lines.append(f'    {source} --> {target}')
            else:
                mermaid_lines.append(f'    {source} --> {target}')
        
        # Add styles
        mermaid_lines.extend([
            "",
            "    classDef frontend fill:#e1f5fe",
            "    classDef backend fill:#f3e5f5", 
            "    classDef database fill:#e8f5e8"
        ])
        
        return "\n".join(mermaid_lines)
    
    def _determine_layer(self, category_name: str) -> str:
        """Determine architecture layer for a category."""
        for layer, layer_categories in self.ARCHITECTURE_LAYERS.items():
            if any(cat in category_name for cat in layer_categories):
                return layer
        return "infrastructure"  # Default layer
    
    def _estimate_category_cost(self, category_name: str) -> str:
        """Estimate cost tier for a category."""
        high_cost_categories = ["monitoring", "cloud_services", "ml_ai"]
        medium_cost_categories = ["databases", "messaging", "orchestration"]
        
        if category_name in high_cost_categories:
            return "high"
        elif category_name in medium_cost_categories:
            return "medium"
        else:
            return "low"
    
    def _generate_relationships(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate relationships between nodes."""
        edges = []
        
        # Create simple relationships based on common patterns
        frontend_nodes = [n for n in nodes if "frontend" in n["category"]]
        backend_nodes = [n for n in nodes if "backend" in n["category"]]
        database_nodes = [n for n in nodes if "database" in n["category"]]
        
        # Frontend -> Backend relationships
        for frontend in frontend_nodes:
            for backend in backend_nodes:
                edges.append({
                    "source": frontend["id"],
                    "target": backend["id"],
                    "relationship": "calls"
                })
        
        # Backend -> Database relationships
        for backend in backend_nodes:
            for database in database_nodes:
                edges.append({
                    "source": backend["id"],
                    "target": database["id"],
                    "relationship": "queries"
                })
        
        return edges
    
    def _calculate_complexity_score(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> float:
        """Calculate complexity score for the technology stack."""
        # Simple complexity metric based on number of nodes and edges
        node_count = len(nodes)
        edge_count = len(edges)
        
        # Base complexity on technology count
        base_score = min(node_count / 10.0, 1.0)  # Normalize to 0-1
        
        # Add complexity for interconnections
        if node_count > 0:
            connection_ratio = edge_count / node_count
            complexity_score = base_score + (connection_ratio * 0.5)
        else:
            complexity_score = 0.0
        
        return min(complexity_score, 1.0)  # Cap at 1.0