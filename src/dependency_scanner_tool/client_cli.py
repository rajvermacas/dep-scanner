#!/usr/bin/env python3
"""Command-line interface for the Dependency Scanner Client."""

import os
import sys
import json
import csv
from typing import Optional
import click
from dotenv import load_dotenv

from dependency_scanner_tool.client import DependencyScannerClient

# Load environment variables
load_dotenv()


def generate_csv_data(url: str, results) -> list:
    """Generate CSV data from scan results.
    
    Args:
        url: The GitLab group URL or project URL provided by user
        results: ScanResultResponse object
        
    Returns:
        List of dictionaries ready for CSV writing
    """
    csv_data = []
    
    if results.scan_type == "group":
        # For group scans: aggregate dependencies across all projects
        # For each dependency category, check if ANY project has it
        all_dependencies = set()
        all_infrastructure = set()
        if results.project_results:
            for project in results.project_results:
                all_dependencies.update(project.dependencies.keys())
                if hasattr(project, 'infrastructure_usage') and project.infrastructure_usage:
                    all_infrastructure.update(project.infrastructure_usage.keys())
        
        # Check each dependency category
        for dep_category in all_dependencies:
            has_dependency = False
            # If ANY project in the group has this dependency, mark as True
            if results.project_results:
                for project in results.project_results:
                    if project.dependencies.get(dep_category, False):
                        has_dependency = True
                        break
            
            csv_data.append({
                'GitLab Group URL or Project URL': url,
                'Dependency': dep_category,
                'Status': has_dependency
            })
        
        # Check each infrastructure usage category
        for infra_type in all_infrastructure:
            has_infra = False
            # If ANY project in the group has this infrastructure, mark as True
            if results.project_results:
                for project in results.project_results:
                    if (hasattr(project, 'infrastructure_usage') and 
                        project.infrastructure_usage and 
                        project.infrastructure_usage.get(infra_type, False)):
                        has_infra = True
                        break
            
            csv_data.append({
                'GitLab Group URL or Project URL': url,
                'Dependency': infra_type,
                'Status': has_infra
            })
    else:
        # For single repository scans: use direct dependency results
        for dep_category, has_dependency in results.dependencies.items():
            csv_data.append({
                'GitLab Group URL or Project URL': url,
                'Dependency': dep_category,
                'Status': has_dependency
            })
        
        # Add infrastructure usage for single repository scans
        if hasattr(results, 'infrastructure_usage') and results.infrastructure_usage:
            for infra_type, has_infra in results.infrastructure_usage.items():
                csv_data.append({
                    'GitLab Group URL or Project URL': url,
                    'Dependency': infra_type,
                    'Status': has_infra
                })
    
    return csv_data


