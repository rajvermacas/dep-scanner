"""Language-agnostic analyzer for REST API calls.

This analyzer detects URLs in any programming language by looking for
URL patterns in the source code, regardless of the language or framework.
"""

import logging
import re
from pathlib import Path
from typing import List, Set

from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiCallAnalyzer, ApiAuthType


logger = logging.getLogger(__name__)


class GenericApiCallAnalyzer(ApiCallAnalyzer):
    """Language-agnostic analyzer for REST API calls.

    This analyzer works with any programming language by detecting URL patterns
    in strings, comments, and configuration values. It's designed as a fallback
    for languages without specific analyzers.
    """

    # Support all common file extensions
    # This is intentionally broad to catch all files
    supported_extensions: Set[str] = {
        # Web languages
        ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
        ".html", ".htm", ".css", ".scss", ".sass", ".less",
        ".vue", ".svelte",

        # Backend languages
        ".java", ".kt", ".kts",  # Java, Kotlin
        ".go",  # Go
        ".rb",  # Ruby
        ".php",  # PHP
        ".cs",  # C#
        ".rs",  # Rust
        ".swift",  # Swift
        ".m", ".mm",  # Objective-C
        ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",  # C/C++
        ".scala",  # Scala (backup for Scala analyzer)
        ".py",  # Python (backup for Python analyzer)

        # Scripting languages
        ".sh", ".bash", ".zsh", ".fish",  # Shell scripts
        ".pl", ".pm",  # Perl
        ".lua",  # Lua

        # Data/Config files
        ".json", ".yaml", ".yml", ".toml", ".xml",
        ".properties", ".ini", ".conf", ".config",
        ".env", ".env.example",

        # Other
        ".sql",  # SQL
        ".graphql", ".gql",  # GraphQL
        ".proto",  # Protocol Buffers
        ".md", ".markdown", ".rst", ".txt",  # Documentation
    }

    # URL patterns to detect
    URL_PATTERNS = [
        # Standard URL patterns in quotes (single or double) - cleaner matching
        r'["\'](https?://[^"\']+)["\']',

        # URLs in backticks (template literals in JS/TS)
        r'`(https?://[^`]+)`',

        # URLs without quotes (in comments, markdown, etc.) - exclude trailing punctuation
        r'\b(https?://[^\s<>"{}|\\^`\[\];,)]+)',

        # Interpolated URLs in various languages
        r'f["\'](https?://[^"\']+)["\']',  # Python f-strings
        r'\$\{[^}]*(https?://[^}]+)\}',  # Template literals
    ]

    # Patterns to exclude (reduce false positives)
    EXCLUDE_PATTERNS = [
        r'^https?://(www\.)?example\.(com|org|net)(/|$)',  # Root example domains only (example.com, www.example.org)
        r'^https?://localhost',  # Localhost
        r'^https?://127\.0\.0\.1',  # Loopback
        r'^https?://.*\.(test|local|invalid)',  # Test domains
        r'^https?://schemas?\.',  # XML/JSON schemas
    ]

    def analyze(self, file_path: Path) -> List[ApiCall]:
        """Analyze any file for REST API calls.

        Args:
            file_path: Path to the file

        Returns:
            List of API calls found in the file
        """
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []

        # Skip binary files
        if self._is_binary_file(file_path):
            return []

        api_calls = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

                # Extract API calls using regex patterns
                api_calls = self._extract_api_calls(content, file_path)
        except Exception as e:
            logger.warning(f"Error analyzing API calls in {file_path}: {str(e)}")
            return []

        return api_calls

    def _extract_api_calls(self, content: str, file_path: Path) -> List[ApiCall]:
        """Extract API calls from content.

        Args:
            content: Content of the file
            file_path: Path to the source file

        Returns:
            List of API calls found in the content
        """
        api_calls = []
        found_urls = set()  # Track URLs to avoid duplicates

        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern in self.URL_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Extract URL from first captured group
                    url = match.group(1) if match.lastindex and match.lastindex >= 1 else None

                    if not url or not (url.startswith('http://') or url.startswith('https://')):
                        continue

                    # Skip excluded patterns
                    if self._should_exclude_url(url):
                        continue

                    # Avoid duplicates
                    key = (url, line_num)
                    if key in found_urls:
                        continue

                    found_urls.add(key)

                    # Try to determine HTTP method from context
                    http_method = self._determine_http_method(line, url)

                    # Try to determine auth type from context
                    auth_type = self._determine_auth_type(content, line_num)

                    api_calls.append(ApiCall(
                        url=url,
                        http_method=http_method,
                        auth_type=auth_type,
                        source_file=str(file_path),
                        line_number=line_num
                    ))

        return api_calls

    def _should_exclude_url(self, url: str) -> bool:
        """Check if a URL should be excluded.

        Args:
            url: URL to check

        Returns:
            True if URL should be excluded, False otherwise
        """
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _determine_http_method(self, line: str, url: str) -> str:
        """Try to determine HTTP method from line context.

        Args:
            line: Line containing the URL
            url: The URL found

        Returns:
            HTTP method string or "UNKNOWN"
        """
        # Common patterns for HTTP methods (case-insensitive)
        method_patterns = [
            (r'\.(get|GET)\s*\(', 'GET'),  # .Get( or .get(
            (r'\b(get|GET)\s*\(', 'GET'),  # get( or GET(
            (r'\.(post|POST)\s*\(', 'POST'),  # .Post( or .post(
            (r'\b(post|POST)\s*\(', 'POST'),  # post( or POST(
            (r'\.(put|PUT)\s*\(', 'PUT'),  # .Put( or .put(
            (r'\b(put|PUT)\s*\(', 'PUT'),  # put( or PUT(
            (r'\.(delete|DELETE)\s*\(', 'DELETE'),  # .Delete( or .delete(
            (r'\b(delete|DELETE|del)\s*\(', 'DELETE'),  # delete( or DELETE(
            (r'\.(patch|PATCH)\s*\(', 'PATCH'),  # .Patch( or .patch(
            (r'\b(patch|PATCH)\s*\(', 'PATCH'),  # patch( or PATCH(
            (r'\.(head|HEAD)\s*\(', 'HEAD'),  # .Head( or .head(
            (r'\b(head|HEAD)\s*\(', 'HEAD'),  # head( or HEAD(
            (r'\.(options|OPTIONS)\s*\(', 'OPTIONS'),  # .Options( or .options(
            (r'\b(options|OPTIONS)\s*\(', 'OPTIONS'),  # options( or OPTIONS(
            # Method as parameter
            (r'method:\s*["\']?(GET|get)["\']?', 'GET'),
            (r'method:\s*["\']?(POST|post)["\']?', 'POST'),
            (r'method:\s*["\']?(PUT|put)["\']?', 'PUT'),
            (r'method:\s*["\']?(DELETE|delete)["\']?', 'DELETE'),
            (r'method:\s*["\']?(PATCH|patch)["\']?', 'PATCH'),
        ]

        for pattern, method in method_patterns:
            if re.search(pattern, line):
                return method

        return "UNKNOWN"

    def _determine_auth_type(self, content: str, line_num: int) -> ApiAuthType:
        """Try to determine authentication type from context.

        Args:
            content: Full file content
            line_num: Line number of the API call

        Returns:
            Detected authentication type
        """
        lines = content.split('\n')

        # Check surrounding lines for auth patterns (smaller window to reduce false positives)
        start_line = max(0, line_num - 3)
        end_line = min(len(lines), line_num + 3)

        # Keep original case for better matching
        context = '\n'.join(lines[start_line:end_line])
        context_lower = context.lower()

        # Check for various auth patterns (case-insensitive)
        if re.search(r'bearer\s+[a-zA-Z0-9_-]+', context_lower) or \
           re.search(r'authorization.*bearer', context_lower):
            return ApiAuthType.TOKEN

        if re.search(r'authorization.*basic', context_lower) or \
           re.search(r'basic\s+[a-zA-Z0-9+/=]+', context_lower):
            return ApiAuthType.BASIC

        # Check for API key patterns (case-insensitive)
        if re.search(r'x-api-key', context_lower) or \
           re.search(r'api[_-]?key', context_lower) or \
           re.search(r'["\']X-API-Key["\']', context) or \
           re.search(r"['\"]X-API-Key['\"]", context):  # Both quote types
            return ApiAuthType.API_KEY

        if re.search(r'oauth', context_lower):
            return ApiAuthType.OAUTH

        return ApiAuthType.UNKNOWN

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary.

        Args:
            file_path: Path to the file

        Returns:
            True if file is binary, False otherwise
        """
        # Common binary file extensions
        binary_extensions = {
            '.pyc', '.pyo', '.so', '.dll', '.dylib', '.exe',
            '.bin', '.dat', '.db', '.sqlite', '.sqlite3',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.pdf', '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z',
            '.mp3', '.mp4', '.avi', '.mov', '.wav',
            '.ttf', '.otf', '.woff', '.woff2', '.eot',
        }

        if file_path.suffix.lower() in binary_extensions:
            return True

        # Try to read first few bytes to detect binary content
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                # Check for null bytes (common in binary files)
                if b'\x00' in chunk:
                    return True
        except Exception:
            return True

        return False
