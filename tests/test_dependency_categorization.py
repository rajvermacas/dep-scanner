"""Tests for the dependency categorization feature."""

import json
import tempfile
from pathlib import Path

import pytest

from dependency_scanner_tool.scanner import Dependency
from dependency_scanner_tool.categorization import DependencyCategorizer


def test_dependency_categorizer_init():
    """Test initialization of DependencyCategorizer."""
    # Test with valid configuration
    config = {
        "categories": {
            "A": ["requests", "flask", "django"],
            "B": ["numpy", "pandas", "matplotlib"],
            "C": ["pytest", "tox", "coverage"]
        }
    }
    
    categorizer = DependencyCategorizer(config)
    assert categorizer.categories == config["categories"]
    
    # Test with empty configuration
    categorizer = DependencyCategorizer({})
    assert categorizer.categories == {}
    
    # Test with None configuration
    categorizer = DependencyCategorizer(None)
    assert categorizer.categories == {}


def test_dependency_categorizer_from_json():
    """Test creating DependencyCategorizer from JSON file."""
    # Create a temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "categories": {
                "A": ["requests", "flask", "django"],
                "B": ["numpy", "pandas", "matplotlib"]
            }
        }, f)
    
    # Test loading from the file
    categorizer = DependencyCategorizer.from_json(Path(f.name))
    assert categorizer.categories == {
        "A": ["requests", "flask", "django"],
        "B": ["numpy", "pandas", "matplotlib"]
    }
    
    # Test with non-existent file
    with pytest.raises(FileNotFoundError):
        DependencyCategorizer.from_json(Path("non_existent_file.json"))
    
    # Test with invalid JSON
    invalid_json_path = Path(f.name).parent / "invalid.json"
    try:
        with open(invalid_json_path, 'w') as f2:
            f2.write("invalid json")
        
        with pytest.raises(json.JSONDecodeError):
            DependencyCategorizer.from_json(invalid_json_path)
    finally:
        # Clean up temporary files
        Path(f.name).unlink(missing_ok=True)
        invalid_json_path.unlink(missing_ok=True)


def test_categorize_dependency():
    """Test categorizing a single dependency."""
    config = {
        "categories": {
            "A": ["requests", "flask", "django"],
            "B": ["numpy", "pandas", "matplotlib"],
            "C": ["pytest", "tox", "coverage"]
        }
    }
    
    categorizer = DependencyCategorizer(config)
    
    # Test dependencies in category A
    for name in config["categories"]["A"]:
        dep = Dependency(name=name)
        categories = categorizer.categorize_dependency(dep)
        assert "A" in categories
        assert "B" not in categories
        assert "C" not in categories
    
    # Test dependencies in category B
    for name in config["categories"]["B"]:
        dep = Dependency(name=name)
        categories = categorizer.categorize_dependency(dep)
        assert "A" not in categories
        assert "B" in categories
        assert "C" not in categories
    
    # Test dependencies in category C
    for name in config["categories"]["C"]:
        dep = Dependency(name=name)
        categories = categorizer.categorize_dependency(dep)
        assert "A" not in categories
        assert "B" not in categories
        assert "C" in categories
    
    # Test dependency not in any category
    dep = Dependency(name="unknown-package")
    categories = categorizer.categorize_dependency(dep)
    assert categories == ["Uncategorized"]


def test_categorize_dependencies():
    """Test categorizing multiple dependencies."""
    config = {
        "categories": {
            "A": ["requests", "flask", "django"],
            "B": ["numpy", "pandas", "matplotlib"],
            "C": ["pytest", "tox", "coverage"]
        }
    }
    
    categorizer = DependencyCategorizer(config)
    
    dependencies = [
        Dependency(name="requests"),
        Dependency(name="numpy"),
        Dependency(name="pytest"),
        Dependency(name="unknown-package")
    ]
    
    result = categorizer.categorize_dependencies(dependencies)
    
    assert "A" in result
    assert "B" in result
    assert "C" in result
    assert "Uncategorized" in result
    
    assert len(result["A"]) == 1
    assert len(result["B"]) == 1
    assert len(result["C"]) == 1
    assert len(result["Uncategorized"]) == 1
    
    assert result["A"][0].name == "requests"
    assert result["B"][0].name == "numpy"
    assert result["C"][0].name == "pytest"
    assert result["Uncategorized"][0].name == "unknown-package"


def test_dependency_in_multiple_categories():
    """Test a dependency that belongs to multiple categories."""
    config = {
        "categories": {
            "A": ["requests", "flask", "django"],
            "B": ["requests", "numpy", "pandas"],
            "C": ["pytest", "tox", "coverage"]
        }
    }
    
    categorizer = DependencyCategorizer(config)
    
    # Test dependency in multiple categories
    dep = Dependency(name="requests")
    categories = categorizer.categorize_dependency(dep)
    assert "A" in categories
    assert "B" in categories
    assert "C" not in categories
    
    # Test categorizing multiple dependencies
    dependencies = [
        Dependency(name="requests"),
        Dependency(name="numpy"),
        Dependency(name="pytest")
    ]
    
    result = categorizer.categorize_dependencies(dependencies)
    
    assert "A" in result
    assert "B" in result
    assert "C" in result
    
    # requests should be in both A and B
    assert len(result["A"]) == 1
    assert len(result["B"]) == 2
    assert len(result["C"]) == 1
    
    assert result["A"][0].name == "requests"
    assert "requests" in [dep.name for dep in result["B"]]
    assert "numpy" in [dep.name for dep in result["B"]]
    assert result["C"][0].name == "pytest"
