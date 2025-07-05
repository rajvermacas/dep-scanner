"""Test cases for infrastructure scanner base functionality."""
import pytest
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.base import (
    BaseInfrastructureScanner,
    InfrastructureScannerRegistry
)
from dependency_scanner_tool.models.infrastructure import (
    InfrastructureType,
    InfrastructureComponent
)


class TestInfrastructureScanner(BaseInfrastructureScanner):
    """Test implementation of BaseInfrastructureScanner."""
    
    def get_supported_file_patterns(self):
        """Return supported file patterns."""
        return ["*.test"]
    
    def get_infrastructure_type(self):
        """Return infrastructure type."""
        return InfrastructureType.IaC
    
    def scan_file(self, file_path):
        """Scan a single file for infrastructure components."""
        return [
            InfrastructureComponent(
                type=self.get_infrastructure_type(),
                name="test_component",
                service="test_service",
                subtype="test_resource",
                configuration={"test": "value"},
                source_file=str(file_path)
            )
        ]


def test_base_infrastructure_scanner_abstract_methods():
    """Test that BaseInfrastructureScanner is properly abstract."""
    with pytest.raises(TypeError):
        # Should not be able to instantiate abstract class
        BaseInfrastructureScanner()


def test_infrastructure_scanner_implementation():
    """Test concrete implementation of BaseInfrastructureScanner."""
    scanner = TestInfrastructureScanner()
    
    # Test supported file patterns
    patterns = scanner.get_supported_file_patterns()
    assert patterns == ["*.test"]
    
    # Test infrastructure type
    infra_type = scanner.get_infrastructure_type()
    assert infra_type == InfrastructureType.IaC
    
    # Test file matching
    assert scanner.can_handle_file(Path("test.test")) is True
    assert scanner.can_handle_file(Path("test.txt")) is False
    
    # Test file scanning
    file_path = Path("test.test")
    components = scanner.scan_file(file_path)
    assert len(components) == 1
    assert components[0].name == "test_component"
    assert components[0].service == "test_service"
    assert components[0].source_file == str(file_path)


def test_infrastructure_scanner_registry():
    """Test InfrastructureScannerRegistry functionality."""
    registry = InfrastructureScannerRegistry()
    
    # Test registration
    scanner = TestInfrastructureScanner()
    registry.register("test", scanner)
    
    # Test retrieval
    retrieved_scanner = registry.get("test")
    assert retrieved_scanner is scanner
    
    # Test get all scanners
    all_scanners = registry.get_all()
    assert "test" in all_scanners
    assert all_scanners["test"] is scanner
    
    # Test get scanner for file
    scanners = registry.get_scanners_for_file(Path("test.test"))
    assert len(scanners) == 1
    assert scanners[0] is scanner
    
    # Test no matching scanners
    scanners = registry.get_scanners_for_file(Path("nomatch.txt"))
    assert len(scanners) == 0


def test_infrastructure_scanner_registry_nonexistent():
    """Test registry behavior with non-existent scanner."""
    registry = InfrastructureScannerRegistry()
    
    with pytest.raises(KeyError):
        registry.get("nonexistent")