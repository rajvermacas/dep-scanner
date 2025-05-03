"""Tests for the Maven pom.xml parser."""

import os
import tempfile
from pathlib import Path

import pytest

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.maven_pom import MavenPomParser
from dep_scanner.scanner import DependencyType


class TestMavenPomParser:
    """Tests for the MavenPomParser class."""
    
    def test_can_parse(self):
        """Test that the parser can parse Maven pom.xml files."""
        parser = MavenPomParser()
        
        # Should parse pom.xml files
        assert parser.can_parse(Path("pom.xml"))
        assert parser.can_parse(Path("path/to/pom.xml"))
        
        # Should not parse other files
        assert not parser.can_parse(Path("build.gradle"))
        assert not parser.can_parse(Path("requirements.txt"))
        assert not parser.can_parse(Path("pyproject.toml"))
    
    def test_parse_basic(self):
        """Test parsing a basic Maven pom.xml file."""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  
  <groupId>com.example</groupId>
  <artifactId>my-app</artifactId>
  <version>1.0-SNAPSHOT</version>
  
  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.12</version>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>org.apache.commons</groupId>
      <artifactId>commons-lang3</artifactId>
      <version>3.12.0</version>
    </dependency>
  </dependencies>
</project>
""")
            file_path = Path(f.name)
        
        try:
            parser = MavenPomParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 2
            
            # Check that the dependencies have the correct attributes
            junit_dep = next(d for d in dependencies if d.name == "junit:junit")
            assert junit_dep.version == "4.12"
            assert junit_dep.source_file == str(file_path)
            assert junit_dep.dependency_type == DependencyType.UNKNOWN
            
            commons_dep = next(d for d in dependencies if d.name == "org.apache.commons:commons-lang3")
            assert commons_dep.version == "3.12.0"
            assert commons_dep.source_file == str(file_path)
        finally:
            os.unlink(file_path)
    
    def test_parse_with_properties(self):
        """Test parsing a Maven pom.xml file with properties."""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  
  <groupId>com.example</groupId>
  <artifactId>my-app</artifactId>
  <version>1.0-SNAPSHOT</version>
  
  <properties>
    <junit.version>4.12</junit.version>
    <commons.version>3.12.0</commons.version>
  </properties>
  
  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>${junit.version}</version>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>org.apache.commons</groupId>
      <artifactId>commons-lang3</artifactId>
      <version>${commons.version}</version>
    </dependency>
  </dependencies>
</project>
""")
            file_path = Path(f.name)
        
        try:
            parser = MavenPomParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 2
            
            # Check that the properties were resolved correctly
            junit_dep = next(d for d in dependencies if d.name == "junit:junit")
            assert junit_dep.version == "4.12"
            
            commons_dep = next(d for d in dependencies if d.name == "org.apache.commons:commons-lang3")
            assert commons_dep.version == "3.12.0"
        finally:
            os.unlink(file_path)
    
    def test_parse_with_parent_properties(self):
        """Test parsing a Maven pom.xml file with parent properties."""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.5.0</version>
  </parent>
  
  <groupId>com.example</groupId>
  <artifactId>my-app</artifactId>
  <version>1.0-SNAPSHOT</version>
  
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
      <!-- No version specified, should inherit from parent -->
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
      <!-- No version specified, should inherit from parent -->
    </dependency>
  </dependencies>
</project>
""")
            file_path = Path(f.name)
        
        try:
            parser = MavenPomParser()
            dependencies = parser.parse(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 3  # 2 direct deps + 1 parent dep
            
            # Check that the parent dependency was included
            parent_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-starter-parent")
            assert parent_dep.version == "2.5.0"
            
            # Check that the direct dependencies were parsed correctly
            web_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-starter-web")
            assert web_dep.version is None  # Version is managed by parent
            
            test_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-starter-test")
            assert test_dep.version is None  # Version is managed by parent
        finally:
            os.unlink(file_path)
    
    def test_parse_empty_file(self):
        """Test parsing an empty Maven pom.xml file."""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"")
            file_path = Path(f.name)
        
        try:
            parser = MavenPomParser()
            with pytest.raises(ParsingError):
                parser.parse(file_path)
        finally:
            os.unlink(file_path)
    
    def test_parse_invalid_xml(self):
        """Test parsing an invalid XML file."""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <invalid xml>
</project>
""")
            file_path = Path(f.name)
        
        try:
            parser = MavenPomParser()
            with pytest.raises(ParsingError):
                parser.parse(file_path)
        finally:
            os.unlink(file_path)
    
    def test_parse_no_dependencies(self):
        """Test parsing a Maven pom.xml file with no dependencies."""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  
  <groupId>com.example</groupId>
  <artifactId>my-app</artifactId>
  <version>1.0-SNAPSHOT</version>
  
  <!-- No dependencies section -->
</project>
""")
            file_path = Path(f.name)
        
        try:
            parser = MavenPomParser()
            dependencies = parser.parse(file_path)
            
            # Should return an empty list for a file with no dependencies
            assert len(dependencies) == 0
        finally:
            os.unlink(file_path)
