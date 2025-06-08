"""Analyzer for Scala import statements."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from dependency_scanner_tool.analyzers.base import ImportAnalyzer, ImportAnalyzerRegistry
from dependency_scanner_tool.scanner import Dependency, DependencyType


class ScalaImportAnalyzer(ImportAnalyzer):
    """Analyzer for Scala import statements.
    
    This analyzer extracts import statements from Scala source files and
    converts them to dependencies. It handles various Scala import patterns
    including regular imports, wildcard imports, selective imports, and aliased imports.
    
    Examples of Scala import statements:
    ```scala
    import scala.collection.mutable.Map                    // Standard import
    import java.util.{List, ArrayList}                     // Selective import
    import org.apache.spark._                              // Wildcard import
    import com.example.package.{Class1, Class2 => Alias}   // Aliased import
    import scala.util.Try                                  // Standard library
    ```
    
    The analyzer ignores standard library imports (those starting with 'scala.')
    and Java standard library imports, focusing on third-party dependencies.
    """
    
    # Define supported file extensions
    supported_extensions: Set[str] = {".scala", ".sc"}
    
    # Regular expressions for extracting import statements
    # Match various Scala import patterns
    IMPORT_REGEX = re.compile(r'import\s+([^;\n]+)(?:[;\n]|$)', re.MULTILINE)
    
    # Scala standard library packages to ignore
    SCALA_STDLIB_PACKAGES = {
        "scala", "java", "javax", "sun", "com.sun", "org.xml", "org.w3c"
    }
    
    # Package to Maven artifact mapping for common Scala/Java libraries
    PACKAGE_TO_ARTIFACT_MAPPING: Dict[str, str] = {
        # Scala specific libraries
        "org.scalatest": "org.scalatest:scalatest",
        "org.scalactic": "org.scalactic:scalactic",
        "cats.effect": "org.typelevel:cats-effect",
        "cats": "org.typelevel:cats-core",
        "akka.actor": "com.typesafe.akka:akka-actor",
        "akka.http": "com.typesafe.akka:akka-http",
        "akka.stream": "com.typesafe.akka:akka-stream",
        "play.api": "com.typesafe.play:play",
        "zio": "dev.zio:zio",
        "io.circe": "io.circe:circe-core",
        "org.json4s": "org.json4s:json4s-native",
        "slick": "com.typesafe.slick:slick",
        "doobie": "org.tpolecat:doobie-core",
        "shapeless": "com.chuusai:shapeless",
        "scalaz": "org.scalaz:scalaz-core",
        "fs2": "co.fs2:fs2-core",
        "monix": "io.monix:monix",
        
        # Apache Spark
        "org.apache.spark": "org.apache.spark:spark-core",
        "org.apache.spark.sql": "org.apache.spark:spark-sql",
        "org.apache.spark.streaming": "org.apache.spark:spark-streaming",
        "org.apache.spark.mllib": "org.apache.spark:spark-mllib",
        
        # Common Java libraries used in Scala
        "org.springframework": "org.springframework:spring-core",
        "com.google.common": "com.google.guava:guava",
        "com.google.gson": "com.google.code.gson:gson",
        "com.fasterxml.jackson": "com.fasterxml.jackson.core:jackson-core",
        "org.apache.commons.lang": "org.apache.commons:commons-lang3",
        "org.apache.commons.io": "commons-io:commons-io",
        "org.slf4j": "org.slf4j:slf4j-api",
        "ch.qos.logback": "ch.qos.logback:logback-classic",
        "org.apache.logging.log4j": "org.apache.logging.log4j:log4j-core",
        "junit": "junit:junit",
        "org.mockito": "org.mockito:mockito-core",
        "org.scalacheck": "org.scalacheck:scalacheck",
        
        # Configuration libraries
        "com.typesafe.config": "com.typesafe:config",
        "pureconfig": "com.github.pureconfig:pureconfig",
        
        # HTTP libraries
        "sttp": "com.softwaremill.sttp:core",
        "requests": "com.lihaoyi:requests",
        
        # Database libraries
        "org.postgresql": "org.postgresql:postgresql",
        "mysql": "mysql:mysql-connector-java",
        "org.h2": "com.h2database:h2",
    }
    
    def analyze(self, file_path: Path) -> List[Dependency]:
        """Analyze a Scala file for import statements.
        
        Args:
            file_path: Path to the Scala file
            
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
            
            # Remove comments to avoid false positives
            content = self._remove_comments(content)
            
            # Extract all import statements
            for match in self.IMPORT_REGEX.finditer(content):
                import_statement = match.group(1).strip()
                import_packages = self._parse_import_statement(import_statement)
                
                for import_path in import_packages:
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
            print(f"Error analyzing Scala file {file_path}: {str(e)}")
            return []
    
    def _remove_comments(self, content: str) -> str:
        """Remove Scala comments from the content.
        
        Args:
            content: Original file content
            
        Returns:
            Content with comments removed
        """
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        return content
    
    def _parse_import_statement(self, import_statement: str) -> List[str]:
        """Parse a Scala import statement to extract package names.
        
        Args:
            import_statement: The import statement to parse
            
        Returns:
            List of package names extracted from the import
        """
        import_packages = []
        
        # Handle different import patterns
        if '{' in import_statement and '}' in import_statement:
            # Selective import: package.{Class1, Class2, Class3 => Alias}
            base_package = import_statement.split('{')[0].strip()
            # Remove trailing dot if present
            if base_package.endswith('.'):
                base_package = base_package[:-1]
            imports_part = import_statement.split('{')[1].split('}')[0]
            
            # For selective imports, we're interested in the base package
            if base_package:
                import_packages.append(base_package)
        
        elif import_statement.endswith('._'):
            # Wildcard import: package._
            base_package = import_statement[:-2].strip()
            if base_package:
                import_packages.append(base_package)
        
        else:
            # Standard import: package.Class or package.object
            # We want the package, not the class/object
            parts = import_statement.split('.')
            if len(parts) > 1:
                # Take all parts except the last one (which is likely a class/object)
                package = '.'.join(parts[:-1])
                if package:
                    import_packages.append(package)
            else:
                # Single part import
                if import_statement:
                    import_packages.append(import_statement)
        
        return import_packages
    
    def _should_process_import(self, import_path: str) -> bool:
        """Determine if an import should be processed.
        
        Args:
            import_path: Import path to check
            
        Returns:
            True if the import should be processed, False otherwise
        """
        # Skip standard library imports
        for stdlib_pkg in self.SCALA_STDLIB_PACKAGES:
            if import_path.startswith(stdlib_pkg + ".") or import_path == stdlib_pkg:
                return False
        
        # Skip empty imports
        if not import_path.strip():
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
            if len(parts) >= 3:
                # Use the first two parts of the package as groupId
                group_id = ".".join(parts[:2])
                # Use the third part as artifactId
                artifact_id = parts[2]
                artifact_name = f"{group_id}:{artifact_id}"
            elif len(parts) == 2:
                # Two part package name - treat the whole thing as the package name
                artifact_name = import_path
            elif len(parts) == 1:
                # Single part package name - use as is
                artifact_name = parts[0]
        
        if artifact_name:
            return Dependency(
                name=artifact_name,
                version=None,
                source_file=str(file_path),
                dependency_type=DependencyType.UNKNOWN
            )
        
        return None


# Register the analyzer
ImportAnalyzerRegistry.register("scala", ScalaImportAnalyzer)