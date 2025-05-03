"""Tests for the DependencyClassifier class."""

from dep_scanner.scanner import Dependency, DependencyClassifier, DependencyType


class TestDependencyClassifier:
    """Tests for the DependencyClassifier class."""
    
    def test_basic_classification(self):
        """Test basic dependency classification."""
        # Create a classifier with some allowed and restricted dependencies
        allowed = {"requests", "flask", "django"}
        restricted = {"insecure-package", "deprecated-lib"}
        
        classifier = DependencyClassifier(allowed, restricted)
        
        # Test allowed dependencies
        for name in allowed:
            dep = Dependency(name=name)
            assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
        
        # Test restricted dependencies
        for name in restricted:
            dep = Dependency(name=name)
            assert classifier.classify_dependency(dep) == DependencyType.RESTRICTED
        
        # Test unknown dependencies
        unknown_deps = ["numpy", "pandas", "matplotlib"]
        for name in unknown_deps:
            dep = Dependency(name=name)
            assert classifier.classify_dependency(dep) == DependencyType.UNKNOWN
    
    def test_case_insensitive_classification(self):
        """Test case-insensitive dependency classification."""
        # Create a classifier with some allowed and restricted dependencies
        allowed = {"Requests", "Flask", "Django"}
        restricted = {"Insecure-Package", "Deprecated-Lib"}
        
        classifier = DependencyClassifier(allowed, restricted)
        
        # Test with different case
        assert classifier.classify_dependency(Dependency(name="requests")) == DependencyType.ALLOWED
        assert classifier.classify_dependency(Dependency(name="FLASK")) == DependencyType.ALLOWED
        assert classifier.classify_dependency(Dependency(name="Django")) == DependencyType.ALLOWED
        
        assert classifier.classify_dependency(Dependency(name="insecure-package")) == DependencyType.RESTRICTED
        assert classifier.classify_dependency(Dependency(name="DEPRECATED-LIB")) == DependencyType.RESTRICTED
    
    def test_python_package_name_normalization(self):
        """Test Python package name normalization in dependency classification."""
        # Create a classifier with some allowed and restricted dependencies
        allowed = {"beautifulsoup4", "scikit-learn"}
        restricted = {"pillow", "python-dotenv"}
        
        classifier = DependencyClassifier(allowed, restricted)
        
        # Test with import names instead of PyPI names
        assert classifier.classify_dependency(Dependency(name="bs4")) == DependencyType.ALLOWED
        assert classifier.classify_dependency(Dependency(name="sklearn")) == DependencyType.ALLOWED
        
        assert classifier.classify_dependency(Dependency(name="PIL")) == DependencyType.RESTRICTED
        assert classifier.classify_dependency(Dependency(name="dotenv")) == DependencyType.RESTRICTED
    
    def test_hyphen_underscore_equivalence(self):
        """Test hyphen/underscore equivalence in dependency classification."""
        # Create a classifier with some allowed and restricted dependencies
        allowed = {"scikit-learn", "python-dateutil"}
        restricted = {"python-dotenv", "google-api-python-client"}
        
        classifier = DependencyClassifier(allowed, restricted)
        
        # Test with underscores instead of hyphens
        assert classifier.classify_dependency(Dependency(name="scikit_learn")) == DependencyType.ALLOWED
        assert classifier.classify_dependency(Dependency(name="python_dateutil")) == DependencyType.ALLOWED
        
        assert classifier.classify_dependency(Dependency(name="python_dotenv")) == DependencyType.RESTRICTED
        assert classifier.classify_dependency(Dependency(name="google_api_python_client")) == DependencyType.RESTRICTED
    
    def test_version_specifier_handling(self):
        """Test handling of version specifiers in dependency classification."""
        # Create a classifier with some allowed and restricted dependencies
        allowed = {"django", "flask"}
        restricted = {"insecure-package", "deprecated-lib"}
        
        classifier = DependencyClassifier(allowed, restricted)
        
        # Test with version specifiers
        assert classifier.classify_dependency(Dependency(name="django>=2.0")) == DependencyType.ALLOWED
        assert classifier.classify_dependency(Dependency(name="flask==1.0.0")) == DependencyType.ALLOWED
        
        assert classifier.classify_dependency(Dependency(name="insecure-package~=1.0.0")) == DependencyType.RESTRICTED
        assert classifier.classify_dependency(Dependency(name="deprecated-lib>0.1.0")) == DependencyType.RESTRICTED
