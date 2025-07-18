"""Authentication middleware for the REST API."""

import base64
import binascii
import logging
import os
from typing import Optional

from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


logger = logging.getLogger(__name__)


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Authentication middleware."""
    
    def __init__(self, app, username: Optional[str] = None, password: Optional[str] = None):
        super().__init__(app)
        # Get credentials from environment or use defaults
        self.username = username or os.getenv("API_USERNAME", "admin")
        self.password = password or os.getenv("API_PASSWORD", "secret123")
        
        if not self.username or not self.password:
            raise ValueError("API_USERNAME and API_PASSWORD environment variables must be set")
    
    async def dispatch(self, request: Request, call_next):
        """Process the request with authentication."""
        # Skip authentication for health check in some cases (optional)
        # For now, we'll require auth for all endpoints as per security requirements
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"Missing Authorization header for {request.url}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # Parse Basic auth header
        try:
            scheme, credentials = auth_header.split(" ", 1)
            if scheme.lower() != "basic":
                logger.warning(f"Invalid authentication scheme: {scheme}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authentication scheme"},
                    headers={"WWW-Authenticate": "Basic"},
                )
            
            # Decode credentials
            try:
                decoded_credentials = base64.b64decode(credentials).decode("utf-8")
                username, password = decoded_credentials.split(":", 1)
            except (binascii.Error, UnicodeDecodeError, ValueError):
                logger.warning("Invalid authentication format")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authentication format"},
                    headers={"WWW-Authenticate": "Basic"},
                )
            
            # Validate credentials
            if username != self.username or password != self.password:
                logger.warning(f"Invalid credentials for user: {username}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid credentials"},
                    headers={"WWW-Authenticate": "Basic"},
                )
            
            # Authentication successful, proceed with request
            response = await call_next(request)
            return response
            
        except ValueError:
            logger.warning("Malformed Authorization header")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication format"},
                headers={"WWW-Authenticate": "Basic"},
            )


def verify_credentials(credentials: HTTPBasicCredentials) -> bool:
    """Verify HTTP Basic credentials."""
    expected_username = os.getenv("API_USERNAME", "admin")
    expected_password = os.getenv("API_PASSWORD", "secret123")
    
    return credentials.username == expected_username and credentials.password == expected_password


def get_current_user(credentials: HTTPBasicCredentials = Depends(HTTPBasic())) -> str:
    """Get the current authenticated user."""
    if not verify_credentials(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username