"""Tests for the DependencyClassifier class."""

from dep_scanner.scanner import Dependency, DependencyClassifier, DependencyType


def test_basic_classification():
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


def test_case_insensitive_classification():
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


def test_python_package_name_normalization():
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


def test_hyphen_underscore_equivalence():
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


def test_version_specifier_handling():
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


def test_classify_dependency_direct_match():
    """Test classifying a dependency with a direct match."""
    classifier = DependencyClassifier(
        allowed_list={"requests", "numpy", "pandas"},
        restricted_list={"insecure-package", "vulnerable-lib"}
    )
    
    # Test allowed dependencies
    dep = Dependency(name="requests")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="numpy")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    # Test restricted dependencies
    dep = Dependency(name="insecure-package")
    assert classifier.classify_dependency(dep) == DependencyType.RESTRICTED
    
    # Test unknown dependencies
    dep = Dependency(name="some-other-package")
    assert classifier.classify_dependency(dep) == DependencyType.UNKNOWN


def test_classify_dependency_with_version():
    """Test classifying a dependency with a version."""
    classifier = DependencyClassifier(
        allowed_list={"requests", "numpy", "pandas"},
        restricted_list={"insecure-package", "vulnerable-lib"}
    )
    
    # Test with version
    dep = Dependency(name="requests", version="2.25.1")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="insecure-package", version="1.0.0")
    assert classifier.classify_dependency(dep) == DependencyType.RESTRICTED


def test_classify_dependency_with_source_file():
    """Test classifying a dependency with a source file."""
    classifier = DependencyClassifier(
        allowed_list={"requests", "numpy", "pandas"},
        restricted_list={"insecure-package", "vulnerable-lib"}
    )
    
    # Test with source file
    dep = Dependency(name="requests", source_file="requirements.txt")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="insecure-package", source_file="requirements.txt")
    assert classifier.classify_dependency(dep) == DependencyType.RESTRICTED


def test_classify_dependency_with_type():
    """Test classifying a dependency with a type."""
    classifier = DependencyClassifier(
        allowed_list={"requests", "numpy", "pandas"},
        restricted_list={"insecure-package", "vulnerable-lib"}
    )
    
    # Test with type
    dep = Dependency(name="requests", dependency_type=DependencyType.UNKNOWN)
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="insecure-package", dependency_type=DependencyType.UNKNOWN)
    assert classifier.classify_dependency(dep) == DependencyType.RESTRICTED


def test_classify_dependency_with_version_specifiers():
    """Test classifying a dependency with version specifiers."""
    classifier = DependencyClassifier(
        allowed_list={"requests", "numpy", "pandas"},
        restricted_list={"insecure-package", "vulnerable-lib", "deprecated-lib"}
    )
    
    # Test with version specifiers in the name
    assert classifier.classify_dependency(Dependency(name="requests>=2.25.1")) == DependencyType.ALLOWED
    assert classifier.classify_dependency(Dependency(name="numpy==1.20.1")) == DependencyType.ALLOWED
    
    assert classifier.classify_dependency(Dependency(name="insecure-package~=1.0.0")) == DependencyType.RESTRICTED
    assert classifier.classify_dependency(Dependency(name="deprecated-lib>0.1.0")) == DependencyType.RESTRICTED


def test_classify_dependency_python_package_variations():
    """Test classifying Python dependencies with package name variations."""
    classifier = DependencyClassifier(
        allowed_list={"requests", "beautifulsoup4", "scikit-learn"},
        restricted_list={"insecure-package", "vulnerable-lib"}
    )
    
    # Test package name variations
    dep = Dependency(name="bs4")  # beautifulsoup4 import name
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="sklearn")  # scikit-learn import name
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    # Test case insensitivity
    dep = Dependency(name="BeautifulSoup4")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED


def test_classify_dependency_java_package_variations():
    """Test classifying Java dependencies with package name variations."""
    classifier = DependencyClassifier(
        allowed_list={
            "org.springframework.boot:spring-boot", 
            "com.google.guava:guava",
            "junit:junit"
        },
        restricted_list={
            "com.insecure:vulnerable-library", 
            "org.outdated:insecure-component"
        }
    )
    
    # Test direct matches
    dep = Dependency(name="org.springframework.boot:spring-boot")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="com.google.guava:guava")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="com.insecure:vulnerable-library")
    assert classifier.classify_dependency(dep) == DependencyType.RESTRICTED
    
    # Test package variations
    # A dependency with the same group ID but different artifact ID
    dep = Dependency(name="org.springframework.boot:spring-boot-autoconfigure")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    # A dependency with a different group ID
    dep = Dependency(name="org.apache.commons:commons-lang3")
    assert classifier.classify_dependency(dep) == DependencyType.UNKNOWN


def test_classify_mixed_dependencies():
    """Test classifying a mix of Python and Java dependencies."""
    classifier = DependencyClassifier(
        allowed_list={
            "requests", 
            "numpy", 
            "org.springframework.boot:spring-boot", 
            "com.google.guava:guava"
        },
        restricted_list={
            "insecure-package", 
            "com.insecure:vulnerable-library"
        }
    )
    
    # Test Python dependencies
    dep = Dependency(name="requests")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="insecure-package")
    assert classifier.classify_dependency(dep) == DependencyType.RESTRICTED
    
    # Test Java dependencies
    dep = Dependency(name="org.springframework.boot:spring-boot")
    assert classifier.classify_dependency(dep) == DependencyType.ALLOWED
    
    dep = Dependency(name="com.insecure:vulnerable-library")
    assert classifier.classify_dependency(dep) == DependencyType.RESTRICTED
