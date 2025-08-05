#!/usr/bin/env python3
"""Command-line interface for the Dependency Scanner Client."""

import os
import sys
import json
from typing import Optional
import click
from dotenv import load_dotenv

from dependency_scanner_tool.client import DependencyScannerClient

# Load environment variables
load_dotenv()


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
@click.pass_obj
def scan(client, url, wait, max_wait, json_output):
    """Submit a repository or group for scanning."""
    from dependency_scanner_tool.api.gitlab_service import gitlab_service

    try:
        if gitlab_service.is_gitlab_group_url(url):
            # Handle GitLab group
            click.echo(f"Scanning GitLab group: {url}")
            git_urls = gitlab_service.get_project_git_urls(url)
            results = []

            for git_url in git_urls:
                job_id, scan_result = client.scan_repository_and_wait(
                    git_url=git_url,
                    max_wait=max_wait,
                    show_progress=True
                )
                results.append((job_id, scan_result))
            
            # Combine the results for group-level reporting
            group_dependencies = {}
            for _, scan_result in results:
                for category, has_deps in scan_result.dependencies.items():
                    if category not in group_dependencies:
                        group_dependencies[category] = has_deps
                    else:
                        group_dependencies[category] = group_dependencies[category] or has_deps

            click.echo("\n" + "="*50)
            click.echo("SCAN RESULTS")
            click.echo("="*50)
            click.echo(f"Group: {url}")
            click.echo("\nDependency Categories:")

            for category, has_deps in group_dependencies.items():
                status = "✅ Found" if has_deps else "❌ None"
                click.echo(f"  {category}: {status}")

            # Save to JSON if requested
            if json_output:
                output_data = {
                    "group_url": url,
                    "dependencies": group_dependencies
                }
                with open(json_output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                click.echo(f"\nResults saved to: {json_output}")

        else:
            # Handle single repository
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
                click.echo(f"Repository: {results.git_url}")
                click.echo("\nDependency Categories:")
                
                for category, has_deps in results.dependencies.items():
                    status = "✅ Found" if has_deps else "❌ None"
                    click.echo(f"  {category}: {status}")
                
                # Save to JSON if requested
                if json_output:
                    output_data = {
                        "job_id": job_id,
                        "git_url": results.git_url,
                        "dependencies": results.dependencies
                    }
                    with open(json_output, 'w') as f:
                        json.dump(output_data, f, indent=2)
                    click.echo(f"\nResults saved to: {json_output}")
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
@click.pass_obj
def results(client, job_id, json_output):
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
        
        # Save to JSON if requested
        if json_output:
            output_data = {
                "git_url": response.git_url,
                "dependencies": response.dependencies
            }
            with open(json_output, 'w') as f:
                json.dump(output_data, f, indent=2)
            click.echo(f"\nResults saved to: {json_output}")
            
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
@click.argument('group_url')
@click.option('--max-wait', default=600, help='Maximum wait time per repository in seconds')
@click.option('--json-output', help='Save results to JSON file')
@click.option('--csv-output', help='Save results to CSV file')
@click.option('--gitlab-token', help='GitLab access token for private groups', envvar='GITLAB_TOKEN')
@click.pass_obj
def group_scan(client, group_url, max_wait, json_output, csv_output, gitlab_token):
    """
    Scan all repositories in a GitLab group.

    Args:
        client: The DependencyScannerClient object.
        group_url (str): The URL of the GitLab group to scan.
        max_wait (int): Maximum wait time per repository in seconds.
        json_output (str): Path to save the detailed results in JSON format.
        csv_output (str): Path to save the summary results in CSV format.
        gitlab_token (str): GitLab access token for private groups.
    """
    from dependency_scanner_tool.api.gitlab_service import GitLabGroupService
    
    click.echo(f"🔍 GITLAB GROUP SCAN")
    click.echo("="*60)
    click.echo(f"Group: {group_url}")
    click.echo("="*60)
    
    try:
        # Initialize GitLab service with optional token
        gitlab_service = GitLabGroupService(access_token=gitlab_token)
        
        # Verify it's a GitLab group URL
        if not gitlab_service.is_gitlab_group_url(group_url):
            click.echo(f"❌ Invalid GitLab group URL: {group_url}", err=True)
            click.echo("Expected format: https://gitlab.com/group-name", err=True)
            sys.exit(1)
        
        # Get project information
        click.echo("Fetching group projects...")
        project_info = gitlab_service.get_project_info(group_url)
        
        if not project_info:
            click.echo("❌ No projects found in the group", err=True)
            sys.exit(1)
        
        click.echo(f"Found {len(project_info)} projects in the group:\n")
        for i, project in enumerate(project_info, 1):
            click.echo(f"  {i}. {project['name']} ({project['path']})")
        
        click.echo(f"\nStarting dependency scan for {len(project_info)} projects...")
        
        # Scan each project
        results = []
        group_dependencies = {}
        failed_projects = []
        
        for i, project in enumerate(project_info, 1):
            project_name = project['name']
            git_url = project['git_url']
            
            click.echo(f"\n[{i}/{len(project_info)}] Scanning: {project_name}")
            click.echo(f"Repository: {git_url}")
            
            try:
                job_id, scan_result = client.scan_repository_and_wait(
                    git_url=git_url,
                    max_wait=max_wait,
                    show_progress=True
                )
                
                results.append({
                    'project_name': project_name,
                    'git_url': git_url,
                    'job_id': job_id,
                    'dependencies': scan_result.dependencies,
                    'status': 'success'
                })
                
                # Aggregate dependencies (OR logic: if any project has it, mark as present)
                for category, has_deps in scan_result.dependencies.items():
                    if category not in group_dependencies:
                        group_dependencies[category] = has_deps
                    else:
                        group_dependencies[category] = group_dependencies[category] or has_deps
                
                click.echo(f"✅ {project_name} scan completed")
                
            except Exception as e:
                click.echo(f"❌ {project_name} scan failed: {e}")
                failed_projects.append({
                    'project_name': project_name,
                    'git_url': git_url,
                    'error': str(e)
                })
                results.append({
                    'project_name': project_name,
                    'git_url': git_url,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Display group-level results
        click.echo("\n" + "="*60)
        click.echo("📋 GROUP SCAN RESULTS")
        click.echo("="*60)
        click.echo(f"Group: {group_url}")
        click.echo(f"Total Projects: {len(project_info)}")
        click.echo(f"Successfully Scanned: {len(results) - len(failed_projects)}")
        click.echo(f"Failed: {len(failed_projects)}")
        
        if failed_projects:
            click.echo("\n❌ Failed Projects:")
            for failed in failed_projects:
                click.echo(f"  - {failed['project_name']}: {failed['error']}")
        
        click.echo("\n📦 Group-Level Dependencies:")
        for category, has_deps in group_dependencies.items():
            status = "✅ Present" if has_deps else "❌ Absent"
            click.echo(f"  {category}: {status}")
        
        # Save detailed results to JSON
        if json_output:
            output_data = {
                "group_url": group_url,
                "scan_summary": {
                    "total_projects": len(project_info),
                    "successful_scans": len(results) - len(failed_projects),
                    "failed_scans": len(failed_projects)
                },
                "group_dependencies": group_dependencies,
                "project_results": results,
                "failed_projects": failed_projects
            }
            try:
                with open(json_output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                click.echo(f"\n💾 Detailed results saved to: {json_output}")
            except IOError as e:
                click.echo(f"\n❌ Error saving JSON file: {e}", err=True)

        # Save detailed results to CSV
        if csv_output:
            import csv
            header = ['group_url', 'dependency_category', 'dependency_status']
            try:
                with open(csv_output, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    for category, has_deps in group_dependencies.items():
                        row = [
                            group_url,
                            category,
                            has_deps
                        ]
                        writer.writerow(row)
                click.echo(f"\n💾 Detailed results saved to: {csv_output}")
            except IOError as e:
                click.echo(f"\n❌ Error saving CSV file: {e}", err=True)
        
        click.echo("\n🎉 Group scan completed!")
        
    except Exception as e:
        click.echo(f"❌ Group scan failed: {e}", err=True)
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
        
        with open(json_output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        click.echo(f"\n📄 Detailed results saved to: {json_output}")
        click.echo("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        click.echo(f"❌ Demo failed: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()