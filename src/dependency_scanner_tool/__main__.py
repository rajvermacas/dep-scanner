"""Main entry point for running the dependency scanner as a module."""

import sys
from pathlib import Path

# Add the src directory to sys.path
# This ensures that the package can be imported in tests even if not installed
project_root = Path(__file__).parent.parent.absolute()

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dependency_scanner_tool.cli import main

if __name__ == "__main__":
    main()
