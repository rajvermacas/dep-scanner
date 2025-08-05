"""GitLab API service for group and project operations."""

import logging
import re
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, quote

logger = logging.getLogger(__name__)


class GitLabGroupService:
    """Service for interacting with GitLab groups and projects."""
    
    def __init__(self, access_token: Optional[str] = None, timeout: int = 30):
        """
        Initialize GitLab service.
        
        Args:
            access_token: GitLab personal access token (optional for public groups)
            timeout: Request timeout in seconds
        """
        self.access_token = access_token
        self.timeout = timeout
        self.session = requests.Session()
        
        if access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {access_token}',
                'Private-Token': access_token
            })
        
        self.session.headers.update({
            'User-Agent': 'dependency-scanner-tool/1.0'
        })
    
    def is_gitlab_group_url(self, url: str) -> bool:
        """
        Check if the given URL is a GitLab group URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if it's a GitLab group URL, False otherwise
        """
        # Match GitLab group URLs like https://gitlab.com/group-name
        gitlab_group_pattern = r'^https://gitlab\.com/([^/]+)/?$'
        return bool(re.match(gitlab_group_pattern, url))
    
    def extract_group_path(self, group_url: str) -> str:
        """
        Extract group path from GitLab group URL.
        
        Args:
            group_url: GitLab group URL
            
        Returns:
            Group path/name
            
        Raises:
            ValueError: If URL format is invalid
        """
        gitlab_group_pattern = r'^https://gitlab\.com/([^/]+)/?$'
        match = re.match(gitlab_group_pattern, group_url)
        
        if not match:
            raise ValueError(f"Invalid GitLab group URL format: {group_url}")
        
        return match.group(1)
    
    def get_group_projects(self, group_url: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get all projects in a GitLab group.
        
        Args:
            group_url: GitLab group URL
            per_page: Number of projects per API page
            
        Returns:
            List of project dictionaries
            
        Raises:
            Exception: If API request fails
        """
        group_path = self.extract_group_path(group_url)
        
        # URL encode the group path to handle special characters
        encoded_group_path = quote(group_path, safe='')
        
        projects = []
        page = 1
        
        while True:
            api_url = f"https://gitlab.com/api/v4/groups/{encoded_group_path}/projects"
            params = {
                'page': page,
                'per_page': per_page,
                'simple': 'true',  # Get simplified project info
                'archived': 'false',  # Exclude archived projects
                'order_by': 'name',
                'sort': 'asc'
            }
            
            try:
                logger.info(f"Fetching GitLab group projects: {api_url} (page {page})")
                response = self.session.get(api_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                page_projects = response.json()
                
                if not page_projects:
                    break
                
                projects.extend(page_projects)
                
                # Check if there are more pages
                if len(page_projects) < per_page:
                    break
                
                page += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch GitLab group projects: {e}")
                raise Exception(f"Failed to fetch GitLab group projects: {e}")
        
        logger.info(f"Found {len(projects)} projects in group: {group_path}")
        return projects
    
    def get_project_git_urls(self, group_url: str) -> List[str]:
        """
        Get Git clone URLs for all projects in a group.
        
        Args:
            group_url: GitLab group URL
            
        Returns:
            List of Git clone URLs
        """
        projects = self.get_group_projects(group_url)
        git_urls = []
        
        for project in projects:
            # Use HTTPS clone URL with .git suffix
            if 'http_url_to_repo' in project:
                git_urls.append(project['http_url_to_repo'])
            elif 'web_url' in project:
                # Fallback: construct from web URL
                web_url = project['web_url']
                if not web_url.endswith('.git'):
                    web_url += '.git'
                git_urls.append(web_url)
        
        logger.info(f"Generated {len(git_urls)} Git URLs from group projects")
        return git_urls
    
    def get_project_info(self, group_url: str) -> List[Dict[str, str]]:
        """
        Get project information for all projects in a group.
        
        Args:
            group_url: GitLab group URL
            
        Returns:
            List of dictionaries with project info (name, url, description)
        """
        projects = self.get_group_projects(group_url)
        project_info = []
        
        for project in projects:
            info = {
                'name': project.get('name', 'Unknown'),
                'path': project.get('path', ''),
                'git_url': project.get('http_url_to_repo', ''),
                'web_url': project.get('web_url', ''),
                'description': project.get('description', ''),
                'default_branch': project.get('default_branch', 'main'),
                'created_at': project.get('created_at', ''),
                'last_activity_at': project.get('last_activity_at', '')
            }
            project_info.append(info)
        
        return project_info


# Global GitLab service instance
gitlab_service = GitLabGroupService()
