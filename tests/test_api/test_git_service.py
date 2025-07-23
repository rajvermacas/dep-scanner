"""Tests for git service URL conversion functionality."""

import pytest
from dependency_scanner_tool.api.git_service import RepositoryService


class TestRepositoryService:
    """Test cases for RepositoryService URL conversion methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = RepositoryService()
    
    def test_convert_github_url_with_git_suffix(self):
        """Test GitHub URL conversion with .git suffix."""
        git_url = "https://github.com/rajvermacas/airflow.git"
        expected_zip_url = "https://github.com/rajvermacas/airflow/archive/refs/heads/main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_github_url_without_git_suffix(self):
        """Test GitHub URL conversion without .git suffix."""
        git_url = "https://github.com/rajvermacas/airflow"
        expected_zip_url = "https://github.com/rajvermacas/airflow/archive/refs/heads/main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_github_url_with_trailing_slash(self):
        """Test GitHub URL conversion with trailing slash."""
        git_url = "https://github.com/rajvermacas/airflow/"
        expected_zip_url = "https://github.com/rajvermacas/airflow/archive/refs/heads/main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_github_url_with_git_suffix_and_trailing_slash(self):
        """Test GitHub URL conversion with .git suffix and trailing slash."""
        git_url = "https://github.com/rajvermacas/airflow.git/"
        expected_zip_url = "https://github.com/rajvermacas/airflow/archive/refs/heads/main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_gitlab_url_with_git_suffix(self):
        """Test GitLab URL conversion with .git suffix."""
        git_url = "https://gitlab.com/owner/project.git"
        expected_zip_url = "https://gitlab.com/owner/project/-/archive/main/project-main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_gitlab_url_without_git_suffix(self):
        """Test GitLab URL conversion without .git suffix."""
        git_url = "https://gitlab.com/owner/project"
        expected_zip_url = "https://gitlab.com/owner/project/-/archive/main/project-main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_gitlab_url_with_trailing_slash(self):
        """Test GitLab URL conversion with trailing slash."""
        git_url = "https://gitlab.com/owner/project/"
        expected_zip_url = "https://gitlab.com/owner/project/-/archive/main/project-main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_gitlab_url_with_git_suffix_and_trailing_slash(self):
        """Test GitLab URL conversion with .git suffix and trailing slash."""
        git_url = "https://gitlab.com/owner/project.git/"
        expected_zip_url = "https://gitlab.com/owner/project/-/archive/main/project-main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_generic_url_with_git_suffix(self):
        """Test generic Git URL conversion with .git suffix."""
        git_url = "https://example.com/owner/project.git"
        expected_zip_url = "https://example.com/owner/project/archive/main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_convert_generic_url_without_git_suffix(self):
        """Test generic Git URL conversion without .git suffix."""
        git_url = "https://example.com/owner/project"
        expected_zip_url = "https://example.com/owner/project/archive/main.zip"
        
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
    
    def test_edge_cases(self):
        """Test edge cases for URL conversion."""
        # Test with complex repository names
        git_url = "https://github.com/user/my-awesome-project.git"
        expected_zip_url = "https://github.com/user/my-awesome-project/archive/refs/heads/main.zip"
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url
        
        # Test with underscores and numbers
        git_url = "https://github.com/user123/project_name_123.git"
        expected_zip_url = "https://github.com/user123/project_name_123/archive/refs/heads/main.zip"
        actual_zip_url = self.service._convert_to_zip_url(git_url)
        assert actual_zip_url == expected_zip_url