"""Tests for the Gradle build file parser."""

import os
import tempfile
from pathlib import Path

from dep_scanner.parsers.gradle_build import GradleBuildParser
from dep_scanner.scanner import DependencyType


class TestGradleBuildParser:
    """Tests for the GradleBuildParser class."""
    
    def test_can_parse(self):
        """Test that the parser can parse Gradle build files."""
        parser = GradleBuildParser()
        
        # Should parse build.gradle files
        assert parser.can_parse(Path("build.gradle"))
        assert parser.can_parse(Path("path/to/build.gradle"))
        assert parser.can_parse(Path("build.gradle.kts"))
        assert parser.can_parse(Path("path/to/build.gradle.kts"))
        
        # Should not parse other files
        assert not parser.can_parse(Path("pom.xml"))
        assert not parser.can_parse(Path("requirements.txt"))
        assert not parser.can_parse(Path("pyproject.toml"))
    
    def test_parse_basic(self):
        """Test parsing a basic Gradle build file."""
        with tempfile.NamedTemporaryFile(suffix=".gradle", delete=False) as f:
            f.write(b"""
plugins {
    id 'java'
    id 'org.springframework.boot' version '2.5.0'
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web:2.5.0'
    implementation 'com.google.guava:guava:30.1-jre'
    testImplementation 'junit:junit:4.13.2'
}
""")
            file_path = Path(f.name)
        
        try:
            parser = GradleBuildParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 3
            
            # Check that the dependencies have the correct attributes
            spring_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-starter-web")
            assert spring_dep.version == "2.5.0"
            assert spring_dep.source_file == str(file_path)
            assert spring_dep.dependency_type == DependencyType.UNKNOWN
            
            guava_dep = next(d for d in dependencies if d.name == "com.google.guava:guava")
            assert guava_dep.version == "30.1-jre"
            
            junit_dep = next(d for d in dependencies if d.name == "junit:junit")
            assert junit_dep.version == "4.13.2"
        finally:
            os.unlink(file_path)
    
    def test_parse_kotlin_dsl(self):
        """Test parsing a Gradle Kotlin DSL build file."""
        with tempfile.NamedTemporaryFile(suffix=".gradle.kts", delete=False) as f:
            f.write(b"""
plugins {
    java
    id("org.springframework.boot") version "2.5.0"
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web:2.5.0")
    implementation("com.google.guava:guava:30.1-jre")
    testImplementation("junit:junit:4.13.2")
}
""")
            file_path = Path(f.name)
        
        try:
            parser = GradleBuildParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 3
            
            # Check that the dependencies have the correct attributes
            spring_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-starter-web")
            assert spring_dep.version == "2.5.0"
            
            guava_dep = next(d for d in dependencies if d.name == "com.google.guava:guava")
            assert guava_dep.version == "30.1-jre"
            
            junit_dep = next(d for d in dependencies if d.name == "junit:junit")
            assert junit_dep.version == "4.13.2"
        finally:
            os.unlink(file_path)
    
    def test_parse_with_variables(self):
        """Test parsing a Gradle build file with variables."""
        with tempfile.NamedTemporaryFile(suffix=".gradle", delete=False) as f:
            f.write(b"""
plugins {
    id 'java'
}

ext {
    springVersion = '2.5.0'
    junitVersion = '4.13.2'
}

dependencies {
    implementation "org.springframework.boot:spring-boot-starter-web:${springVersion}"
    testImplementation "junit:junit:${junitVersion}"
}
""")
            file_path = Path(f.name)
        
        try:
            parser = GradleBuildParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 2
            
            # Check that the dependencies have the correct attributes
            # Note: We don't resolve variables in this implementation
            spring_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-starter-web")
            assert spring_dep.version == "${springVersion}"
            
            junit_dep = next(d for d in dependencies if d.name == "junit:junit")
            assert junit_dep.version == "${junitVersion}"
        finally:
            os.unlink(file_path)
    
    def test_parse_different_dependency_formats(self):
        """Test parsing a Gradle build file with different dependency formats."""
        with tempfile.NamedTemporaryFile(suffix=".gradle", delete=False) as f:
            f.write(b"""
dependencies {
    // String notation
    implementation 'org.springframework.boot:spring-boot-starter-web:2.5.0'
    
    // Map notation
    implementation group: 'com.google.guava', name: 'guava', version: '30.1-jre'
    
    // No version
    implementation 'org.apache.commons:commons-lang3'
    
    // Different configurations
    api 'com.fasterxml.jackson.core:jackson-databind:2.12.3'
    compileOnly 'org.projectlombok:lombok:1.18.20'
    runtimeOnly 'mysql:mysql-connector-java:8.0.25'
    testImplementation 'junit:junit:4.13.2'
}
""")
            file_path = Path(f.name)
        
        try:
            parser = GradleBuildParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 7
            
            # Check string notation
            spring_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-starter-web")
            assert spring_dep.version == "2.5.0"
            
            # Check map notation
            guava_dep = next(d for d in dependencies if d.name == "com.google.guava:guava")
            assert guava_dep.version == "30.1-jre"
            
            # Check no version
            commons_dep = next(d for d in dependencies if d.name == "org.apache.commons:commons-lang3")
            assert commons_dep.version is None
            
            # Check different configurations
            jackson_dep = next(d for d in dependencies if d.name == "com.fasterxml.jackson.core:jackson-databind")
            assert jackson_dep.version == "2.12.3"
            
            lombok_dep = next(d for d in dependencies if d.name == "org.projectlombok:lombok")
            assert lombok_dep.version == "1.18.20"
            
            mysql_dep = next(d for d in dependencies if d.name == "mysql:mysql-connector-java")
            assert mysql_dep.version == "8.0.25"
            
            junit_dep = next(d for d in dependencies if d.name == "junit:junit")
            assert junit_dep.version == "4.13.2"
        finally:
            os.unlink(file_path)
    
    def test_parse_empty_file(self):
        """Test parsing an empty Gradle build file."""
        with tempfile.NamedTemporaryFile(suffix=".gradle", delete=False) as f:
            f.write(b"")
            file_path = Path(f.name)
        
        try:
            parser = GradleBuildParser()
            dependencies = parser.parse(file_path)
            
            # Should return an empty list for an empty file
            assert len(dependencies) == 0
        finally:
            os.unlink(file_path)
    
    def test_parse_no_dependencies(self):
        """Test parsing a Gradle build file with no dependencies section."""
        with tempfile.NamedTemporaryFile(suffix=".gradle", delete=False) as f:
            f.write(b"""
plugins {
    id 'java'
}

repositories {
    mavenCentral()
}

// No dependencies section
""")
            file_path = Path(f.name)
        
        try:
            parser = GradleBuildParser()
            dependencies = parser.parse(file_path)
            
            # Should return an empty list for a file with no dependencies
            assert len(dependencies) == 0
        finally:
            os.unlink(file_path)
