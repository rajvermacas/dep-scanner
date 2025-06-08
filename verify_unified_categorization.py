#!/usr/bin/env python3
"""Verify that unified categorization works for both dependencies and API calls."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from dependency_scanner_tool.categorization import DependencyCategorizer
    from dependency_scanner_tool.scanner import Dependency, DependencyType, ScanResult
    from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiAuthType
    from dependency_scanner_tool.reporters.json_reporter import JSONReporter
    
    print("Testing unified categorization for dependencies and API calls...")
    
    # Create sample data
    sample_deps = [
        Dependency(name="jinja2", version="3.1.6", source_file="test.txt"),
        Dependency(name="black", version="22.8.0", source_file="test.txt"),
        Dependency(name="pyyaml", version="6.0", source_file="test.txt"),
    ]
    
    sample_api_calls = [
        ApiCall(
            url="https://api.github.com/user",
            http_method="GET",
            source_file="test.py",
            line_number=10,
            auth_type=ApiAuthType.BASIC
        ),
        ApiCall(
            url="https://api.openweathermap.org/data/2.5/weather",
            http_method="GET", 
            source_file="test.py",
            line_number=20,
            auth_type=ApiAuthType.UNKNOWN
        )
    ]
    
    # Simulate categorized API calls (this would normally come from API categorization)
    categorized_api_calls = {
        "Web Frameworks": [sample_api_calls[0]],
        "Data Science": [sample_api_calls[1]]
    }
    
    # Create a mock scan result with categorized API calls
    scan_result = ScanResult(
        languages={"Python": 100.0},
        package_managers={"pip"},
        dependency_files=[Path("test.txt")],
        dependencies=sample_deps,
        api_calls=sample_api_calls,
        errors=[]
    )
    scan_result.categorized_api_calls = categorized_api_calls
    
    # Create JSONReporter with category config
    config_path = Path("config.yaml")
    reporter = JSONReporter(category_config=config_path)
    
    # Generate the data structure (this is what would go to the HTML template)
    data = reporter._convert_to_dict(scan_result)
    
    print("\n📊 Unified Categories Generated:")
    unified_categories = data.get('unified_categories', {})
    
    for category, items in unified_categories.items():
        print(f"\n🏷️  {category}:")
        
        deps = items.get('dependencies', [])
        if deps:
            print(f"  📦 Dependencies ({len(deps)}):")
            for dep in deps:
                print(f"    - {dep['name']} ({dep['version']})")
        else:
            print(f"  📦 Dependencies: None")
            
        api_calls = items.get('api_calls', [])
        if api_calls:
            print(f"  🌐 API Calls ({len(api_calls)}):")
            for api in api_calls:
                print(f"    - {api['url']} ({api['http_method']})")
        else:
            print(f"  🌐 API Calls: None")
    
    # Verify the fix
    has_deps_in_categories = any(
        items.get('dependencies') for items in unified_categories.values()
    )
    has_apis_in_categories = any(
        items.get('api_calls') for items in unified_categories.values()
    )
    
    print(f"\n🔍 Verification Results:")
    print(f"  ✅ Dependencies in categories: {has_deps_in_categories}")
    print(f"  ✅ API calls in categories: {has_apis_in_categories}")
    
    if has_deps_in_categories and has_apis_in_categories:
        print("\n🎉 SUCCESS: Both dependencies and API calls are properly categorized!")
        print("   The HTML report will now show both types in the 'Categorized Dependencies and API Calls' section.")
    else:
        print("\n❌ ISSUE: Missing categorization for one or both types")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()