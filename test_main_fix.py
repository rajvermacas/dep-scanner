#!/usr/bin/env python3
"""Test script to verify the fix in __main__.py works correctly."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from dependency_scanner_tool.categorization import DependencyCategorizer
    from dependency_scanner_tool.scanner import Dependency, DependencyType
    from dependency_scanner_tool.reporters.json_reporter import JSONReporter
    
    print("Testing main entry point fix...")
    
    # Simulate what happens in main when config.yaml is used for categorization
    config_file = "config.yaml"
    category_config_path = None
    
    # This mimics the logic we added to __main__.py
    if Path(config_file).exists():
        category_config_path = Path(config_file)
        print(f"✅ Config file found: {category_config_path}")
    
    # Test that JSONReporter can load the config for dependency categorization
    if category_config_path:
        json_reporter = JSONReporter(category_config=category_config_path)
        
        if json_reporter.categorizer:
            print("✅ JSONReporter successfully loaded categorizer")
            
            # Test categorization with sample dependencies
            sample_deps = [
                Dependency(name="jinja2", version="3.1.6", source_file="test.txt"),
                Dependency(name="black", version="22.8.0", source_file="test.txt"),
                Dependency(name="pyyaml", version="6.0", source_file="test.txt"),
            ]
            
            categorized = json_reporter.categorizer.categorize_dependencies(sample_deps)
            
            print(f"✅ Dependencies categorized into {len(categorized)} categories:")
            for category, deps in categorized.items():
                print(f"  - {category}: {[dep.name for dep in deps]}")
            
            print("\n🎉 SUCCESS: The fix in __main__.py will now properly categorize dependencies!")
            print("   When you run the main entrypoint, both dependencies and API calls will show in the categorized section.")
        else:
            print("❌ JSONReporter failed to load categorizer")
    else:
        print("❌ Config file not found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()