"""Normalizers for Python package names.

This module provides utilities for normalizing Python package names to handle
inconsistencies between how packages are imported and how they're specified
in dependency files.
"""

import re
from typing import Dict, Optional, Set

# Known mappings between PyPI package names and import names
# Format: {import_name: pypi_name}
KNOWN_PACKAGE_MAPPINGS: Dict[str, str] = {
    # Common packages with different import vs PyPI names
    "bs4": "beautifulsoup4",
    "PIL": "pillow",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
    "googleapiclient": "google-api-python-client",
    "cairo": "pycairo",
    "gi": "pygobject",
    "ruamel.yaml": "ruamel-yaml",
    "yaml": "pyyaml",
    "psycopg2": "psycopg2-binary",  # Common variant
    "mysqlclient": "mysql-python",
    "httpx": "httpx",  # Same name but included for completeness
    "httplib2": "httplib2",
    "requests": "requests",
    "flask": "flask",
    "django": "django",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "scipy": "scipy",
    "tensorflow": "tensorflow",
    "torch": "torch",
    "pytest": "pytest",
    "coverage": "coverage",
}

# Inverse mapping for PyPI to import name
# Format: {pypi_name: import_name}
INVERSE_PACKAGE_MAPPINGS: Dict[str, str] = {v: k for k, v in KNOWN_PACKAGE_MAPPINGS.items()}


def normalize_import_name(import_name: str) -> str:
    """Normalize a Python import name to its canonical form.
    
    Args:
        import_name: The import name to normalize (e.g., "bs4", "sklearn")
        
    Returns:
        Normalized import name
    """
    # Handle namespace packages by taking the first part
    base_name = import_name.split('.')[0].lower()
    
    # Return the normalized name
    return base_name


def normalize_pypi_name(pypi_name: str) -> str:
    """Normalize a PyPI package name to its canonical form.
    
    Args:
        pypi_name: The PyPI package name to normalize (e.g., "beautifulsoup4", "scikit-learn")
        
    Returns:
        Normalized PyPI name
    """
    # Convert to lowercase
    name = pypi_name.lower()
    
    # Replace hyphens with underscores
    name = name.replace('-', '_')
    
    # Remove version specifiers if present
    name = re.sub(r'[<>=!~].*$', '', name).strip()
    
    return name


def get_pypi_name_from_import(import_name: str) -> Optional[str]:
    """Get the PyPI package name for a given import name.
    
    Args:
        import_name: The import name (e.g., "bs4", "sklearn")
        
    Returns:
        PyPI package name or None if not found
    """
    # Handle case sensitivity by normalizing the import name
    normalized_import = normalize_import_name(import_name)
    
    # Check if we have a direct mapping
    for key, value in KNOWN_PACKAGE_MAPPINGS.items():
        if normalized_import == key.lower():
            return value
    
    # If no mapping exists, the import name might be the same as the PyPI name
    return normalized_import


def get_import_name_from_pypi(pypi_name: str) -> Optional[str]:
    """Get the import name for a given PyPI package name.
    
    Args:
        pypi_name: The PyPI package name (e.g., "beautifulsoup4", "scikit-learn")
        
    Returns:
        Import name or None if not found
    """
    # Handle case sensitivity by normalizing the PyPI name
    normalized_pypi = normalize_pypi_name(pypi_name)
    
    # Check if we have a direct mapping
    for key, value in INVERSE_PACKAGE_MAPPINGS.items():
        if normalized_pypi == normalize_pypi_name(key):
            return value
    
    # If no mapping exists, the PyPI name might be the same as the import name
    return normalized_pypi


def is_package_match(import_name: str, pypi_name: str) -> bool:
    """Check if an import name matches a PyPI package name.
    
    Args:
        import_name: The import name (e.g., "bs4", "sklearn")
        pypi_name: The PyPI package name (e.g., "beautifulsoup4", "scikit-learn")
        
    Returns:
        True if they match, False otherwise
    """
    # Normalize both names
    normalized_import = normalize_import_name(import_name)
    normalized_pypi = normalize_pypi_name(pypi_name)
    
    # Direct match after normalization
    if normalized_import == normalized_pypi:
        return True
    
    # Check if import name maps to this PyPI name
    pypi_from_import = get_pypi_name_from_import(import_name)
    if pypi_from_import and normalize_pypi_name(pypi_from_import) == normalized_pypi:
        return True
    
    # Check if PyPI name maps to this import name
    import_from_pypi = get_import_name_from_pypi(pypi_name)
    if import_from_pypi and normalize_import_name(import_from_pypi) == normalized_import:
        return True
    
    return False


def normalize_package_names(package_names: Set[str], is_pypi: bool = True) -> Dict[str, str]:
    """Normalize a set of package names and return a mapping of original to normalized names.
    
    Args:
        package_names: Set of package names to normalize
        is_pypi: Whether the names are PyPI package names (True) or import names (False)
        
    Returns:
        Dictionary mapping original names to normalized names
    """
    result = {}
    
    for name in package_names:
        if is_pypi:
            result[name] = normalize_pypi_name(name)
        else:
            result[name] = normalize_import_name(name)
    
    return result
