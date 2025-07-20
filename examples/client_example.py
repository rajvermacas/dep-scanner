#!/usr/bin/env python3
"""Example usage of the Dependency Scanner Client."""

import os
import json
from dotenv import load_dotenv

from dependency_scanner_tool.client import DependencyScannerClient

# Load environment variables
load_dotenv()

def main():
    """Main example function."""
    # Configuration
    server_url = os.getenv('SCANNER_SERVER_URL', 'http://localhost:8000')
    username = os.getenv('API_USERNAME', 'admin')
    password = os.getenv('API_PASSWORD', 'secure_password_change_me')
    
    print("🔍 Dependency Scanner Client Example")
    print("=" * 50)
    
    try:
        # Initialize client
        print(f"Connecting to server: {server_url}")
        client = DependencyScannerClient(
            base_url=server_url,
            username=username,
            password=password
        )
        
        # Health check
        print("Checking server health...")
        health = client.health_check()
        print(f"✅ Server is healthy (version: {health.get('version')})")
        
        # Example repository to scan
        git_url = "https://github.com/rajvermacas/airflow.git"
        print(f"\nScanning repository: {git_url}")
        
        # Submit scan and wait for completion
        job_id, results = client.scan_repository_and_wait(
            git_url=git_url,
            max_wait=600,  # 10 minutes
            show_progress=True
        )
        
        print("\n" + "=" * 50)
        print("📋 SCAN RESULTS")
        print("=" * 50)
        print(f"Job ID: {job_id}")
        print(f"Repository: {results.git_url}")
        print("\nDependency Categories Found:")
        
        for category, has_deps in results.dependencies.items():
            status = "✅ Yes" if has_deps else "❌ No"
            print(f"  {category}: {status}")
        
        # Save results to file
        output_file = "scan_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "job_id": job_id,
                "git_url": results.git_url,
                "dependencies": results.dependencies
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print("🎉 Example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())