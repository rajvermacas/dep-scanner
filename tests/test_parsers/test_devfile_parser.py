"""Tests for DevfileParser."""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from dependency_scanner_tool.exceptions import ParsingError
from dependency_scanner_tool.parsers.devfile_parser import DevfileParser
from dependency_scanner_tool.scanner import Dependency, DependencyType


class TestDevfileParser:
    """Test cases for DevfileParser."""
    
    @pytest.fixture
    def parser(self):
        """Create a DevfileParser instance for testing."""
        return DevfileParser()
    
    @pytest.fixture
    def test_data_dir(self):
        """Get the test data directory."""
        return Path(__file__).parent.parent / "test_data" / "devfile_samples"
    
    def test_supported_extensions(self, parser):
        """Test that parser supports correct file extensions."""
        assert ".yaml" in parser.supported_extensions
        assert ".yml" in parser.supported_extensions
        
    def test_supported_filenames(self, parser):
        """Test that parser supports correct filenames."""
        assert "devfile.yaml" in parser.supported_filenames
        assert "devfile.yml" in parser.supported_filenames
    
    def test_can_parse_devfile_names(self, parser):
        """Test can_parse method with devfile filenames."""
        assert parser.can_parse(Path("devfile.yaml"))
        assert parser.can_parse(Path("devfile.yml"))
        assert parser.can_parse(Path("project/devfile.yaml"))
        
    def test_can_parse_devcontainer_devfile(self, parser):
        """Test can_parse method with .devcontainer/devfile.yaml."""
        assert parser.can_parse(Path(".devcontainer/devfile.yaml"))
        assert parser.can_parse(Path("project/.devcontainer/devfile.yml"))
        
    def test_can_parse_non_devfile(self, parser):
        """Test can_parse method with non-devfile names."""
        assert not parser.can_parse(Path("requirements.txt"))
        assert not parser.can_parse(Path("package.json"))
        # Note: docker-compose.yml might be detected as potential devfile
        # through content analysis if it contains devfile-like keywords
        # This is acceptable behavior for the content-detection feature
    
    def test_is_valid_devfile_valid(self):
        """Test _is_valid_devfile with valid devfile data."""
        valid_devfile = {
            "schemaVersion": "2.2.0",
            "metadata": {"name": "test"},
            "components": [
                {
                    "name": "test-container",
                    "container": {"image": "node:16"}
                }
            ]
        }
        assert DevfileParser._is_valid_devfile(valid_devfile)
    
    def test_is_valid_devfile_invalid_missing_schema(self):
        """Test _is_valid_devfile with missing schemaVersion."""
        invalid_devfile = {
            "metadata": {"name": "test"},
            "components": []
        }
        assert not DevfileParser._is_valid_devfile(invalid_devfile)
    
    def test_is_valid_devfile_invalid_missing_sections(self):
        """Test _is_valid_devfile with missing required sections."""
        invalid_devfile = {
            "schemaVersion": "2.2.0",
            "metadata": {"name": "test"}
            # Missing components, commands, events, projects
        }
        assert not DevfileParser._is_valid_devfile(invalid_devfile)
    
    def test_is_valid_devfile_not_dict(self):
        """Test _is_valid_devfile with non-dict input."""
        assert not DevfileParser._is_valid_devfile("not a dict")
        assert not DevfileParser._is_valid_devfile(None)
        assert not DevfileParser._is_valid_devfile([])
    
    def test_parse_simple_container_devfile(self, parser, test_data_dir):
        """Test parsing a simple container devfile."""
        devfile_path = test_data_dir / "simple_container_devfile.yaml"
        dependencies = parser.parse(devfile_path)
        
        # Should find the python:3.9-slim container
        assert len(dependencies) == 1
        dep = dependencies[0]
        assert dep.name == "python"
        assert dep.version == "3.9-slim"
        assert dep.source_file == str(devfile_path)
        assert dep.dependency_type == DependencyType.UNKNOWN
    
    def test_parse_kubernetes_devfile(self, parser, test_data_dir):
        """Test parsing devfile with Kubernetes components."""
        devfile_path = test_data_dir / "kubernetes_devfile.yaml"
        dependencies = parser.parse(devfile_path)
        
        # Should find:
        # 1. node:16-alpine container
        # 2. postgres-deployment.yaml reference
        # 3. redis inline kubernetes component
        # 4. app-storage volume
        expected_names = [
            "node",
            "k8s-resource:postgres-deployment.yaml", 
            "k8s-inline:redis-cache",
            "devfile-volume:app-storage"
        ]
        
        assert len(dependencies) == 4
        actual_names = [dep.name for dep in dependencies]
        assert set(actual_names) == set(expected_names)
        
        # Check specific dependencies
        node_dep = next(dep for dep in dependencies if dep.name == "node")
        assert node_dep.version == "16-alpine"
        
        volume_dep = next(dep for dep in dependencies if dep.name == "devfile-volume:app-storage")
        assert volume_dep.version == "2Gi"
    
    def test_parse_plugin_devfile(self, parser, test_data_dir):
        """Test parsing devfile with plugin components."""
        devfile_path = test_data_dir / "plugin_devfile.yaml"
        dependencies = parser.parse(devfile_path)
        
        # Should find:
        # 1. eclipse/che-java11-maven:latest container
        # 2. redhat/java11/latest plugin
        # 3. vscode-java plugin URI
        # 4. project-storage volume
        expected_names = [
            "eclipse/che-java11-maven",  # User/repo format preserved
            "devfile-plugin:redhat/java11/latest",
            "devfile-plugin-uri:https://github.com/eclipse/che-plugin-registry/raw/main/v3/plugins/redhat/vscode-java/0.82.0/meta.yaml",
            "devfile-volume:project-storage"
        ]
        
        assert len(dependencies) == 4
        actual_names = [dep.name for dep in dependencies]
        assert set(actual_names) == set(expected_names)
        
        # Check plugin version
        plugin_dep = next(dep for dep in dependencies if dep.name == "devfile-plugin:redhat/java11/latest")
        assert plugin_dep.version == "0.63.0"
        
        # Check container version
        container_dep = next(dep for dep in dependencies if dep.name == "eclipse/che-java11-maven")
        assert container_dep.version == "latest"
    
    def test_parse_devcontainer_devfile(self, parser, test_data_dir):
        """Test parsing devfile with image component."""
        devfile_path = test_data_dir / "devcontainer_devfile.yaml"
        dependencies = parser.parse(devfile_path)
        
        # Should find:
        # 1. typescript-node container from mcr.microsoft.com
        # 2. postgres image component
        expected_names = ["typescript-node", "postgres"]
        
        assert len(dependencies) == 2
        actual_names = [dep.name for dep in dependencies]
        assert set(actual_names) == set(expected_names)
        
        # Check versions
        typescript_dep = next(dep for dep in dependencies if dep.name == "typescript-node")
        assert typescript_dep.version == "16"
        
        postgres_dep = next(dep for dep in dependencies if dep.name == "postgres")
        assert postgres_dep.version == "13-alpine"
    
    def test_parse_dotnet_devcontainer_devfile(self, parser, test_data_dir):
        """Test parsing devfile in .devcontainer directory."""
        devfile_path = test_data_dir / ".devcontainer" / "devfile.yaml"
        dependencies = parser.parse(devfile_path)
        
        # Should find dotnet/sdk:6.0
        assert len(dependencies) == 1
        dep = dependencies[0]
        assert dep.name == "sdk"  # Registry prefix removed
        assert dep.version == "6.0"
        assert dep.source_file == str(devfile_path)
    
    def test_parse_file_not_exists(self, parser):
        """Test parsing non-existent file."""
        with pytest.raises(ParsingError, match="File does not exist"):
            parser.parse(Path("nonexistent.yaml"))
    
    def test_parse_invalid_devfile(self, parser, test_data_dir):
        """Test parsing invalid devfile."""
        devfile_path = test_data_dir / "invalid_devfile.yaml"
        with pytest.raises(ParsingError, match="File does not appear to be a valid devfile"):
            parser.parse(devfile_path)
    
    def test_parse_not_a_devfile(self, parser, test_data_dir):
        """Test parsing YAML that's not a devfile."""
        devfile_path = test_data_dir / "not_a_devfile.yaml"
        with pytest.raises(ParsingError, match="File does not appear to be a valid devfile"):
            parser.parse(devfile_path)
    
    @patch('dependency_scanner_tool.parsers.devfile_parser.yaml', None)
    def test_parse_no_yaml_library(self, parser, test_data_dir):
        """Test parsing when YAML library is not available."""
        devfile_path = test_data_dir / "simple_container_devfile.yaml"
        with pytest.raises(ParsingError, match="YAML parsing library not available"):
            parser.parse(devfile_path)
    
    def test_parse_container_image_simple(self, parser):
        """Test _parse_container_image with simple images."""
        assert parser._parse_container_image("python") == ("python", None)
        assert parser._parse_container_image("python:3.9") == ("python", "3.9")
        assert parser._parse_container_image("python:3.9-slim") == ("python", "3.9-slim")
    
    def test_parse_container_image_registry(self, parser):
        """Test _parse_container_image with registry prefixes."""
        assert parser._parse_container_image("docker.io/library/python:3.9") == ("python", "3.9")
        assert parser._parse_container_image("mcr.microsoft.com/dotnet/sdk:6.0") == ("sdk", "6.0")
        assert parser._parse_container_image("gcr.io/my-project/my-app:latest") == ("my-app", "latest")
    
    def test_parse_container_image_user_repo(self, parser):
        """Test _parse_container_image with user/repo format."""
        assert parser._parse_container_image("eclipse/che-java11-maven:latest") == ("eclipse/che-java11-maven", "latest")
        assert parser._parse_container_image("user/repo:v1.0") == ("user/repo", "v1.0")
    
    def test_parse_container_image_with_digest(self, parser):
        """Test _parse_container_image with digest."""
        image_with_digest = "python:3.9@sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        assert parser._parse_container_image(image_with_digest) == ("python", "3.9")
    
    def test_parse_container_image_invalid(self, parser):
        """Test _parse_container_image with invalid inputs."""
        assert parser._parse_container_image("") == (None, None)
        assert parser._parse_container_image(None) == (None, None)
        assert parser._parse_container_image("   ") == (None, None)
        assert parser._parse_container_image(123) == (None, None)
    
    def test_extract_container_dependencies_no_components(self, parser):
        """Test _extract_container_dependencies with no components."""
        data = {"schemaVersion": "2.2.0"}
        deps = parser._extract_container_dependencies(data, Path("test.yaml"))
        assert len(deps) == 0
    
    def test_extract_container_dependencies_empty_components(self, parser):
        """Test _extract_container_dependencies with empty components."""
        data = {
            "schemaVersion": "2.2.0",
            "components": []
        }
        deps = parser._extract_container_dependencies(data, Path("test.yaml"))
        assert len(deps) == 0
    
    def test_extract_container_dependencies_invalid_component(self, parser):
        """Test _extract_container_dependencies with invalid component format."""
        data = {
            "schemaVersion": "2.2.0",
            "components": ["not_a_dict", None, 123]
        }
        deps = parser._extract_container_dependencies(data, Path("test.yaml"))
        assert len(deps) == 0
    
    def test_extract_kubernetes_dependencies_openshift(self, parser):
        """Test _extract_kubernetes_dependencies with OpenShift component."""
        data = {
            "schemaVersion": "2.2.0",
            "components": [
                {
                    "name": "openshift-component",
                    "openshift": {
                        "reference": "openshift-deployment.yaml"
                    }
                }
            ]
        }
        deps = parser._extract_kubernetes_dependencies(data, Path("test.yaml"))
        assert len(deps) == 1
        assert deps[0].name == "openshift-resource:openshift-deployment.yaml"
    
    def test_can_parse_with_content_detection(self, parser, tmp_path):
        """Test can_parse method with content-based detection."""
        # Create a real test file with devfile content
        devfile_content = """schemaVersion: 2.2.0
components:
  - name: test
    container:
      image: node:16
"""
        
        test_file = tmp_path / "some-config.yaml"
        test_file.write_text(devfile_content)
        
        # Should detect this as a devfile based on content
        result = parser.can_parse(test_file)
        assert result
    
    def test_can_parse_with_path_hints(self, parser):
        """Test can_parse method with path-based hints."""
        # Should detect based on filename containing 'devfile'
        assert parser.can_parse(Path("my-devfile-config.yaml"))
        assert parser.can_parse(Path("project/devpod-setup.yml"))
    
    @patch('dependency_scanner_tool.parsers.devfile_parser.yaml')
    def test_parse_yaml_error(self, mock_yaml, parser, tmp_path):
        """Test parsing with YAML syntax error."""
        mock_yaml.YAMLError = Exception  # Mock the exception class
        mock_yaml.safe_load.side_effect = mock_yaml.YAMLError("Invalid YAML syntax")
        
        test_file = tmp_path / "test.yaml"
        test_file.write_text("invalid: yaml: content:")
        
        with pytest.raises(ParsingError, match="Invalid YAML syntax"):
            parser.parse(test_file)