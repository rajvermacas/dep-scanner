"""
Configuration file for pytest.
This file is automatically loaded by pytest before running tests.
"""
import sys
from pathlib import Path

# Add the src directory to sys.path
# This ensures that the package can be imported in tests even if not installed
project_root = Path(__file__).parent.parent.absolute()
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
