"""Tests for the Java package name normalizer."""

from dep_scanner.normalizers.java_package import JavaPackageNormalizer


class TestJavaPackageNormalizer:
    """Tests for the JavaPackageNormalizer class."""
    
    def test_get_maven_coordinates_from_package(self):
        """Test getting Maven coordinates from a Java package name."""
        normalizer = JavaPackageNormalizer()
        
        # Test common mappings
        assert normalizer.get_maven_coordinates_from_package("org.springframework.boot") == "org.springframework.boot:spring-boot"
        assert normalizer.get_maven_coordinates_from_package("com.google.common.collect") == "com.google.guava:guava"
        assert normalizer.get_maven_coordinates_from_package("org.junit") == "junit:junit"
        
        # Test packages not in the mapping
        assert normalizer.get_maven_coordinates_from_package("com.example.app") == "com.example:app"
        assert normalizer.get_maven_coordinates_from_package("io.github.user.project") == "io.github.user:project"
        
        # Test edge cases
        assert normalizer.get_maven_coordinates_from_package("") == ""
        assert normalizer.get_maven_coordinates_from_package("single") == "single:single"
    
    def test_get_package_from_maven_coordinates(self):
        """Test getting a Java package name from Maven coordinates."""
        normalizer = JavaPackageNormalizer()
        
        # Test common mappings
        assert normalizer.get_package_from_maven_coordinates("org.springframework.boot:spring-boot") == "org.springframework.boot"
        assert normalizer.get_package_from_maven_coordinates("com.google.guava:guava") == "com.google.common"
        assert normalizer.get_package_from_maven_coordinates("junit:junit") == "org.junit"
        
        # Test coordinates not in the mapping
        assert normalizer.get_package_from_maven_coordinates("com.example:app") == "com.example"
        assert normalizer.get_package_from_maven_coordinates("io.github.user:project") == "io.github.user"
        
        # Test edge cases
        assert normalizer.get_package_from_maven_coordinates("") == ""
        assert normalizer.get_package_from_maven_coordinates("single") == "single"
    
    def test_is_java_standard_library(self):
        """Test checking if a package is part of the Java standard library."""
        normalizer = JavaPackageNormalizer()
        
        # Test standard library packages
        assert normalizer.is_java_standard_library("java.util")
        assert normalizer.is_java_standard_library("java.io")
        assert normalizer.is_java_standard_library("java.lang")
        assert normalizer.is_java_standard_library("javax.swing")
        
        # Test non-standard library packages
        assert not normalizer.is_java_standard_library("org.springframework.boot")
        assert not normalizer.is_java_standard_library("com.google.common")
        assert not normalizer.is_java_standard_library("org.junit")
        
        # Test edge cases
        assert not normalizer.is_java_standard_library("")
        assert not normalizer.is_java_standard_library("java")  # Just "java" is not a standard library package
        assert not normalizer.is_java_standard_library("javax")  # Just "javax" is not a standard library package
