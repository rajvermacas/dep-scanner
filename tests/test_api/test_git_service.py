"""Tests for git service URL conversion functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
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


class TestDownloadProgressCallback:
    """Test cases for download progress callback functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = RepositoryService()

    @patch('dependency_scanner_tool.api.git_service.requests.get')
    def test_download_zip_calls_progress_callback(self, mock_get):
        """Test that download progress callback is called during download."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        # Simulate downloading 3 chunks of 8KB each (24KB total)
        mock_response.iter_content = Mock(return_value=[b'x' * 8192, b'y' * 8192, b'z' * 8192])
        mock_get.return_value = mock_response

        # Create progress callback mock
        progress_callback = Mock()

        # Create temp zip path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            zip_path = Path(tmp.name)

        try:
            # Call download with callback
            self.service._download_zip(
                "https://example.com/test.zip",
                zip_path,
                timeout_seconds=30,
                progress_callback=progress_callback
            )

            # Verify callback was called with cumulative byte counts
            assert progress_callback.call_count == 3
            progress_callback.assert_any_call(8192)    # First chunk
            progress_callback.assert_any_call(16384)   # First + second chunk
            progress_callback.assert_any_call(24576)   # All chunks
        finally:
            # Cleanup
            if zip_path.exists():
                zip_path.unlink()

    @patch('dependency_scanner_tool.api.git_service.requests.get')
    def test_download_zip_without_callback(self, mock_get):
        """Test that download works without progress callback."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        mock_response.iter_content = Mock(return_value=[b'x' * 8192])
        mock_get.return_value = mock_response

        # Create temp zip path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            zip_path = Path(tmp.name)

        try:
            # Call download without callback (should not raise error)
            self.service._download_zip(
                "https://example.com/test.zip",
                zip_path,
                timeout_seconds=30,
                progress_callback=None
            )

            # Verify file was created
            assert zip_path.exists()
        finally:
            # Cleanup
            if zip_path.exists():
                zip_path.unlink()

    @patch('dependency_scanner_tool.api.git_service.repository_cache')
    @patch('dependency_scanner_tool.api.git_service.validate_git_url')
    def test_download_repository_passes_callback(self, mock_validate, mock_cache):
        """Test that download_repository passes callback to underlying method."""
        mock_validate.return_value = "https://github.com/test/repo.git"
        mock_cache.get.return_value = None  # Not in cache

        progress_callback = Mock()

        # Patch _download_repository_direct to verify callback is passed
        with patch.object(self.service, '_download_repository_direct') as mock_direct:
            mock_direct.return_value = Path("/fake/path")

            self.service.download_repository(
                "https://github.com/test/repo.git",
                progress_callback=progress_callback
            )

            # Verify callback was passed to _download_repository_direct
            mock_direct.assert_called_once_with(
                "https://github.com/test/repo.git",
                None,  # timeout
                progress_callback
            )