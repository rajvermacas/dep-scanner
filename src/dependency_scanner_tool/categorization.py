"""Module for categorizing dependencies based on configurable groups."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from dependency_scanner_tool.scanner import Dependency
from dependency_scanner_tool.normalizers.python_package import is_package_match
from dependency_scanner_tool.normalizers.java_package import JavaPackageNormalizer

logger = logging.getLogger(__name__)


class DependencyCategorizer:
    """Categorizes dependencies into configurable groups."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the dependency categorizer.
        
        Args:
            config: Configuration dictionary containing category definitions.
                   Expected format: {"categories": {"A": {"dependencies": ["dep1", "dep2"]}, "B": {"dependencies": ["dep3"]}}}
                   Or legacy format: {"categories": {"A": ["dep1", "dep2"], "B": ["dep3"]}}
        """
        self.categories = {}
        self.java_normalizer = JavaPackageNormalizer()
        
        if config and "categories" in config:
            # Handle new unified structure with dependencies and api_patterns
            for category_name, category_data in config["categories"].items():
                if isinstance(category_data, dict) and "dependencies" in category_data:
                    # New unified structure
                    self.categories[category_name] = category_data["dependencies"]
                elif isinstance(category_data, list):
                    # Legacy structure - direct list of dependencies
                    self.categories[category_name] = category_data
                else:
                    logger.warning(f"Skipping invalid category format for '{category_name}'")
            
            logger.info(f"Initialized dependency categorizer with {len(self.categories)} categories")
        else:
            logger.info("Initialized dependency categorizer with no categories")
    
    @classmethod
    def from_json(cls, json_path: Path) -> 'DependencyCategorizer':
        """Create a DependencyCategorizer from a JSON configuration file.
        
        Args:
            json_path: Path to the JSON configuration file
            
        Returns:
            Initialized DependencyCategorizer
            
        Raises:
            FileNotFoundError: If the JSON file does not exist
            json.JSONDecodeError: If the JSON file is invalid
        """
        logger.info(f"Loading dependency categorization config from {json_path}")
        
        try:
            with open(json_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Successfully loaded categorization config from {json_path}")
                return cls(config)
        except FileNotFoundError:
            logger.error(f"Categorization config file not found: {json_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in categorization config file: {e}")
            raise
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'DependencyCategorizer':
        """Create a DependencyCategorizer from a YAML configuration file.
        
        Args:
            yaml_path: Path to the YAML configuration file
            
        Returns:
            Initialized DependencyCategorizer
            
        Raises:
            FileNotFoundError: If the YAML file does not exist
            yaml.YAMLError: If the YAML file is invalid
        """
        import yaml
        
        logger.info(f"Loading dependency categorization config from {yaml_path}")
        
        try:
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Successfully loaded categorization config from {yaml_path}")
                return cls(config)
        except FileNotFoundError:
            logger.error(f"Categorization config file not found: {yaml_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in categorization config file: {e}")
            raise
    
    def categorize_dependency(self, dependency: Dependency) -> List[str]:
        """Categorize a dependency based on the configured categories.
        
        Args:
            dependency: Dependency to categorize
            
        Returns:
            List of category names the dependency belongs to, or ["Uncategorized"] if none
        """
        matching_categories = []
        
        for category, deps in self.categories.items():
            # Direct match
            if dependency.name in deps:
                matching_categories.append(category)
                continue
            
            # Check for Python package name variations
            if ":" not in dependency.name:  # Python packages don't use colons
                for dep_name in deps:
                    if ":" not in dep_name and is_package_match(dependency.name, dep_name):
                        matching_categories.append(category)
                        break
            
            # Check for Java package name variations
            if ":" in dependency.name:  # Java packages use Maven coordinates with colons
                package_name = self.java_normalizer.get_package_from_maven_coordinates(dependency.name)
                
                for dep_name in deps:
                    if ":" in dep_name:  # Only compare with Maven coordinates
                        dep_package = self.java_normalizer.get_package_from_maven_coordinates(dep_name)
                        if package_name.startswith(dep_package):
                            matching_categories.append(category)
                            break
        
        return matching_categories if matching_categories else ["Uncategorized"]
    
    def categorize_dependencies(self, dependencies: List[Dependency]) -> Dict[str, List[Dependency]]:
        """Categorize multiple dependencies.
        
        Args:
            dependencies: List of dependencies to categorize
            
        Returns:
            Dictionary mapping category names to lists of dependencies
        """
        categorized = {}
        
        for dep in dependencies:
            categories = self.categorize_dependency(dep)
            
            for category in categories:
                if category not in categorized:
                    categorized[category] = []
                
                categorized[category].append(dep)
        
        logger.info(f"Categorized {len(dependencies)} dependencies into {len(categorized)} categories")
        return categorized
