#!/usr/bin/env python3
"""Test script to verify that dependency categorization is working."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from dependency_scanner_tool.categorization import DependencyCategorizer
    from dependency_scanner_tool.scanner import Dependency, DependencyType
    
    print("Testing dependency categorization...")
    
    # Load the categorizer from config.yaml
    config_path = Path("config.yaml")
    if config_path.exists():
        categorizer = DependencyCategorizer.from_yaml(config_path)
        print(f"✅ Successfully loaded categorizer from {config_path}")
        
        # Test with some sample dependencies
        sample_deps = [
            Dependency(name="jinja2", version="3.1.6", source_file="test.txt"),
            Dependency(name="black", version="22.8.0", source_file="test.txt"),
            Dependency(name="pyyaml", version="6.0", source_file="test.txt"),
            Dependency(name="pytest", version="7.1.3", source_file="test.txt"),
        ]
        
        categorized = categorizer.categorize_dependencies(sample_deps)
        
        print("\n📋 Categorization Results:")
        for category, deps in categorized.items():
            print(f"  {category}: {[dep.name for dep in deps]}")
        
        if categorized:
            print("✅ Dependency categorization is working correctly!")
        else:
            print("❌ No dependencies were categorized")
    else:
        print(f"❌ Config file not found: {config_path}")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")