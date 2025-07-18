"""
Configuration file for pytest.
This file is automatically loaded by pytest before running tests.
"""
import sys
import os
import pytest
from pathlib import Path

# Add the src directory to sys.path
# This ensures that the package can be imported in tests even if not installed
project_root = Path(__file__).parent.parent.absolute()
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set secure test credentials (not defaults)
    os.environ["API_USERNAME"] = "test_user_secure"
    os.environ["API_PASSWORD"] = "test_password_secure_123!"
    
    yield
    
    # Clean up after tests
    if "API_USERNAME" in os.environ:
        del os.environ["API_USERNAME"]
    if "API_PASSWORD" in os.environ:
        del os.environ["API_PASSWORD"]
