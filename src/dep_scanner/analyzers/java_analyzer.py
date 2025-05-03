"""Analyzer for Java import statements."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from dep_scanner.analyzers.base import ImportAnalyzer, ImportAnalyzerRegistry
from dep_scanner.scanner import Dependency, DependencyType


class JavaImportAnalyzer(ImportAnalyzer):
    """Analyzer for Java import statements.
    
    This analyzer extracts import statements from Java source files and
    converts them to dependencies. It handles standard imports, static imports,
    and wildcard imports.
    
    Examples of Java import statements:
    ```java
    import java.util.List;                       // Standard import
    import static org.junit.Assert.assertEquals; // Static import
    import org.springframework.boot.*;           // Wildcard import
    ```
    
    The analyzer ignores standard library imports (those starting with 'java.')
    and focuses on third-party dependencies.
    """
    
    # Define supported file extensions
    supported_extensions: Set[str] = {".java"}
    
    # Regular expressions for extracting import statements
    # Match standard imports: import package.name.Class;
    IMPORT_REGEX = re.compile(r'import\s+(?!static\s+)([^;]+);')
    
    # Match static imports: import static package.name.Class.method;
    STATIC_IMPORT_REGEX = re.compile(r'import\s+static\s+([^;]+);')
    
    # Package to Maven artifact mapping
    # This is a simplified mapping for common Java packages
    PACKAGE_TO_ARTIFACT_MAPPING: Dict[str, str] = {
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
    
    def analyze(self, file_path: Path) -> List[Dependency]:
        """Analyze a Java file for import statements.
        
        Args:
            file_path: Path to the Java file
            
        Returns:
            List of dependencies found in the file
        """
        dependencies = []
        
        try:
            # Read the file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                return []
            
            # Extract standard imports
            for match in self.IMPORT_REGEX.finditer(content):
                import_path = match.group(1).strip()
                if self._should_process_import(import_path):
                    dependency = self._convert_import_to_dependency(import_path, file_path)
                    if dependency:
                        dependencies.append(dependency)
            
            # Extract static imports
            for match in self.STATIC_IMPORT_REGEX.finditer(content):
                import_path = match.group(1).strip()
                # Remove the method name from the import path
                import_path = import_path.rsplit(".", 1)[0]
                if self._should_process_import(import_path):
                    dependency = self._convert_import_to_dependency(import_path, file_path)
                    if dependency:
                        dependencies.append(dependency)
            
            # Remove duplicates based on dependency name
            unique_dependencies = {}
            for dep in dependencies:
                unique_dependencies[dep.name] = dep
            
            return list(unique_dependencies.values())
        except Exception as e:
            # Log the error but don't fail the analysis
            # This allows the scanner to continue with other files
            print(f"Error analyzing Java file {file_path}: {str(e)}")
            return []
    
    def _should_process_import(self, import_path: str) -> bool:
        """Determine if an import should be processed.
        
        Args:
            import_path: Import path to check
            
        Returns:
            True if the import should be processed, False otherwise
        """
        # Skip standard library imports
        if import_path.startswith("java."):
            return False
        
        # Skip javax.* imports that are part of the standard library
        if import_path.startswith("javax.") and not any(
            import_path.startswith(pkg) for pkg in self.PACKAGE_TO_ARTIFACT_MAPPING
            if pkg.startswith("javax.")
        ):
            return False
        
        return True
    
    def _convert_import_to_dependency(
        self, import_path: str, file_path: Path
    ) -> Optional[Dependency]:
        """Convert an import path to a dependency.
        
        Args:
            import_path: Import path to convert
            file_path: Path to the source file
            
        Returns:
            Dependency object or None if the import cannot be mapped
        """
        # Handle wildcard imports
        if import_path.endswith(".*"):
            import_path = import_path[:-2]
        
        # Try to map the import to a Maven artifact
        artifact_name = None
        
        # Find the longest matching package prefix
        matching_prefix = ""
        for package_prefix, artifact in self.PACKAGE_TO_ARTIFACT_MAPPING.items():
            if import_path.startswith(package_prefix) and len(package_prefix) > len(matching_prefix):
                matching_prefix = package_prefix
                artifact_name = artifact
        
        if not artifact_name:
            # If no mapping is found, try to guess the artifact name
            # based on the package structure
            parts = import_path.split(".")
            if len(parts) >= 2:
                # Use the first two parts of the package as groupId
                group_id = ".".join(parts[:2])
                # Use the third part as artifactId, or the second if there's no third
                artifact_id = parts[2] if len(parts) > 2 else parts[1]
                artifact_name = f"{group_id}:{artifact_id}"
        
        if artifact_name:
            return Dependency(
                name=artifact_name,
                version=None,
                source_file=str(file_path),
                dependency_type=DependencyType.UNKNOWN
            )
        
        return None


# Register the analyzer
ImportAnalyzerRegistry.register("java_import", JavaImportAnalyzer)
