"""Parser for Gradle build files."""

import re
from pathlib import Path
from typing import List, Set

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency, DependencyType


class GradleBuildParser(DependencyParser):
    """Parser for Gradle build files.
    
    This parser extracts dependencies from Gradle build files (both Groovy and Kotlin DSL),
    which typically have the following formats:
    
    Groovy DSL:
    ```groovy
    dependencies {
        implementation 'org.springframework.boot:spring-boot-starter-web:2.5.0'
        implementation group: 'com.google.guava', name: 'guava', version: '30.1-jre'
        testImplementation 'junit:junit:4.13.2'
    }
    ```
    
    Kotlin DSL:
    ```kotlin
    dependencies {
        implementation("org.springframework.boot:spring-boot-starter-web:2.5.0")
        implementation(group = "com.google.guava", name = "guava", version = "30.1-jre")
        testImplementation("junit:junit:4.13.2")
    }
    ```
    """
    
    # Define supported file extensions and filenames
    supported_extensions: Set[str] = {".gradle", ".gradle.kts"}
    supported_filenames: Set[str] = {"build.gradle", "build.gradle.kts"}
    
    # Regular expressions for extracting dependencies
    # Match string notation: implementation 'group:artifact:version'
    STRING_NOTATION_REGEX = re.compile(
        r'(?:implementation|api|compile|runtime|testImplementation|testCompile|'
        r'testRuntime|compileOnly|runtimeOnly|annotationProcessor|kapt)\s+'
        r'[\'"]([^:\'"\s]+):([^:\'"\s]+)(?::([^\'"\s]+))?[\'"]'
    )
    
    # Match Kotlin DSL string notation: implementation("group:artifact:version")
    KOTLIN_STRING_NOTATION_REGEX = re.compile(
        r'(?:implementation|api|compile|runtime|testImplementation|testCompile|'
        r'testRuntime|compileOnly|runtimeOnly|annotationProcessor|kapt)'
        r'\s*\(\s*[\'"]([^:\'"\s]+):([^:\'"\s]+)(?::([^\'"\s]+))?[\'"]'
    )
    
    # Match map notation: implementation group: 'group', name: 'artifact', version: 'version'
    MAP_NOTATION_REGEX = re.compile(
        r'(?:implementation|api|compile|runtime|testImplementation|testCompile|'
        r'testRuntime|compileOnly|runtimeOnly|annotationProcessor|kapt)\s+'
        r'(?:group\s*:\s*[\'"]([^\'"\s]+)[\'"]'
        r'\s*,\s*name\s*:\s*[\'"]([^\'"\s]+)[\'"]'
        r'(?:\s*,\s*version\s*:\s*[\'"]([^\'"\s]+)[\'"])?)'
    )
    
    # Match Kotlin DSL map notation: implementation(group = "group", name = "artifact", version = "version")
    KOTLIN_MAP_NOTATION_REGEX = re.compile(
        r'(?:implementation|api|compile|runtime|testImplementation|testCompile|'
        r'testRuntime|compileOnly|runtimeOnly|annotationProcessor|kapt)'
        r'\s*\(\s*group\s*=\s*[\'"]([^\'"\s]+)[\'"]'
        r'\s*,\s*name\s*=\s*[\'"]([^\'"\s]+)[\'"]'
        r'(?:\s*,\s*version\s*=\s*[\'"]([^\'"\s]+)[\'"])?'
    )
    
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a Gradle build file.
        
        Args:
            file_path: Path to the Gradle build file
            
        Returns:
            List of dependencies found in the file
            
        Raises:
            ParsingError: If the file cannot be parsed
        """
        dependencies = []
        
        try:
            # Read the file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                return []
            
            # Extract dependencies using regular expressions
            dependencies.extend(self._extract_dependencies_with_regex(
                content, self.STRING_NOTATION_REGEX, file_path
            ))
            dependencies.extend(self._extract_dependencies_with_regex(
                content, self.KOTLIN_STRING_NOTATION_REGEX, file_path
            ))
            dependencies.extend(self._extract_dependencies_with_regex(
                content, self.MAP_NOTATION_REGEX, file_path
            ))
            dependencies.extend(self._extract_dependencies_with_regex(
                content, self.KOTLIN_MAP_NOTATION_REGEX, file_path
            ))
            
            return dependencies
        except Exception as e:
            if not isinstance(e, ParsingError):
                raise ParsingError(file_path, f"Error parsing Gradle build file: {str(e)}")
            raise
    
    def _extract_dependencies_with_regex(
        self, content: str, regex: re.Pattern, file_path: Path
    ) -> List[Dependency]:
        """Extract dependencies using a regular expression.
        
        Args:
            content: File content
            regex: Regular expression to use
            file_path: Path to the file (for error reporting)
            
        Returns:
            List of dependencies found
        """
        dependencies = []
        
        for match in regex.finditer(content):
            group_id, artifact_id, version = match.groups()
            
            if group_id and artifact_id:
                dependencies.append(
                    Dependency(
                        name=f"{group_id}:{artifact_id}",
                        version=version,
                        source_file=str(file_path),
                        dependency_type=DependencyType.UNKNOWN
                    )
                )
        
        return dependencies


# Register the parser
ParserRegistry.register("gradle_build", GradleBuildParser)
