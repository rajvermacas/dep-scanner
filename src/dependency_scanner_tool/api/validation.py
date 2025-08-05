"""URL validation for Git URLs to prevent injection and SSRF attacks."""

import re
import urllib.parse
from typing import Set
from ipaddress import ip_address

from fastapi import HTTPException, status


# Allowed Git URL schemes
ALLOWED_SCHEMES = {"https", "ssh", "git"}

# Allowed standard ports for Git operations
ALLOWED_PORTS = {80, 443, 22, 9418}  # HTTP, HTTPS, SSH, Git protocol

# Common Git hosting domains (whitelist approach)
TRUSTED_DOMAINS = {
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "dev.azure.com",
    "ssh.dev.azure.com",
    "source.developers.google.com",
    "gitlab.example.com",  # For private GitLab instances
}

# Private network ranges to block (RFC 1918, RFC 4193, etc.)
PRIVATE_NETWORKS = {
    "127.0.0.0/8",      # Loopback
    "10.0.0.0/8",       # Private Class A
    "172.16.0.0/12",    # Private Class B
    "192.168.0.0/16",   # Private Class C
    "169.254.0.0/16",   # Link-local
    "fc00::/7",         # IPv6 unique local addresses
    "::1/128",          # IPv6 loopback
}

# Cloud metadata endpoints to block
METADATA_ENDPOINTS = {
    "169.254.169.254",          # AWS, Azure, GCP
    "metadata.google.internal", # GCP
    "metadata.azure.com",       # Azure
}

# Dangerous command injection patterns
INJECTION_PATTERNS = [
    r"[;&|`$]",          # Shell metacharacters
    r"\.\.\/",           # Path traversal
    r"file:\/\/",        # File protocol
    r"ftp:\/\/",         # FTP protocol
    r"\\\\",             # UNC paths
    r"[<>]",             # Redirection operators
    r"rm\s+-rf",         # Dangerous rm commands
    r"curl\s+",          # HTTP requests
    r"wget\s+",          # HTTP requests
    r"nc\s+",            # Netcat
    r"telnet\s+",        # Telnet
]


def is_private_ip(ip: str) -> bool:
    """Check if an IP address is in a private network range."""
    try:
        addr = ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def is_metadata_endpoint(hostname: str) -> bool:
    """Check if hostname is a known cloud metadata endpoint."""
    return hostname.lower() in METADATA_ENDPOINTS


def is_gitlab_group_url(url: str) -> bool:
    """
    Check if the given URL is a GitLab group URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if it's a GitLab group URL, False otherwise
    """
    import re
    gitlab_group_pattern = r'^https://gitlab\.com/([^/]+)/?$'
    return bool(re.match(gitlab_group_pattern, url))


def validate_git_url(git_url: str) -> str:
    """
    Validate Git URL to prevent injection attacks and SSRF.
    Also supports GitLab group URLs.
    
    Args:
        git_url: The Git URL or GitLab group URL to validate
        
    Returns:
        The validated Git URL
        
    Raises:
        HTTPException: If the URL is invalid or potentially dangerous
    """
    if not git_url or not git_url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Git URL cannot be empty"
        )
    
    git_url = git_url.strip()
    
    # Check for command injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, git_url, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Git URL: contains potentially dangerous characters"
            )
    
    # Handle SSH URLs like git@github.com:user/repo.git
    if git_url.startswith("git@"):
        # Validate SSH URL format
        ssh_pattern = r"^git@([a-zA-Z0-9.-]+):([a-zA-Z0-9._/-]+)\.git$"
        match = re.match(ssh_pattern, git_url)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid SSH Git URL format"
            )
        hostname = match.group(1)
        
        # Check for metadata endpoints
        if is_metadata_endpoint(hostname):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Metadata endpoint access not allowed"
            )
        
        # Check for private networks
        if is_private_ip(hostname):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Private network access not allowed"
            )
        
        # Check domain whitelist for SSH URLs
        if hostname not in TRUSTED_DOMAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain not allowed: {hostname}. Allowed domains: {', '.join(TRUSTED_DOMAINS)}"
            )
        
        return git_url
    
    # Parse the URL for other schemes
    try:
        parsed_url = urllib.parse.urlparse(git_url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Git URL format"
        )
    
    # Validate scheme
    if parsed_url.scheme not in ALLOWED_SCHEMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Git URL scheme: {parsed_url.scheme}. Allowed: {', '.join(ALLOWED_SCHEMES)}"
        )
    
    # Check for local file paths
    if not parsed_url.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Git URL: local file paths are not allowed"
        )
    
    # Extract hostname and port
    hostname = parsed_url.hostname
    port = parsed_url.port
    
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Git URL: missing hostname"
        )
    
    # Check for metadata endpoints
    if is_metadata_endpoint(hostname):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata endpoint access not allowed"
        )
    
    # Check for private networks
    if is_private_ip(hostname):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Private network access not allowed"
        )
    
    # Check for non-standard ports
    if port and port not in ALLOWED_PORTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Non-standard port not allowed: {port}"
        )
    
    # For SSH URLs with ssh:// scheme, validate the format
    if parsed_url.scheme == "ssh":
        # Standard SSH URLs like ssh://git@github.com/user/repo.git
        pass  # Already validated above
    
    # For stricter security, only allow trusted domains (ENABLED BY DEFAULT)
    # Domain whitelisting is now enabled by default for security
    if hostname not in TRUSTED_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain not allowed: {hostname}. Allowed domains: {', '.join(TRUSTED_DOMAINS)}"
        )
    
    # Additional validation for GitHub-style URLs and GitLab group URLs
    if parsed_url.scheme in ["https", "http"]:
        # Check if it's a GitLab group URL (different validation)
        if is_gitlab_group_url(git_url):
            # GitLab group URLs are valid as-is
            return git_url
        
        # Must end with .git for HTTPS clone URLs
        if not git_url.endswith(".git"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTTPS Git URLs must end with .git"
            )
    
    return git_url


def validate_git_url_whitelist(git_url: str, allowed_domains: Set[str] = None) -> str:
    """
    Validate Git URL with domain whitelist approach.
    
    Args:
        git_url: The Git URL to validate
        allowed_domains: Set of allowed domains (defaults to TRUSTED_DOMAINS)
        
    Returns:
        The validated Git URL
        
    Raises:
        HTTPException: If the URL is invalid or not in whitelist
    """
    if allowed_domains is None:
        allowed_domains = TRUSTED_DOMAINS
    
    # First run standard validation
    validated_url = validate_git_url(git_url)
    
    # Then check domain whitelist
    parsed_url = urllib.parse.urlparse(validated_url)
    hostname = parsed_url.hostname
    
    # Handle SSH URLs
    if validated_url.startswith("git@"):
        ssh_pattern = r"^git@([a-zA-Z0-9.-]+):"
        match = re.match(ssh_pattern, validated_url)
        if match:
            hostname = match.group(1)
    
    if hostname not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain not allowed: {hostname}. Allowed domains: {', '.join(allowed_domains)}"
        )
    
    return validated_url