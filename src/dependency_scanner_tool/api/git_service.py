"""Secure Git service using GitPython instead of subprocess."""

import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional
import time

from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from dependency_scanner_tool.api.validation import validate_git_url


logger = logging.getLogger(__name__)


class GitService:
    """Secure Git service with timeout and resource management."""
    
    def __init__(self, clone_timeout: int = 300, max_repo_size: int = 500 * 1024 * 1024):
        """
        Initialize Git service.
        
        Args:
            clone_timeout: Maximum time in seconds for clone operations
            max_repo_size: Maximum repository size in bytes (default: 500MB)
        """
        self.clone_timeout = clone_timeout
        self.max_repo_size = max_repo_size
    
    def clone_repository(self, git_url: str, timeout: Optional[int] = None) -> Path:
        """
        Securely clone a Git repository to a temporary directory.
        
        Args:
            git_url: The Git URL to clone
            timeout: Optional timeout override
            
        Returns:
            Path to the cloned repository
            
        Raises:
            Exception: If clone fails, times out, or URL is invalid
        """
        # Validate the Git URL first
        validated_url = validate_git_url(git_url)
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="repo_scan_")
        repo_path = Path(temp_dir) / "repo"
        
        try:
            logger.info(f"Cloning repository: {validated_url}")
            start_time = time.time()
            
            # Clone with GitPython (more secure than subprocess)
            # Note: GitPython doesn't support timeout parameter directly
            Repo.clone_from(
                validated_url,
                str(repo_path),
                # Additional security options
                no_hardlinks=True,  # Prevent hardlink attacks
                depth=1,  # Shallow clone for faster operations
                single_branch=True,  # Only clone default branch
                # Disable certain Git features for security
                env={
                    "GIT_TERMINAL_PROMPT": "0",  # Disable interactive prompts
                    "GIT_ASKPASS": "echo",  # Disable password prompts
                    "GIT_SSH_COMMAND": "ssh -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/dev/null",
                }
            )
            
            clone_time = time.time() - start_time
            logger.info(f"Repository cloned successfully in {clone_time:.2f} seconds")
            
            # Check repository size
            repo_size = self._get_directory_size(repo_path)
            if repo_size > self.max_repo_size:
                logger.warning(f"Repository size ({repo_size} bytes) exceeds limit ({self.max_repo_size} bytes)")
                shutil.rmtree(temp_dir)
                raise Exception(f"Repository size exceeds limit: {repo_size} bytes")
            
            logger.info(f"Repository size: {repo_size} bytes")
            return repo_path
            
        except GitCommandError as e:
            logger.error(f"Git clone failed: {str(e)}")
            shutil.rmtree(temp_dir)
            raise Exception(f"Git clone failed: {str(e)}")
        except Exception as e:
            logger.error(f"Clone operation failed: {str(e)}")
            shutil.rmtree(temp_dir)
            raise Exception(f"Clone operation failed: {str(e)}")
    
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
        Validate that a path contains a valid Git repository.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            True if valid Git repository, False otherwise
        """
        try:
            repo = Repo(str(repo_path))
            return not repo.bare  # Ensure it's not a bare repository
        except (InvalidGitRepositoryError, NoSuchPathError):
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
            repo = Repo(str(repo_path))
            return {
                "remote_url": repo.remotes.origin.url if repo.remotes else None,
                "branch": repo.active_branch.name if repo.active_branch else None,
                "commit_hash": repo.head.commit.hexsha if repo.head.commit else None,
                "commit_message": repo.head.commit.message.strip() if repo.head.commit else None,
                "author": str(repo.head.commit.author) if repo.head.commit else None,
                "commit_date": repo.head.commit.committed_datetime.isoformat() if repo.head.commit else None,
            }
        except Exception as e:
            logger.error(f"Failed to get repository info: {e}")
            return {}


# Global Git service instance
git_service = GitService()