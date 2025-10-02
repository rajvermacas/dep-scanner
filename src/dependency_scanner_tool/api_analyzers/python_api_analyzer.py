"""Analyzer for Python REST API calls."""

import ast
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from dependency_scanner_tool.api_analyzers.base import ApiCall, ApiCallAnalyzer, ApiAuthType
from dependency_scanner_tool.exceptions import ParsingError


class PythonApiCallAnalyzer(ApiCallAnalyzer):
    """Analyzer for Python REST API calls."""
    
    # Define supported file extensions
    supported_extensions: Set[str] = {".py"}
    
    # Mapping of common HTTP libraries and their functions
    HTTP_LIBRARIES = {
        "requests": {
            "get": "GET",
            "post": "POST",
            "put": "PUT",
            "delete": "DELETE",
            "patch": "PATCH",
            "head": "HEAD",
            "options": "OPTIONS",
            "request": None,  # Method determined by args
        },
        "urllib.request": {
            "urlopen": "GET",  # Default is GET but can be changed
            "Request": None,
        },
        "http.client": {
            "HTTPConnection": None,
            "HTTPSConnection": None,
        },
        "httpx": {
            "get": "GET",
            "post": "POST",
            "put": "PUT",
            "delete": "DELETE",
            "patch": "PATCH",
            "head": "HEAD",
            "options": "OPTIONS",
            "request": None,
        },
        "aiohttp": {
            "ClientSession": None,
        }
    }
    
    def analyze(self, file_path: Path) -> List[ApiCall]:
        """Analyze Python file for REST API calls.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of API calls found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        if not file_path.exists():
            raise ParsingError(file_path, f"File does not exist: {file_path}")
        
        api_calls = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Try to normalize indentation to fix common syntax errors
                normalized_content = self._normalize_indentation(content)
                
                # Parse the Python file
                try:
                    tree = ast.parse(normalized_content)
                    
                    # Extract API calls using AST
                    api_calls = self._extract_api_calls_from_ast(tree, file_path)
                except SyntaxError as e:
                    logging.warning(f"Syntax error in {file_path}: {e}")
                    
                    # Fall back to regex-based extraction for files with syntax errors
                    api_calls = self._extract_api_calls_with_regex(content, file_path)
        except Exception as e:
            logging.warning(f"Error analyzing Python API calls in {file_path}: {str(e)}")
            # Don't raise the exception, just return an empty list
            return []
        
        return api_calls
    
    def _extract_api_calls_from_ast(self, tree: ast.Module, file_path: Path) -> List[ApiCall]:
        """Extract API calls from an AST.

        Args:
            tree: AST of the Python file
            file_path: Path to the source file

        Returns:
            List of API calls found in the file
        """
        api_calls = []
        found_urls = set()  # Track URLs to avoid duplicates

        # Track imported HTTP libraries and their aliases
        imports = {}

        # First pass: collect imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    module_name = name.name
                    alias = name.asname or module_name

                    # Check if this is a known HTTP library
                    if module_name in self.HTTP_LIBRARIES:
                        imports[alias] = module_name

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module

                    for name in node.names:
                        # Handle cases like 'from requests import get, post'
                        if module_name in self.HTTP_LIBRARIES and name.name in self.HTTP_LIBRARIES[module_name]:
                            alias = name.asname or name.name
                            imports[alias] = (module_name, name.name)

        # Second pass: find library-specific API calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                api_call = self._process_call_node(node, imports, file_path)
                if api_call:
                    key = (api_call.url, api_call.line_number)
                    if key not in found_urls:
                        found_urls.add(key)
                        api_calls.append(api_call)

        # Third pass: find any URL strings (generic matching)
        for node in ast.walk(tree):
            url = None
            line_num = getattr(node, 'lineno', None)

            # Check for string constants that look like URLs
            if isinstance(node, ast.Str):
                url = node.s
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                url = node.value

            # If we found a URL-like string, create an API call
            if url and isinstance(url, str) and (url.startswith('http://') or url.startswith('https://')):
                key = (url, line_num)
                if key not in found_urls:
                    found_urls.add(key)
                    api_calls.append(ApiCall(
                        url=url,
                        http_method="UNKNOWN",  # Cannot determine method without library context
                        auth_type=ApiAuthType.UNKNOWN,
                        source_file=str(file_path),
                        line_number=line_num
                    ))

        return api_calls
    
    def _process_call_node(self, node: ast.Call, imports: Dict[str, Any], file_path: Path) -> Optional[ApiCall]:
        """Process a call node to extract API call information.
        
        Args:
            node: Call node from AST
            imports: Dictionary of imported HTTP libraries and their aliases
            file_path: Path to the source file
            
        Returns:
            ApiCall object if an API call is detected, None otherwise
        """
        # Get the function being called
        if isinstance(node.func, ast.Attribute):
            # Handle calls like requests.get()
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                function_name = node.func.attr
                
                # Check if this is a known HTTP library
                if module_name in imports and imports[module_name] in self.HTTP_LIBRARIES:
                    actual_module = imports[module_name]
                    
                    # Check if this is a known HTTP function
                    if function_name in self.HTTP_LIBRARIES[actual_module]:
                        return self._extract_api_call_from_node(node, actual_module, function_name, file_path)
                
                # Direct check for known libraries (without import tracking)
                elif module_name in self.HTTP_LIBRARIES and function_name in self.HTTP_LIBRARIES[module_name]:
                    return self._extract_api_call_from_node(node, module_name, function_name, file_path)
        
        elif isinstance(node.func, ast.Name):
            # Handle direct function calls from imports like 'from requests import get'
            function_name = node.func.id
            
            if function_name in imports and isinstance(imports[function_name], tuple):
                module_name, actual_function = imports[function_name]
                
                # Check if this is a known HTTP library and function
                if module_name in self.HTTP_LIBRARIES and actual_function in self.HTTP_LIBRARIES[module_name]:
                    return self._extract_api_call_from_node(node, module_name, actual_function, file_path)
        
        return None
    
    def _extract_api_call_from_node(self, node: ast.Call, module_name: str, function_name: str, file_path: Path) -> Optional[ApiCall]:
        """Extract API call details from a function call node.
        
        Args:
            node: Call node from AST
            module_name: Name of the HTTP library module
            function_name: Name of the function being called
            file_path: Path to the source file
            
        Returns:
            ApiCall object if URL information can be extracted, None otherwise
        """
        url = None
        http_method = self.HTTP_LIBRARIES[module_name].get(function_name)
        auth_type = ApiAuthType.UNKNOWN
        
        # Extract the URL from positional arguments
        for i, arg in enumerate(node.args):
            if i == 0 and isinstance(arg, ast.Str):
                url = arg.s
                break
            elif i == 0 and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                # For Python 3.8+ where string literals are represented as ast.Constant
                url = arg.value
                break
        
        # If no URL found in positional args, look in keyword arguments
        if not url:
            for keyword in node.keywords:
                if keyword.arg == 'url':
                    if isinstance(keyword.value, ast.Str):
                        url = keyword.value.s
                        break
                    elif isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                        url = keyword.value.value
                        break
        
        # Try to determine the HTTP method if not already known
        if not http_method:
            for keyword in node.keywords:
                if keyword.arg == 'method':
                    if isinstance(keyword.value, ast.Str):
                        http_method = keyword.value.s
                        break
                    elif isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                        http_method = keyword.value.value
                        break
        
        # Try to determine authentication type
        for keyword in node.keywords:
            if keyword.arg == 'auth':
                auth_type = ApiAuthType.BASIC
            elif keyword.arg == 'headers' and isinstance(keyword.value, ast.Dict):
                # Look for Authorization header
                for i, key in enumerate(keyword.value.keys):
                    if isinstance(key, ast.Str) and key.s.lower() == 'authorization':
                        value = keyword.value.values[i]
                        if isinstance(value, ast.Str):
                            if value.s.lower().startswith('bearer'):
                                auth_type = ApiAuthType.TOKEN
                            elif value.s.lower().startswith('basic'):
                                auth_type = ApiAuthType.BASIC
                            else:
                                auth_type = ApiAuthType.API_KEY
                    elif isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value.lower() == 'authorization':
                        value = keyword.value.values[i]
                        if isinstance(value, ast.Constant) and isinstance(value.value, str):
                            if value.value.lower().startswith('bearer'):
                                auth_type = ApiAuthType.TOKEN
                            elif value.value.lower().startswith('basic'):
                                auth_type = ApiAuthType.BASIC
                            else:
                                auth_type = ApiAuthType.API_KEY
        
        if url:
            return ApiCall(
                url=url,
                http_method=http_method,
                auth_type=auth_type,
                source_file=str(file_path),
                line_number=getattr(node, 'lineno', None)
            )
        
        return None
    
    def _extract_api_calls_with_regex(self, content: str, file_path: Path) -> List[ApiCall]:
        """Extract API calls using regex (fallback method).

        Args:
            content: Content of the Python file
            file_path: Path to the source file

        Returns:
            List of API calls found in the file
        """
        api_calls = []

        # Regex patterns for common HTTP library calls
        library_patterns = [
            # requests.get('https://example.com')
            r'requests\.(get|post|put|delete|patch|head|options)\s*\(\s*[\'"]([^\'"]+)[\'"]',
            # requests.request('GET', 'https://example.com')
            r'requests\.request\s*\(\s*[\'"]([A-Z]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]',
            # urllib.request.urlopen('https://example.com')
            r'urllib\.request\.urlopen\s*\(\s*[\'"]([^\'"]+)[\'"]',
            # httpx.get('https://example.com')
            r'httpx\.(get|post|put|delete|patch|head|options)\s*\(\s*[\'"]([^\'"]+)[\'"]',
        ]

        # Generic URL pattern to catch any http(s) URLs in the code
        # Matches URLs in quotes: "https://..." or 'https://...'
        generic_url_pattern = r'[\'"]((https?://[^\'"]+))[\'"]'

        # Extract line by line for better line number tracking
        lines = content.split('\n')
        found_urls = set()  # Track URLs to avoid duplicates

        for line_num, line in enumerate(lines, 1):
            # First try library-specific patterns
            for pattern in library_patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if len(match) == 2:
                        if pattern.startswith('requests.request'):
                            # requests.request('METHOD', 'URL')
                            http_method, url = match
                        else:
                            # requests.get('URL')
                            http_method, url = match[0].upper(), match[1]

                        key = (url, line_num)
                        if key not in found_urls:
                            found_urls.add(key)
                            api_calls.append(ApiCall(
                                url=url,
                                http_method=http_method,
                                auth_type=ApiAuthType.UNKNOWN,
                                source_file=str(file_path),
                                line_number=line_num
                            ))

            # Then look for generic URLs not caught by library patterns
            generic_matches = re.findall(generic_url_pattern, line)
            for match in generic_matches:
                url = match[0]  # Full URL
                key = (url, line_num)
                if key not in found_urls:
                    found_urls.add(key)
                    api_calls.append(ApiCall(
                        url=url,
                        http_method="UNKNOWN",  # Cannot determine method without library context
                        auth_type=ApiAuthType.UNKNOWN,
                        source_file=str(file_path),
                        line_number=line_num
                    ))

        return api_calls
    
    def _normalize_indentation(self, content: str) -> str:
        """Normalize indentation to handle some syntax errors.
        
        Args:
            content: Content of the Python file
            
        Returns:
            Normalized content
        """
        try:
            # First try to parse without normalization
            ast.parse(content)
            return content
        except SyntaxError:
            # Only try to normalize if there's a syntax error
            try:
                lines = content.split('\n')
                normalized_lines = []
                
                for line in lines:
                    stripped = line.lstrip()
                    
                    # Skip empty lines and comments
                    if not stripped or stripped.startswith('#'):
                        normalized_lines.append(line)
                        continue
                    
                    # Keep original line if it's valid
                    normalized_lines.append(line)
                
                return '\n'.join(normalized_lines)
            except Exception as e:
                logging.debug(f"Error during indentation normalization: {e}")
                return content  # Return original content if normalization fails
