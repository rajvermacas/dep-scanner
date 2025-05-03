"""Tests for the Java import statement analyzer."""

import os
import tempfile
from pathlib import Path

from dep_scanner.analyzers.java_analyzer import JavaImportAnalyzer
from dep_scanner.scanner import DependencyType


class TestJavaImportAnalyzer:
    """Tests for the JavaImportAnalyzer class."""
    
    def test_can_analyze(self):
        """Test that the analyzer can analyze Java files."""
        analyzer = JavaImportAnalyzer()
        
        # Should analyze Java files
        assert analyzer.can_analyze(Path("Main.java"))
        assert analyzer.can_analyze(Path("path/to/Main.java"))
        
        # Should not analyze other files
        assert not analyzer.can_analyze(Path("main.py"))
        assert not analyzer.can_analyze(Path("index.js"))
        assert not analyzer.can_analyze(Path("style.css"))
    
    def test_analyze_basic_imports(self):
        """Test analyzing a Java file with basic imports."""
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False) as f:
            f.write(b"""
package com.example.app;

import java.util.List;
import java.util.ArrayList;
import java.io.IOException;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import com.google.common.collect.ImmutableList;

public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
        List<String> list = new ArrayList<>();
        ImmutableList<String> immutableList = ImmutableList.of("item");
    }
}
""")
            file_path = Path(f.name)
        
        try:
            analyzer = JavaImportAnalyzer()
            dependencies = analyzer.analyze(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 3
            
            # Check standard library imports (should be ignored)
            java_util_deps = [d for d in dependencies if d.name.startswith("java.")]
            assert len(java_util_deps) == 0
            
            # Check third-party imports
            spring_deps = [d for d in dependencies if d.name.startswith("org.springframework")]
            assert len(spring_deps) == 2
            
            spring_boot_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot")
            assert spring_boot_dep.version is None
            assert spring_boot_dep.source_file == str(file_path)
            assert spring_boot_dep.dependency_type == DependencyType.UNKNOWN
            
            spring_autoconfigure_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-autoconfigure")
            assert spring_autoconfigure_dep.version is None
            
            guava_dep = next(d for d in dependencies if d.name == "com.google.guava:guava")
            assert guava_dep.version is None
        finally:
            os.unlink(file_path)
    
    def test_analyze_static_imports(self):
        """Test analyzing a Java file with static imports."""
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False) as f:
            f.write(b"""
package com.example.app;

import static java.lang.Math.PI;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static com.google.common.base.Preconditions.checkNotNull;

public class MathUtils {
    public void testCircleArea() {
        double radius = 2.0;
        double area = PI * radius * radius;
        assertEquals(12.56, area, 0.01);
        assertTrue(area > 0);
        checkNotNull(area);
    }
}
""")
            file_path = Path(f.name)
        
        try:
            analyzer = JavaImportAnalyzer()
            dependencies = analyzer.analyze(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 2
            
            # Check standard library imports (should be ignored)
            java_lang_deps = [d for d in dependencies if d.name.startswith("java.")]
            assert len(java_lang_deps) == 0
            
            # Check third-party imports
            junit_dep = next(d for d in dependencies if d.name == "junit:junit")
            assert junit_dep.version is None
            
            guava_dep = next(d for d in dependencies if d.name == "com.google.guava:guava")
            assert guava_dep.version is None
        finally:
            os.unlink(file_path)
    
    def test_analyze_wildcard_imports(self):
        """Test analyzing a Java file with wildcard imports."""
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False) as f:
            f.write(b"""
package com.example.app;

import java.util.*;
import java.io.*;
import org.springframework.boot.*;
import org.springframework.boot.autoconfigure.*;
import com.google.common.collect.*;

public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
        List<String> list = new ArrayList<>();
        ImmutableList<String> immutableList = ImmutableList.of("item");
    }
}
""")
            file_path = Path(f.name)
        
        try:
            analyzer = JavaImportAnalyzer()
            dependencies = analyzer.analyze(file_path)
            
            # Check that we found the expected dependencies
            assert len(dependencies) == 3
            
            # Check standard library imports (should be ignored)
            java_util_deps = [d for d in dependencies if d.name.startswith("java.")]
            assert len(java_util_deps) == 0
            
            # Check third-party imports
            spring_deps = [d for d in dependencies if d.name.startswith("org.springframework")]
            assert len(spring_deps) == 2
            
            spring_boot_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot")
            assert spring_boot_dep.version is None
            
            spring_autoconfigure_dep = next(d for d in dependencies if d.name == "org.springframework.boot:spring-boot-autoconfigure")
            assert spring_autoconfigure_dep.version is None
            
            guava_dep = next(d for d in dependencies if d.name == "com.google.guava:guava")
            assert guava_dep.version is None
        finally:
            os.unlink(file_path)
    
    def test_analyze_empty_file(self):
        """Test analyzing an empty Java file."""
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False) as f:
            f.write(b"")
            file_path = Path(f.name)
        
        try:
            analyzer = JavaImportAnalyzer()
            dependencies = analyzer.analyze(file_path)
            
            # Should return an empty list for an empty file
            assert len(dependencies) == 0
        finally:
            os.unlink(file_path)
    
    def test_analyze_no_imports(self):
        """Test analyzing a Java file with no imports."""
        with tempfile.NamedTemporaryFile(suffix=".java", delete=False) as f:
            f.write(b"""
package com.example.app;

public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
""")
            file_path = Path(f.name)
        
        try:
            analyzer = JavaImportAnalyzer()
            dependencies = analyzer.analyze(file_path)
            
            # Should return an empty list for a file with no imports
            assert len(dependencies) == 0
        finally:
            os.unlink(file_path)
