"""Tests for the Python package name normalizer."""

from dep_scanner.normalizers.python_package import (
    normalize_import_name,
    normalize_pypi_name,
    get_pypi_name_from_import,
    get_import_name_from_pypi,
    is_package_match,
    normalize_package_names
)


class TestPythonPackageNormalizer:
    """Tests for the Python package name normalizer."""
    
    def test_normalize_import_name(self):
        """Test normalizing import names."""
        # Test basic normalization
        assert normalize_import_name("bs4") == "bs4"
        assert normalize_import_name("BS4") == "bs4"  # Case normalization
        
        # Test namespace packages
        assert normalize_import_name("google.cloud") == "google"
        assert normalize_import_name("django.contrib.auth") == "django"
    
    def test_normalize_pypi_name(self):
        """Test normalizing PyPI package names."""
        # Test basic normalization
        assert normalize_pypi_name("beautifulsoup4") == "beautifulsoup4"
        assert normalize_pypi_name("BeautifulSoup4") == "beautifulsoup4"  # Case normalization
        
        # Test hyphen replacement
        assert normalize_pypi_name("scikit-learn") == "scikit_learn"
        
        # Test version specifier removal
        assert normalize_pypi_name("django>=2.0") == "django"
        assert normalize_pypi_name("flask==1.0.0") == "flask"
        assert normalize_pypi_name("requests~=2.25.0") == "requests"
    
    def test_get_pypi_name_from_import(self):
        """Test getting PyPI package name from import name."""
        # Test known mappings
        assert get_pypi_name_from_import("bs4") == "beautifulsoup4"
        assert get_pypi_name_from_import("PIL") == "pillow"
        assert get_pypi_name_from_import("sklearn") == "scikit-learn"
        
        # Test case insensitivity
        assert get_pypi_name_from_import("BS4") == "beautifulsoup4"
        
        # Test direct matches
        assert get_pypi_name_from_import("requests") == "requests"
        assert get_pypi_name_from_import("flask") == "flask"
        
        # Test namespace packages
        assert get_pypi_name_from_import("google.cloud") == "google"
    
    def test_get_import_name_from_pypi(self):
        """Test getting import name from PyPI package name."""
        # Test known mappings
        assert get_import_name_from_pypi("beautifulsoup4") == "bs4"
        assert get_import_name_from_pypi("pillow") == "PIL"
        assert get_import_name_from_pypi("scikit-learn") == "sklearn"
        
        # Test case insensitivity
        assert get_import_name_from_pypi("BeautifulSoup4") == "bs4"
        
        # Test direct matches
        assert get_import_name_from_pypi("requests") == "requests"
        assert get_import_name_from_pypi("flask") == "flask"
    
    def test_is_package_match(self):
        """Test package name matching."""
        # Test direct matches
        assert is_package_match("requests", "requests") is True
        assert is_package_match("flask", "flask") is True
        
        # Test known mappings
        assert is_package_match("bs4", "beautifulsoup4") is True
        assert is_package_match("PIL", "pillow") is True
        assert is_package_match("sklearn", "scikit-learn") is True
        
        # Test case insensitivity
        assert is_package_match("BS4", "beautifulsoup4") is True
        assert is_package_match("bs4", "BeautifulSoup4") is True
        
        # Test hyphen/underscore equivalence
        assert is_package_match("scikit_learn", "scikit-learn") is True
        
        # Test non-matches
        assert is_package_match("requests", "flask") is False
        assert is_package_match("bs4", "pillow") is False
    
    def test_normalize_package_names(self):
        """Test normalizing a set of package names."""
        # Test PyPI package names
        pypi_names = {"beautifulsoup4", "scikit-learn", "Django>=2.0"}
        normalized = normalize_package_names(pypi_names, is_pypi=True)
        
        assert normalized["beautifulsoup4"] == "beautifulsoup4"
        assert normalized["scikit-learn"] == "scikit_learn"
        assert normalized["Django>=2.0"] == "django"
        
        # Test import names
        import_names = {"bs4", "sklearn", "django.contrib"}
        normalized = normalize_package_names(import_names, is_pypi=False)
        
        assert normalized["bs4"] == "bs4"
        assert normalized["sklearn"] == "sklearn"
        assert normalized["django.contrib"] == "django"
