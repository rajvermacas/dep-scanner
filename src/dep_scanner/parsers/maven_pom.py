"""Parser for Maven pom.xml files."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set

from dep_scanner.exceptions import ParsingError
from dep_scanner.parsers.base import DependencyParser, ParserRegistry
from dep_scanner.scanner import Dependency, DependencyType


class MavenPomParser(DependencyParser):
    """Parser for Maven pom.xml files.
    
    This parser extracts dependencies from Maven pom.xml files, which typically
    have the following structure:
    
    ```xml
    <project>
      <dependencies>
        <dependency>
          <groupId>junit</groupId>
          <artifactId>junit</artifactId>
          <version>4.12</version>
          <scope>test</scope>
        </dependency>
      </dependencies>
    </project>
    ```
    
    It also handles property resolution for version variables like ${junit.version}
    and parent POM references.
    """
    
    # Define supported file extensions and filenames
    supported_extensions: Set[str] = {".xml"}
    supported_filenames: Set[str] = {"pom.xml"}
    
    # XML namespaces in Maven POM files
    NAMESPACES = {
        "mvn": "http://maven.apache.org/POM/4.0.0"
    }
    
    def parse(self, file_path: Path) -> List[Dependency]:
        """Parse dependencies from a Maven pom.xml file.
        
        Args:
            file_path: Path to the pom.xml file
            
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
                raise ParsingError(file_path, "Empty pom.xml file")
            
            try:
                # Parse XML content
                tree = ET.fromstring(content)
                
                # Extract properties for variable resolution
                properties = self._extract_properties(tree)
                
                # Extract parent POM information if present
                parent = self._extract_parent(tree)
                if parent:
                    dependencies.append(parent)
                
                # Find all dependency elements
                # Try with namespace first, then without namespace
                dependency_elements = tree.findall(".//mvn:dependencies/mvn:dependency", self.NAMESPACES)
                if not dependency_elements:
                    dependency_elements = tree.findall(".//dependencies/dependency")
                
                # Process each dependency
                for dep_elem in dependency_elements:
                    dependency = self._process_dependency(dep_elem, properties, file_path)
                    if dependency:
                        dependencies.append(dependency)
                
                return dependencies
            except ET.ParseError as e:
                raise ParsingError(file_path, f"Invalid XML format: {str(e)}")
        except Exception as e:
            if not isinstance(e, ParsingError):
                raise ParsingError(file_path, f"Error parsing Maven pom.xml file: {str(e)}")
            raise
    
    def _extract_properties(self, tree: ET.Element) -> Dict[str, str]:
        """Extract properties from the pom.xml file for variable resolution.
        
        Args:
            tree: XML element tree of the pom.xml file
            
        Returns:
            Dictionary of property names to values
        """
        properties = {}
        
        # Try with namespace first, then without namespace
        props_elem = tree.find(".//mvn:properties", self.NAMESPACES)
        if props_elem is None:
            props_elem = tree.find(".//properties")
        
        if props_elem is not None:
            for prop in props_elem:
                # Remove namespace prefix if present
                tag = prop.tag
                if "}" in tag:
                    tag = tag.split("}", 1)[1]
                
                properties[tag] = prop.text or ""
        
        return properties
    
    def _extract_parent(self, tree: ET.Element) -> Optional[Dependency]:
        """Extract parent POM information.
        
        Args:
            tree: XML element tree of the pom.xml file
            
        Returns:
            Parent dependency or None if not found
        """
        # Try with namespace first, then without namespace
        parent_elem = tree.find(".//mvn:parent", self.NAMESPACES)
        if parent_elem is None:
            parent_elem = tree.find(".//parent")
        
        if parent_elem is not None:
            # Extract parent groupId, artifactId, and version
            group_id = self._get_element_text(parent_elem, "groupId")
            artifact_id = self._get_element_text(parent_elem, "artifactId")
            version = self._get_element_text(parent_elem, "version")
            
            if group_id and artifact_id:
                return Dependency(
                    name=f"{group_id}:{artifact_id}",
                    version=version,
                    source_file="parent_pom",
                    dependency_type=DependencyType.UNKNOWN
                )
        
        return None
    
    def _process_dependency(self, dep_elem: ET.Element, properties: Dict[str, str], file_path: Path) -> Optional[Dependency]:
        """Process a single dependency element.
        
        Args:
            dep_elem: Dependency XML element
            properties: Properties for variable resolution
            file_path: Path to the pom.xml file
            
        Returns:
            Dependency object or None if invalid
        """
        # Extract groupId, artifactId, and version
        group_id = self._get_element_text(dep_elem, "groupId")
        artifact_id = self._get_element_text(dep_elem, "artifactId")
        version = self._get_element_text(dep_elem, "version")
        
        # Skip if groupId or artifactId is missing
        if not group_id or not artifact_id:
            return None
        
        # Resolve version if it uses property syntax ${property.name}
        if version and "${" in version and "}" in version:
            version = self._resolve_property(version, properties)
        
        return Dependency(
            name=f"{group_id}:{artifact_id}",
            version=version,
            source_file=str(file_path),
            dependency_type=DependencyType.UNKNOWN
        )
    
    def _get_element_text(self, parent: ET.Element, tag_name: str) -> Optional[str]:
        """Get the text content of a child element.
        
        Args:
            parent: Parent XML element
            tag_name: Tag name of the child element
            
        Returns:
            Text content or None if not found
        """
        # Try with namespace first, then without namespace
        elem = parent.find(f"mvn:{tag_name}", self.NAMESPACES)
        if elem is None:
            elem = parent.find(tag_name)
        
        return elem.text.strip() if elem is not None and elem.text else None
    
    def _resolve_property(self, value: str, properties: Dict[str, str]) -> str:
        """Resolve property references in values.
        
        Args:
            value: Value with property references (e.g., "${junit.version}")
            properties: Properties dictionary
            
        Returns:
            Resolved value
        """
        # Extract property name from ${property.name} syntax
        property_pattern = r"\$\{([^}]+)\}"
        
        def replace_property(match):
            prop_name = match.group(1)
            return properties.get(prop_name, match.group(0))
        
        # Replace all property references
        resolved = re.sub(property_pattern, replace_property, value)
        
        return resolved


# Register the parser
ParserRegistry.register("maven_pom", MavenPomParser)
