"""Secure repository service using ZIP download instead of git clone."""

import logging
import tempfile
import shutil
import zipfile
from pathlib import Path
from typing import Optional
import time
import requests
import re
from urllib.parse import urlparse

from dependency_scanner_tool.api.validation import validate_git_url
from dependency_scanner_tool.api.repository_cache import repository_cache


logger = logging.getLogger(__name__)


class DownloadException(Exception):
    """Exception raised when download fails."""
    pass


class RepositoryService:
    """Secure repository service with ZIP download and resource management."""
    
    def __init__(self, download_timeout: int = 300, max_repo_size: int = 500 * 1024 * 1024):
        """
        Initialize repository service.
        
        Args:
            download_timeout: Maximum time in seconds for download operations
            max_repo_size: Maximum repository size in bytes (default: 500MB)
        """
        self.download_timeout = download_timeout
        self.max_repo_size = max_repo_size
    
    def download_repository(self, git_url: str, timeout: Optional[int] = None) -> Path:
        """
        Securely download a repository as ZIP to a temporary directory with caching.
        
        Args:
            git_url: The Git URL to download (will be converted to ZIP URL)
            timeout: Optional timeout override
            
        Returns:
            Path to the downloaded and extracted repository
            
        Raises:
            Exception: If download fails, times out, or URL is invalid
        """
        # Validate the Git URL first
        validated_url = validate_git_url(git_url)
        
        # Check cache first
        cached_path = repository_cache.get(validated_url)
        if cached_path:
            logger.info(f"Using cached repository for {validated_url}: {cached_path}")
            return cached_path
        
        # Not in cache, proceed with download
        return self._download_repository_direct(validated_url, timeout)
    
    def _download_repository_direct(self, git_url: str, timeout: Optional[int] = None) -> Path:
        """
        Directly download a repository ZIP without caching check.
        
        Args:
            git_url: The Git URL to download (should be pre-validated)
            timeout: Optional timeout override
            
        Returns:
            Path to the downloaded and extracted repository
            
        Raises:
            Exception: If download fails, times out, or URL is invalid
        """
        # Create temporary directory in project root
        project_root = Path(__file__).parent.parent.parent.parent
        tmp_dir = project_root / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="repo_scan_", dir=str(tmp_dir))
        repo_path = Path(temp_dir) / "repo"
        zip_path = Path(temp_dir) / "repo.zip"
        
        try:
            logger.info(f"Downloading repository: {git_url}")
            start_time = time.time()
            
            # Convert Git URL to ZIP download URL
            zip_url = self._convert_to_zip_url(git_url)
            logger.info(f"ZIP download URL: {zip_url}")
            
            # Apply timeout to the download operation
            effective_timeout = timeout or self.download_timeout
            
            # Download ZIP file
            self._download_zip(zip_url, zip_path, effective_timeout)
            
            # Extract ZIP file
            self._extract_zip(zip_path, repo_path)
            
            # Clean up ZIP file
            zip_path.unlink()
            
            download_time = time.time() - start_time
            logger.info(f"Repository downloaded and extracted successfully in {download_time:.2f} seconds")
            
            # Check repository size
            repo_size = self._get_directory_size(repo_path)
            if repo_size > self.max_repo_size:
                logger.warning(f"Repository size ({repo_size} bytes) exceeds limit ({self.max_repo_size} bytes)")
                shutil.rmtree(temp_dir)
                raise Exception(f"Repository size exceeds limit: {repo_size} bytes")
            
            logger.info(f"Repository size: {repo_size} bytes")
            
            # Add to cache before returning
            repository_cache.put(git_url, repo_path)
            
            return repo_path
            
        except DownloadException as e:
            logger.error(f"Repository download failed: {str(e)}")
            shutil.rmtree(temp_dir)
            raise Exception(f"Repository download failed: {str(e)}")
        except Exception as e:
            logger.error(f"Download operation failed: {str(e)}")
            shutil.rmtree(temp_dir)
            raise Exception(f"Download operation failed: {str(e)}")
    
    def _convert_to_zip_url(self, git_url: str) -> str:
        """Convert Git URL to ZIP download URL."""
        # Handle GitHub URLs
        github_pattern = r'https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
        match = re.match(github_pattern, git_url)
        if match:
            owner, repo = match.groups()
            # Remove .git suffix if present
            if repo.endswith('.git'):
                repo = repo[:-4]
            return f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
        
        # Handle GitLab URLs
        gitlab_pattern = r'https://gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
        match = re.match(gitlab_pattern, git_url)
        if match:
            owner, repo = match.groups()
            # Remove .git suffix if present
            if repo.endswith('.git'):
                repo = repo[:-4]
            return f"https://gitlab.com/{owner}/{repo}/-/archive/main/{repo}-main.zip"
        
        # For other Git hosting services, try a generic approach
        # This might not work for all services, but covers common patterns
        if git_url.endswith('.git'):
            base_url = git_url[:-4]
        else:
            base_url = git_url.rstrip('/')
        
        # Try common ZIP download patterns
        return f"{base_url}/archive/main.zip"
    
    def _download_zip(self, zip_url: str, zip_path: Path, timeout_seconds: int) -> None:
        """Download ZIP file with timeout protection."""
        try:
            headers = {
                'User-Agent': 'dependency-scanner-tool/1.0',
                'Accept': 'application/zip, application/octet-stream, */*'
            }
            
            response = requests.get(
                zip_url,
                headers=headers,
                timeout=timeout_seconds,
                stream=True,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Write the ZIP file
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            logger.info(f"Downloaded ZIP file: {zip_path} ({zip_path.stat().st_size} bytes)")
            
        except requests.exceptions.RequestException as e:
            raise DownloadException(f"Failed to download ZIP: {str(e)}")
    
    def _extract_zip(self, zip_path: Path, extract_path: Path) -> None:
        """Extract ZIP file to target directory."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the list of files in the ZIP
                file_list = zip_ref.namelist()
                if not file_list:
                    raise DownloadException("ZIP file is empty")
                
                # Find the root directory in the ZIP (usually <repo>-<branch>/)
                root_dirs = set()
                for file_path in file_list:
                    parts = file_path.split('/')
                    if len(parts) > 1:
                        root_dirs.add(parts[0])
                
                # Extract all files
                zip_ref.extractall(extract_path.parent)
                
                # If there's a single root directory, move its contents up
                if len(root_dirs) == 1:
                    root_dir = extract_path.parent / list(root_dirs)[0]
                    if root_dir.exists() and root_dir.is_dir():
                        # Move contents of root_dir to extract_path
                        extract_path.mkdir(exist_ok=True)
                        for item in root_dir.iterdir():
                            shutil.move(str(item), str(extract_path / item.name))
                        # Remove the now-empty root directory
                        root_dir.rmdir()
                    else:
                        # Fallback: rename root_dir to extract_path
                        root_dir.rename(extract_path)
                else:
                    # Multiple root directories or files, create extract_path and move everything there
                    extract_path.mkdir(exist_ok=True)
                    for item in extract_path.parent.iterdir():
                        if item != extract_path and item != zip_path:
                            shutil.move(str(item), str(extract_path / item.name))
                            
            logger.info(f"Extracted ZIP to: {extract_path}")
            
        except zipfile.BadZipFile as e:
            raise DownloadException(f"Invalid ZIP file: {str(e)}")
        except Exception as e:
            raise DownloadException(f"Failed to extract ZIP: {str(e)}")
    
    def _get_directory_size(self, path: Path) -> int:
        """Get the total size of a directory in bytes."""
        total_size = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (OSError, IOError) as e:
            logger.warning(f"Error calculating directory size: {e}")
        return total_size
    
    def validate_repository(self, repo_path: Path) -> bool:
        """
        Validate that a path contains a valid repository structure.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            True if valid repository structure, False otherwise
        """
        try:
            return repo_path.exists() and repo_path.is_dir() and any(repo_path.iterdir())
        except Exception:
            return False
    
    def cleanup_repository(self, repo_path: Path) -> None:
        """
        Clean up a cloned repository.
        
        Args:
            repo_path: Path to the repository to clean up
        """
        try:
            # Get the parent temp directory
            temp_dir = repo_path.parent
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up repository: {repo_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup repository {repo_path}: {e}")
    
    def get_repository_info(self, repo_path: Path) -> dict:
        """
        Get basic information about a repository.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            Dictionary with repository information
        """
        try:
            # For ZIP-downloaded repos, we have limited info
            # Return basic filesystem information
            stat = repo_path.stat()
            return {
                "path": str(repo_path),
                "size_bytes": self._get_directory_size(repo_path),
                "created_time": stat.st_ctime,
                "modified_time": stat.st_mtime,
                "file_count": len(list(repo_path.rglob("*"))),
            }
        except Exception as e:
            logger.error(f"Failed to get repository info: {e}")
            return {}


# Global repository service instance
repository_service = RepositoryService()

# Backward compatibility alias
git_service = repository_service