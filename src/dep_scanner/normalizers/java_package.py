"""Normalizer for Java package names and Maven coordinates."""

from typing import Dict, Set


class JavaPackageNormalizer:
    """Normalizer for Java package names and Maven coordinates.
    
    This class provides utilities for mapping between Java package names
    (e.g., org.springframework.boot) and Maven coordinates (e.g., org.springframework.boot:spring-boot).
    
    It handles the inconsistencies between how packages are imported in Java code
    and how they're specified in dependency files like pom.xml and build.gradle.
    """
    
    # Mapping from package prefixes to Maven coordinates
    # This is a simplified mapping for common Java packages
    PACKAGE_TO_MAVEN_MAPPING: Dict[str, str] = {
        "org.springframework.boot": "org.springframework.boot:spring-boot",
        "org.springframework.boot.autoconfigure": "org.springframework.boot:spring-boot-autoconfigure",
        "org.springframework.web": "org.springframework:spring-web",
        "org.springframework.data": "org.springframework.data:spring-data-commons",
        "org.springframework.security": "org.springframework.security:spring-security-core",
        "com.google.common": "com.google.guava:guava",
        "com.google.gson": "com.google.code.gson:gson",
        "com.fasterxml.jackson": "com.fasterxml.jackson.core:jackson-core",
        "org.apache.commons.lang": "org.apache.commons:commons-lang3",
        "org.apache.commons.io": "org.apache.commons:commons-io",
        "org.apache.logging.log4j": "org.apache.logging.log4j:log4j-core",
        "org.slf4j": "org.slf4j:slf4j-api",
        "org.junit": "junit:junit",
        "org.mockito": "org.mockito:mockito-core",
        "javax.servlet": "javax.servlet:javax.servlet-api",
        "jakarta.servlet": "jakarta.servlet:jakarta.servlet-api",
    }
    
    # Mapping from Maven coordinates to package prefixes
    # This is the inverse of PACKAGE_TO_MAVEN_MAPPING
    MAVEN_TO_PACKAGE_MAPPING: Dict[str, str] = {
        "org.springframework.boot:spring-boot": "org.springframework.boot",
        "org.springframework.boot:spring-boot-autoconfigure": "org.springframework.boot.autoconfigure",
        "org.springframework:spring-web": "org.springframework.web",
        "org.springframework.data:spring-data-commons": "org.springframework.data",
        "org.springframework.security:spring-security-core": "org.springframework.security",
        "com.google.guava:guava": "com.google.common",
        "com.google.code.gson:gson": "com.google.gson",
        "com.fasterxml.jackson.core:jackson-core": "com.fasterxml.jackson",
        "org.apache.commons:commons-lang3": "org.apache.commons.lang",
        "org.apache.commons:commons-io": "org.apache.commons.io",
        "org.apache.logging.log4j:log4j-core": "org.apache.logging.log4j",
        "org.slf4j:slf4j-api": "org.slf4j",
        "junit:junit": "org.junit",
        "org.mockito:mockito-core": "org.mockito",
        "javax.servlet:javax.servlet-api": "javax.servlet",
        "jakarta.servlet:jakarta.servlet-api": "jakarta.servlet",
    }
    
    # Java standard library package prefixes
    JAVA_STANDARD_LIBRARY_PREFIXES: Set[str] = {
        "java.",
        "javax.",
        "sun.",
        "com.sun.",
        "jdk.",
    }
    
    def get_maven_coordinates_from_package(self, package_name: str) -> str:
        """Get Maven coordinates from a Java package name.
        
        Args:
            package_name: Java package name (e.g., org.springframework.boot)
            
        Returns:
            Maven coordinates (e.g., org.springframework.boot:spring-boot)
            or a best guess if the package is not in the mapping
        """
        if not package_name:
            return ""
        
        # Find the longest matching package prefix
        matching_prefix = ""
        for prefix in self.PACKAGE_TO_MAVEN_MAPPING:
            if package_name.startswith(prefix) and len(prefix) > len(matching_prefix):
                matching_prefix = prefix
        
        if matching_prefix:
            return self.PACKAGE_TO_MAVEN_MAPPING[matching_prefix]
        
        # If no mapping is found, try to guess the Maven coordinates
        # based on the package structure
        parts = package_name.split(".")
        if len(parts) >= 2:
            if len(parts) >= 4:
                # For packages with 4+ parts (e.g., io.github.user.project),
                # use the first three parts as groupId and the fourth as artifactId
                group_id = ".".join(parts[:3])
                artifact_id = parts[3]
            else:
                # For packages with 2-3 parts (e.g., com.example.app),
                # use the first two parts as groupId and the third as artifactId
                group_id = ".".join(parts[:2])
                # Use the third part as artifactId, or the second if there's no third
                artifact_id = parts[2] if len(parts) > 2 else parts[1]
            
            return f"{group_id}:{artifact_id}"
        
        # For single-part packages, use the same value for both groupId and artifactId
        return f"{package_name}:{package_name}"
    
    def get_package_from_maven_coordinates(self, maven_coordinates: str) -> str:
        """Get a Java package name from Maven coordinates.
        
        Args:
            maven_coordinates: Maven coordinates (e.g., org.springframework.boot:spring-boot)
            
        Returns:
            Java package name (e.g., org.springframework.boot)
            or a best guess if the coordinates are not in the mapping
        """
        if not maven_coordinates:
            return ""
        
        # Check if the coordinates are in the mapping
        if maven_coordinates in self.MAVEN_TO_PACKAGE_MAPPING:
            return self.MAVEN_TO_PACKAGE_MAPPING[maven_coordinates]
        
        # If no mapping is found, try to guess the package name
        # based on the Maven coordinates
        parts = maven_coordinates.split(":")
        if len(parts) >= 2:
            # Use the groupId as the package name
            return parts[0]
        
        # For coordinates without a colon, use the value as is
        return maven_coordinates
    
    def is_java_standard_library(self, package_name: str) -> bool:
        """Check if a package is part of the Java standard library.
        
        Args:
            package_name: Java package name (e.g., java.util)
            
        Returns:
            True if the package is part of the Java standard library, False otherwise
        """
        if not package_name:
            return False
        
        # Check if the package starts with any of the standard library prefixes
        for prefix in self.JAVA_STANDARD_LIBRARY_PREFIXES:
            if package_name.startswith(prefix):
                # Make sure it's not just the prefix itself
                return len(package_name) > len(prefix)
        
        return False
