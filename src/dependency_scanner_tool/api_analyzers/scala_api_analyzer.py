"""Analyzer for Scala REST API calls."""

import logging
import re
from pathlib import Path
from typing import List, Optional, Set

from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiCallAnalyzer, ApiAuthType


class ScalaApiCallAnalyzer(ApiCallAnalyzer):
    """Analyzer for Scala REST API calls."""
    
    # Define supported file extensions
    supported_extensions: Set[str] = {".scala"}
    
    # Mapping of common HTTP libraries and their patterns
    HTTP_LIBRARIES = {
        "akka-http": {
            "patterns": [
                # Http().singleRequest(Get("url"))
                r'Http\(\)\.singleRequest\s*\(\s*(Get|Post|Put|Delete|Patch|Head|Options)\s*\(\s*"([^"]+)"',
                # HttpRequest(HttpMethods.GET, "url")
                r'HttpRequest\s*\(\s*HttpMethods\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s*,\s*"([^"]+)"',
            ]
        },
        "play-ws": {
            "patterns": [
                # ws.url("url").get()
                r'ws\.url\s*\(\s*"([^"]+)"\s*\)\.get\s*\(',
                # ws.url("url").post(data)
                r'ws\.url\s*\(\s*"([^"]+)"\s*\)\.post\s*\(',
                # ws.url("url").put(data)
                r'ws\.url\s*\(\s*"([^"]+)"\s*\)\.put\s*\(',
                # ws.url("url").delete()
                r'ws\.url\s*\(\s*"([^"]+)"\s*\)\.delete\s*\(',
                # ws.url("url").patch(data)
                r'ws\.url\s*\(\s*"([^"]+)"\s*\)\.patch\s*\(',
            ]
        },
        "sttp": {
            "patterns": [
                # basicRequest.get(uri"url") - handle multiline
                r'\.get\s*\(\s*uri"([^"]+)"',
                # basicRequest.post(uri"url") - handle multiline
                r'\.post\s*\(\s*uri"([^"]+)"',
                # basicRequest.put(uri"url") - handle multiline
                r'\.put\s*\(\s*uri"([^"]+)"',
                # basicRequest.delete(uri"url") - handle multiline
                r'\.delete\s*\(\s*uri"([^"]+)"',
                # basicRequest.patch(uri"url") - handle multiline
                r'\.patch\s*\(\s*uri"([^"]+)"',
            ]
        },
        "scalaj-http": {
            "patterns": [
                # Http("url")
                r'Http\s*\(\s*"([^"]+)"\s*\)',
            ]
        },
        "requests-scala": {
            "patterns": [
                # requests.method("url") - match any method name
                r'requests\.(\w+)\s*\(\s*"([^"]+)"',
            ]
        }
    }
    
    def analyze(self, file_path: Path) -> List[ApiCall]:
        """Analyze Scala file for REST API calls.
        
        Args:
            file_path: Path to the Scala file
            
        Returns:
            List of API calls found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        if not file_path.exists():
            logging.warning(f"File does not exist: {file_path}")
            return []
        
        api_calls = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract API calls using regex patterns
                api_calls = self._extract_api_calls_with_regex(content, file_path)
        except Exception as e:
            logging.warning(f"Error analyzing Scala API calls in {file_path}: {str(e)}")
            # Don't raise the exception, just return an empty list
            return []
        
        return api_calls
    
    def _extract_api_calls_with_regex(self, content: str, file_path: Path) -> List[ApiCall]:
        """Extract API calls using regex patterns.

        Args:
            content: Content of the Scala file
            file_path: Path to the source file

        Returns:
            List of API calls found in the file
        """
        api_calls = []
        found_urls = set()  # Track URLs to avoid duplicates

        # Remove comments from the entire content
        content_clean = self._remove_all_comments(content)
        lines = content_clean.split('\n')

        # First, extract variable assignments for URLs
        url_variables = self._extract_url_variables(content_clean)

        # Process line by line AND multiline patterns
        for line_num, line in enumerate(lines, 1):
            line_clean = line.strip()
            if not line_clean:
                continue

            for library, config in self.HTTP_LIBRARIES.items():
                for pattern in config["patterns"]:
                    matches = re.finditer(pattern, line_clean, re.IGNORECASE)
                    for match in matches:
                        api_call = self._process_regex_match(
                            match, library, pattern, line_clean, file_path, line_num
                        )
                        if api_call:
                            key = (api_call.url, api_call.line_number)
                            if key not in found_urls:
                                found_urls.add(key)
                                api_calls.append(api_call)

        # Handle multiline patterns (like Play WS and STTP)
        multiline_calls = self._extract_multiline_api_calls(content_clean, file_path)

        # Add multiline calls, avoiding duplicates and updating existing ones
        for new_call in multiline_calls:
            # Check if we already have a call for the same URL
            updated = False
            for i, existing_call in enumerate(api_calls):
                if (existing_call.url == new_call.url and
                    abs((existing_call.line_number or 0) - (new_call.line_number or 0)) <= 3):
                    # Update the existing call with better method info if available
                    if existing_call.http_method == 'GET' and new_call.http_method != 'GET':
                        api_calls[i] = new_call
                    updated = True
                    break

            if not updated:
                key = (new_call.url, new_call.line_number)
                if key not in found_urls:
                    found_urls.add(key)
                    api_calls.append(new_call)

        # Handle Java HTTP client patterns
        java_http_calls = self._extract_java_http_calls(content_clean, file_path, url_variables)
        for call in java_http_calls:
            key = (call.url, call.line_number)
            if key not in found_urls:
                found_urls.add(key)
                api_calls.append(call)

        # Extract generic URLs (any URL in quotes, regardless of library)
        generic_url_calls = self._extract_generic_urls(content_clean, file_path)
        for call in generic_url_calls:
            key = (call.url, call.line_number)
            if key not in found_urls:
                found_urls.add(key)
                api_calls.append(call)

        # Look for authentication patterns in the content
        api_calls = self._detect_authentication(api_calls, content)

        return api_calls
    
    def _process_regex_match(self, match: re.Match, library: str, pattern: str, 
                           line: str, file_path: Path, line_num: int) -> Optional[ApiCall]:
        """Process a regex match to extract API call information.
        
        Args:
            match: Regex match object
            library: Name of the HTTP library
            pattern: Regex pattern that matched
            line: Source line containing the match
            file_path: Path to the source file
            line_num: Line number in the file
            
        Returns:
            ApiCall object if valid information can be extracted, None otherwise
        """
        groups = match.groups()
        
        if library == "akka-http":
            if len(groups) >= 2:
                http_method, url = groups[0], groups[1]
                return ApiCall(
                    url=url,
                    http_method=http_method.upper(),
                    auth_type=ApiAuthType.UNKNOWN,
                    source_file=str(file_path),
                    line_number=line_num
                )
        
        elif library == "play-ws":
            url = groups[0]
            # Determine HTTP method from the pattern
            http_method = self._determine_play_ws_method(pattern)
            return ApiCall(
                url=url,
                http_method=http_method,
                auth_type=ApiAuthType.UNKNOWN,
                source_file=str(file_path),
                line_number=line_num
            )
        
        elif library == "sttp":
            url = groups[0]
            # Determine HTTP method from the pattern
            http_method = self._determine_sttp_method(pattern)
            return ApiCall(
                url=url,
                http_method=http_method,
                auth_type=ApiAuthType.UNKNOWN,
                source_file=str(file_path),
                line_number=line_num
            )
        
        elif library == "scalaj-http":
            url = groups[0]
            # Determine HTTP method from the pattern
            http_method = self._determine_scalaj_method(pattern, line)
            return ApiCall(
                url=url,
                http_method=http_method,
                auth_type=ApiAuthType.UNKNOWN,
                source_file=str(file_path),
                line_number=line_num
            )
        
        elif library == "requests-scala":
            if len(groups) >= 2:
                http_method, url = groups[0], groups[1]
                return ApiCall(
                    url=url,
                    http_method=http_method.upper(),
                    auth_type=ApiAuthType.UNKNOWN,
                    source_file=str(file_path),
                    line_number=line_num
                )
        
        return None
    
    def _extract_multiline_api_calls(self, content: str, file_path: Path) -> List[ApiCall]:
        """Extract API calls that might span multiple lines.
        
        Args:
            content: Clean content of the file
            file_path: Path to the source file
            
        Returns:
            List of API calls found spanning multiple lines
        """
        api_calls = []
        
        # Play WS multiline patterns
        # Pattern: ws.url("...").method()
        play_ws_patterns = [
            r'ws\.url\s*\(\s*"([^"]+)"\s*\)\s*\..*?\.get\s*\(',
            r'ws\.url\s*\(\s*"([^"]+)"\s*\)\s*\..*?\.post\s*\(',
            r'ws\.url\s*\(\s*"([^"]+)"\s*\)\s*\..*?\.put\s*\(',
            r'ws\.url\s*\(\s*"([^"]+)"\s*\)\s*\..*?\.delete\s*\(',
            r'ws\.url\s*\(\s*"([^"]+)"\s*\)\s*\..*?\.patch\s*\(',
        ]
        
        for pattern in play_ws_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                url = match.group(1)
                # Determine method from pattern
                if '.get(' in pattern:
                    method = 'GET'
                elif '.post(' in pattern:
                    method = 'POST'
                elif '.put(' in pattern:
                    method = 'PUT'
                elif '.delete(' in pattern:
                    method = 'DELETE'
                elif '.patch(' in pattern:
                    method = 'PATCH'
                else:
                    method = 'GET'
                
                line_num = content[:match.start()].count('\n') + 1
                api_calls.append(ApiCall(
                    url=url,
                    http_method=method,
                    auth_type=ApiAuthType.UNKNOWN,
                    source_file=str(file_path),
                    line_number=line_num
                ))
        
        # STTP multiline patterns
        # Pattern: basicRequest.method(uri"...")
        sttp_patterns = [
            r'basicRequest\s*\..*?\.get\s*\(\s*uri"([^"]+)"',
            r'basicRequest\s*\..*?\.post\s*\(\s*uri"([^"]+)"',
            r'basicRequest\s*\..*?\.put\s*\(\s*uri"([^"]+)"',
            r'basicRequest\s*\..*?\.delete\s*\(\s*uri"([^"]+)"',
            r'basicRequest\s*\..*?\.patch\s*\(\s*uri"([^"]+)"',
        ]
        
        for pattern in sttp_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                url = match.group(1)
                # Determine method from pattern
                if '.get(' in pattern:
                    method = 'GET'
                elif '.post(' in pattern:
                    method = 'POST'
                elif '.put(' in pattern:
                    method = 'PUT'
                elif '.delete(' in pattern:
                    method = 'DELETE'
                elif '.patch(' in pattern:
                    method = 'PATCH'
                else:
                    method = 'GET'
                
                line_num = content[:match.start()].count('\n') + 1
                api_calls.append(ApiCall(
                    url=url,
                    http_method=method,
                    auth_type=ApiAuthType.UNKNOWN,
                    source_file=str(file_path),
                    line_number=line_num
                ))
        
        # ScalaJ-HTTP: Look for Http() calls followed by postForm/postData on subsequent lines
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line_clean = line.strip()
            # Look for Http("url") pattern
            http_match = re.search(r'Http\s*\(\s*"([^"]+)"\s*\)', line_clean)
            if http_match:
                url = http_match.group(1)
                # Check the next few lines for postForm or postData
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if re.search(r'\.postForm\s*\(|\.postData\s*\(', next_line):
                        # This is a POST request
                        line_num = i + 1
                        api_calls.append(ApiCall(
                            url=url,
                            http_method='POST',
                            auth_type=ApiAuthType.UNKNOWN,
                            source_file=str(file_path),
                            line_number=line_num
                        ))
                        break
                    elif re.search(r'^\s*val\s+\w+\s*=|^\s*$|^\s*\)', next_line):
                        # Found end of statement or new statement
                        break
        
        return api_calls
    
    def _determine_play_ws_method(self, pattern: str) -> str:
        """Determine HTTP method for Play WS calls."""
        if ".get(" in pattern:
            return "GET"
        elif ".post(" in pattern:
            return "POST"
        elif ".put(" in pattern:
            return "PUT"
        elif ".delete(" in pattern:
            return "DELETE"
        elif ".patch(" in pattern:
            return "PATCH"
        return "GET"  # Default
    
    def _determine_sttp_method(self, pattern: str) -> str:
        """Determine HTTP method for STTP calls."""
        if ".get(" in pattern:
            return "GET"
        elif ".post(" in pattern:
            return "POST"
        elif ".put(" in pattern:
            return "PUT"
        elif ".delete(" in pattern:
            return "DELETE"
        elif ".patch(" in pattern:
            return "PATCH"
        return "GET"  # Default
    
    def _determine_scalaj_method(self, pattern: str, line: str) -> str:
        """Determine HTTP method for scalaj-http calls."""
        if ".postForm(" in pattern or ".postData(" in pattern:
            return "POST"
        
        # Look for explicit method specification in the line
        if re.search(r'\.method\s*\(\s*"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)"', line, re.IGNORECASE):
            method_match = re.search(r'\.method\s*\(\s*"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)"', line, re.IGNORECASE)
            if method_match:
                return method_match.group(1).upper()
        
        return "GET"  # Default
    
    def _detect_authentication(self, api_calls: List[ApiCall], content: str) -> List[ApiCall]:
        """Detect and update authentication types for API calls.
        
        Args:
            api_calls: List of API calls to update
            content: Full content of the file
            
        Returns:
            Updated list of API calls with authentication information
        """
        # Look for authentication patterns in the content
        lines = content.split('\n')
        
        for i, api_call in enumerate(api_calls):
            # Check the surrounding lines for authentication patterns
            start_line = max(0, api_call.line_number - 5) if api_call.line_number else 0
            end_line = min(len(lines), api_call.line_number + 5) if api_call.line_number else len(lines)
            
            context = '\n'.join(lines[start_line:end_line])
            
            # Check for various auth patterns
            auth_type = self._detect_auth_type(context)
            if auth_type != ApiAuthType.UNKNOWN:
                api_calls[i] = ApiCall(
                    url=api_call.url,
                    http_method=api_call.http_method,
                    auth_type=auth_type,
                    source_file=api_call.source_file,
                    line_number=api_call.line_number
                )
        
        return api_calls
    
    def _detect_auth_type(self, context: str) -> ApiAuthType:
        """Detect authentication type from context.
        
        Args:
            context: Context around the API call
            
        Returns:
            Detected authentication type
        """
        context_lower = context.lower()
        
        # Check for Bearer token
        if re.search(r'bearer\s+[a-zA-Z0-9_-]+', context_lower) or \
           re.search(r'authorization.*bearer', context_lower) or \
           re.search(r'\.auth\.bearer\s*\(', context_lower):
            return ApiAuthType.TOKEN
        
        # Check for Basic auth
        if re.search(r'authorization.*basic', context_lower) or \
           re.search(r'\.auth\.basic\s*\(', context_lower) or \
           re.search(r'basic\s+[a-zA-Z0-9+/=]+', context_lower):
            return ApiAuthType.BASIC
        
        # Check for API key
        if re.search(r'x-api-key', context_lower) or \
           re.search(r'api[_-]?key', context_lower):
            return ApiAuthType.API_KEY
        
        # Check for OAuth
        if re.search(r'oauth', context_lower):
            return ApiAuthType.OAUTH
        
        return ApiAuthType.UNKNOWN
    
    def _extract_url_variables(self, content: str) -> dict:
        """Extract URL variable assignments from content.
        
        Args:
            content: Clean content of the file
            
        Returns:
            Dictionary mapping variable names to URL values
        """
        url_variables = {}
        
        # Pattern for variable assignments: val varName = "url"
        pattern = r'val\s+(\w+)\s*=\s*"(https?://[^"]+)"'
        matches = re.finditer(pattern, content, re.IGNORECASE)
        
        for match in matches:
            var_name = match.group(1)
            url = match.group(2)
            url_variables[var_name] = url
        
        return url_variables
    
    def _extract_java_http_calls(self, content: str, file_path: Path, url_variables: dict) -> List[ApiCall]:
        """Extract Java HTTP client API calls.
        
        Args:
            content: Clean content of the file
            file_path: Path to the source file
            url_variables: Dictionary of URL variables
            
        Returns:
            List of API calls from Java HTTP client usage
        """
        api_calls = []
        
        # Pattern 1: Direct URL in URI.create("url")
        uri_pattern = r'\.uri\s*\(\s*java\.net\.URI\.create\s*\(\s*"([^"]+)"\s*\)\s*\)'
        uri_matches = re.finditer(uri_pattern, content, re.IGNORECASE)
        
        for match in uri_matches:
            url = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            # Find the HTTP method for this request
            http_method = self._find_java_http_method(content, match.start(), match.end())
            
            api_calls.append(ApiCall(
                url=url,
                http_method=http_method,
                auth_type=ApiAuthType.UNKNOWN,
                source_file=str(file_path),
                line_number=line_num
            ))
        
        # Pattern 2: Variable-based URL in URI.create(variable)
        var_uri_pattern = r'\.uri\s*\(\s*java\.net\.URI\.create\s*\(\s*(\w+)\s*\)\s*\)'
        var_uri_matches = re.finditer(var_uri_pattern, content, re.IGNORECASE)
        
        for match in var_uri_matches:
            var_name = match.group(1)
            if var_name in url_variables:
                url = url_variables[var_name]
                line_num = content[:match.start()].count('\n') + 1
                
                # Find the HTTP method for this request
                http_method = self._find_java_http_method(content, match.start(), match.end())
                
                api_calls.append(ApiCall(
                    url=url,
                    http_method=http_method,
                    auth_type=ApiAuthType.UNKNOWN,
                    source_file=str(file_path),
                    line_number=line_num
                ))
        
        return api_calls
    
    def _find_java_http_method(self, content: str, uri_start: int, uri_end: int) -> str:
        """Find the HTTP method for a Java HTTP request.
        
        Args:
            content: Content of the file
            uri_start: Start position of the URI match
            uri_end: End position of the URI match
            
        Returns:
            HTTP method string
        """
        # Look forward from the URI match for the HTTP method
        # Find the end of the current request builder (until .build())
        context_start = uri_start
        build_match = re.search(r'\.build\s*\(\s*\)', content[uri_end:])
        if build_match:
            context_end = uri_end + build_match.end()
        else:
            context_end = min(len(content), uri_end + 200)
        
        context = content[context_start:context_end]
        
        # Look for HTTP method patterns in this specific request context
        method_patterns = [
            (r'\.GET\s*\(\s*\)', 'GET'),
            (r'\.POST\s*\(', 'POST'),
            (r'\.PUT\s*\(', 'PUT'),
            (r'\.DELETE\s*\(\s*\)', 'DELETE'),
            (r'\.PATCH\s*\(', 'PATCH'),
            (r'\.HEAD\s*\(\s*\)', 'HEAD'),
        ]
        
        for pattern, method in method_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return method
        
        return 'GET'  # Default to GET if no method found
    
    def _remove_comments(self, line: str) -> str:
        """Remove comments from a line.
        
        Args:
            line: Source line
            
        Returns:
            Line with comments removed
        """
        # Remove single-line comments
        comment_pos = line.find('//')
        if comment_pos != -1:
            line = line[:comment_pos]
        
        return line.strip()
    
    def _extract_generic_urls(self, content: str, file_path: Path) -> List[ApiCall]:
        """Extract generic URLs from content regardless of HTTP library.

        Args:
            content: Clean content of the file
            file_path: Path to the source file

        Returns:
            List of API calls with generic URLs
        """
        api_calls = []

        # Generic URL pattern to catch any http(s) URLs in quotes
        # Matches both double quotes and uri"..." syntax used in Scala
        url_patterns = [
            r'"(https?://[^"]+)"',  # Double quotes
            r"'(https?://[^']+)'",  # Single quotes (less common in Scala)
            r'uri"(https?://[^"]+)"',  # STTP uri interpolator
        ]

        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern in url_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    url = match.group(1)
                    api_calls.append(ApiCall(
                        url=url,
                        http_method="UNKNOWN",  # Cannot determine method without library context
                        auth_type=ApiAuthType.UNKNOWN,
                        source_file=str(file_path),
                        line_number=line_num
                    ))

        return api_calls

    def _remove_all_comments(self, content: str) -> str:
        """Remove all comments from content.

        Args:
            content: Source content

        Returns:
            Content with comments removed
        """
        # Remove single-line comments but be careful not to remove // in strings
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Simple approach: look for // but check if it's inside strings
            in_string = False
            string_char = None
            i = 0

            while i < len(line):
                char = line[i]

                if not in_string:
                    if char in ['"', "'"]:
                        in_string = True
                        string_char = char
                    elif char == '/' and i + 1 < len(line) and line[i + 1] == '/':
                        # Found comment outside of string, truncate here
                        line = line[:i]
                        break
                else:
                    if char == string_char and (i == 0 or line[i-1] != '\\'):
                        # End of string (not escaped)
                        in_string = False
                        string_char = None

                i += 1

            cleaned_lines.append(line)

        content = '\n'.join(cleaned_lines)

        # Remove multi-line comments /* ... */
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        return content