@click.group()
@click.option(
    '--server', 
    default='http://localhost:8000',
    help='API server URL (default: http://localhost:8000)',
    envvar='SCANNER_SERVER_URL'
)
@click.option(
    '--username',
    help='API username for authentication',
    envvar='API_USERNAME'
)
@click.option(
    '--password',
    help='API password for authentication', 
    envvar='API_PASSWORD'
)
@click.option('--timeout', default=30, help='Request timeout in seconds')
@click.option('--poll-interval', default=5, help='Polling interval for job status')
@click.pass_context
def cli(ctx, server, username, password, timeout, poll_interval):
    """Dependency Scanner API Client CLI."""
    
    # Ensure we have credentials
    if not username:
        username = click.prompt('API Username', type=str)
    if not password:
        password = click.prompt('API Password', type=str, hide_input=True)
    
    # Initialize client
    try:
        client = DependencyScannerClient(
            base_url=server,
            username=username,
            password=password,
            timeout=timeout,
            poll_interval=poll_interval
        )
        ctx.obj = client
    except Exception as e:
        click.echo(f"Error: Failed to connect to API server: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_obj
def health(client):
    """Check API server health."""
    try:
        response = client.health_check()
        click.echo("✅ Server is healthy")
        click.echo(f"Status: {response.get('status')}")
        click.echo(f"Version: {response.get('version')}")
        click.echo(f"User: {response.get('user')}")
        click.echo(f"Timestamp: {response.get('timestamp')}")
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('url')
@click.option('--wait/--no-wait', default=True, help='Wait for scan completion')
@click.option('--max-wait', default=600, help='Maximum wait time in seconds')
@click.option('--json-output', help='Save results to JSON file')
@click.option('--csv-output', help='Save results to CSV file')
@click.pass_obj
def scan(client, url, wait, max_wait, json_output, csv_output):
    """Submit a repository or GitLab group for scanning."""
    try:
        if wait:
            # Submit and wait for completion
            job_id, results = client.scan_repository_and_wait(
                git_url=url,
                max_wait=max_wait,
                show_progress=True
            )
            
            click.echo("\n" + "="*50)
            click.echo("SCAN RESULTS")
            click.echo("="*50)
            click.echo(f"Job ID: {job_id}")
            click.echo(f"URL: {results.git_url}")
            
            # Display results based on scan type
            if results.scan_type == "group":
                click.echo(f"Type: GitLab Group Scan")
                click.echo(f"Total Projects: {results.total_projects}")
                click.echo(f"Successful Scans: {results.successful_scans}")
                click.echo(f"Failed Scans: {results.failed_scans}")
            else:
                click.echo(f"Type: Single Repository Scan")
            
            click.echo("\nDependency Categories:")
            for category, has_deps in results.dependencies.items():
                status = "✅ Found" if has_deps else "❌ None"
                click.echo(f"  {category}: {status}")
            
            # Show infrastructure usage if available
            if hasattr(results, 'infrastructure_usage') and results.infrastructure_usage:
                click.echo("\nInfrastructure Usage:")
                for infra_type, has_infra in results.infrastructure_usage.items():
                    status = "✅ Found" if has_infra else "❌ None"
                    click.echo(f"  {infra_type}: {status}")
            
            # Save to JSON if requested
            if json_output:
                output_data = {
                    "job_id": job_id,
                    "scan_type": results.scan_type,
                    "git_url": results.git_url,
                    "dependencies": results.dependencies
                }
                if hasattr(results, 'infrastructure_usage') and results.infrastructure_usage:
                    output_data["infrastructure_usage"] = results.infrastructure_usage
                if results.scan_type == "group":
                    output_data.update({
                        "total_projects": results.total_projects,
                        "successful_scans": results.successful_scans,
                        "failed_scans": results.failed_scans,
                        "project_results": [r.model_dump() for r in results.project_results] if results.project_results else [],
                        "failed_projects": results.failed_projects
                    })
                
                with open(json_output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                click.echo(f"\nResults saved to: {json_output}")
            
            # Save to CSV if requested
            if csv_output:
                csv_data = generate_csv_data(url, results)
                with open(csv_output, 'w', newline='') as f:
                    if csv_data:
                        fieldnames = ['GitLab Group URL or Project URL', 'Dependency', 'Status']
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(csv_data)
                    else:
                        # Write empty CSV with headers if no data
                        fieldnames = ['GitLab Group URL or Project URL', 'Dependency', 'Status']
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                click.echo(f"CSV results saved to: {csv_output}")
        else:
            # Just submit the scan
            response = client.submit_scan(url)
            click.echo(f"✅ Scan submitted successfully")
            click.echo(f"Job ID: {response.job_id}")
            click.echo(f"Status: {response.status.value}")
            click.echo(f"Created: {response.created_at}")
            click.echo(f"\nUse 'scanner-client status {response.job_id}' to check progress")
        
    except Exception as e:
        click.echo(f"❌ Scan failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.pass_obj
def status(client, job_id):
    """Get job status."""
    try:
        response = client.get_job_status(job_id)
        click.echo(f"Job ID: {response.job_id}")
        click.echo(f"Status: {response.status.value}")
        click.echo(f"Progress: {response.progress}%")
        click.echo(f"Created: {response.created_at}")
        if response.completed_at:
            click.echo(f"Completed: {response.completed_at}")
    except Exception as e:
        click.echo(f"❌ Failed to get job status: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.option('--json-output', help='Save results to JSON file')
@click.option('--csv-output', help='Save results to CSV file')
@click.pass_obj
def results(client, job_id, json_output, csv_output):
    """Get job results."""
    try:
        response = client.get_job_results(job_id)
        
        click.echo("="*50)
        click.echo("SCAN RESULTS")
        click.echo("="*50)
        click.echo(f"Repository: {response.git_url}")
        click.echo("\nDependency Categories:")
        
        for category, has_deps in response.dependencies.items():
            status = "✅ Found" if has_deps else "❌ None"
            click.echo(f"  {category}: {status}")
        
        # Show infrastructure usage if available
        if hasattr(response, 'infrastructure_usage') and response.infrastructure_usage:
            click.echo("\nInfrastructure Usage:")
            for infra_type, has_infra in response.infrastructure_usage.items():
                status = "✅ Found" if has_infra else "❌ None"
                click.echo(f"  {infra_type}: {status}")
        
        # Save to JSON if requested
        if json_output:
            output_data = {
                "git_url": response.git_url,
                "dependencies": response.dependencies
            }
            if hasattr(response, 'infrastructure_usage') and response.infrastructure_usage:
                output_data["infrastructure_usage"] = response.infrastructure_usage
            with open(json_output, 'w') as f:
                json.dump(output_data, f, indent=2)
            click.echo(f"\nResults saved to: {json_output}")
        
        # Save to CSV if requested
        if csv_output:
            csv_data = generate_csv_data(response.git_url, response)
            with open(csv_output, 'w', newline='') as f:
                if csv_data:
                    fieldnames = ['GitLab Group URL or Project URL', 'Dependency', 'Status']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
                else:
                    # Write empty CSV with headers if no data
                    fieldnames = ['GitLab Group URL or Project URL', 'Dependency', 'Status']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
            click.echo(f"CSV results saved to: {csv_output}")
            
    except Exception as e:
        click.echo(f"❌ Failed to get results: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('job_id')
@click.option('--max-wait', default=600, help='Maximum wait time in seconds')
@click.pass_obj
def wait(client, job_id, max_wait):
    """Wait for job completion."""
    try:
        click.echo(f"Waiting for job {job_id} to complete...")
        final_status, results = client.wait_for_completion(
            job_id=job_id,
            max_wait=max_wait,
            show_progress=True
        )
        
        if results:
            click.echo("\n" + "="*50)
            click.echo("SCAN COMPLETED")
            click.echo("="*50)
            click.echo(f"Repository: {results.git_url}")
            click.echo("\nDependency Categories:")
            
            for category, has_deps in results.dependencies.items():
                status = "✅ Found" if has_deps else "❌ None"
                click.echo(f"  {category}: {status}")
            
            # Show infrastructure usage if available
            if hasattr(results, 'infrastructure_usage') and results.infrastructure_usage:
                click.echo("\nInfrastructure Usage:")
                for infra_type, has_infra in results.infrastructure_usage.items():
                    status = "✅ Found" if has_infra else "❌ None"
                    click.echo(f"  {infra_type}: {status}")
        else:
            click.echo(f"❌ Job completed with status: {final_status.status.value}")
            
    except Exception as e:
        click.echo(f"❌ Wait failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--page', default=1, help='Page number')
@click.option('--per-page', default=10, help='Jobs per page')
@click.option('--status-filter', help='Filter by status (pending, running, completed, failed)')
@click.pass_obj
def list_jobs(client, page, per_page, status_filter):
    """List jobs."""
    try:
        response = client.list_jobs(
            page=page,
            per_page=per_page,
            status=status_filter
        )
        
        click.echo(f"Jobs (Page {response.page} of {response.total_pages}, Total: {response.total})")
        click.echo("="*80)
        
        for job in response.jobs:
            click.echo(f"ID: {job.job_id}")
            click.echo(f"URL: {job.git_url}")
            click.echo(f"Status: {job.status.value} ({job.progress}%)")
            click.echo(f"Created: {job.created_at}")
            if job.completed_at:
                click.echo(f"Completed: {job.completed_at}")
            if job.error_message:
                click.echo(f"Error: {job.error_message}")
            click.echo("-" * 80)
            
    except Exception as e:
        click.echo(f"❌ Failed to list jobs: {e}", err=True)
        sys.exit(1)




@cli.command()
@click.argument('git_url', default='https://github.com/rajvermacas/airflow.git')
@click.option('--json-output', default='airflow_scan_results.json', help='Output file for results')
@click.pass_obj
def demo(client, git_url, json_output):
    """Demo: Scan the Airflow repository."""
    click.echo("🚀 DEMO: Scanning Apache Airflow Repository")
    click.echo("="*60)
    click.echo(f"Repository: {git_url}")
    click.echo("="*60)
    
    try:
        job_id, results = client.scan_repository_and_wait(
            git_url=git_url,
            max_wait=900,  # 15 minutes for large repo
            show_progress=True
        )
        
        click.echo("\n" + "="*60)
        click.echo("✅ DEMO COMPLETED SUCCESSFULLY")
        click.echo("="*60)
        click.echo(f"Job ID: {job_id}")
        click.echo(f"Repository: {results.git_url}")
        click.echo("\nDependency Analysis Results:")
        
        for category, has_deps in results.dependencies.items():
            status = "✅ Found" if has_deps else "❌ None"
            click.echo(f"  📦 {category}: {status}")
        
        # Show infrastructure usage if available
        if hasattr(results, 'infrastructure_usage') and results.infrastructure_usage:
            click.echo("\nInfrastructure Usage:")
            for infra_type, has_infra in results.infrastructure_usage.items():
                status = "✅ Found" if has_infra else "❌ None"
                click.echo(f"  🏗️ {infra_type}: {status}")
        
        # Save detailed results
        output_data = {
            "demo_info": {
                "repository": git_url,
                "job_id": job_id,
                "scan_completed": True
            },
            "results": {
                "git_url": results.git_url,
                "dependencies": results.dependencies
            }
        }
        if hasattr(results, 'infrastructure_usage') and results.infrastructure_usage:
            output_data["results"]["infrastructure_usage"] = results.infrastructure_usage
        
        with open(json_output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        click.echo(f"\n📄 Detailed results saved to: {json_output}")
        click.echo("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        click.echo(f"❌ Demo failed: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()