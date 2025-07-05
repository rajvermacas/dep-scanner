"""Test cases for ARM template scanner."""
import pytest
import tempfile
import json
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.arm_template import ARMTemplateScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType


def test_arm_template_scanner_initialization():
    """Test ARMTemplateScanner initialization."""
    scanner = ARMTemplateScanner()
    
    assert scanner.get_infrastructure_type() == InfrastructureType.IaC
    supported_patterns = scanner.get_supported_file_patterns()
    assert "*.json" in supported_patterns
    assert "azuredeploy.json" in supported_patterns
    assert "mainTemplate.json" in supported_patterns


def test_arm_template_scanner_can_handle_file():
    """Test ARMTemplateScanner file handling."""
    scanner = ARMTemplateScanner()
    
    assert scanner.can_handle_file(Path("azuredeploy.json")) is True
    assert scanner.can_handle_file(Path("mainTemplate.json")) is True
    assert scanner.can_handle_file(Path("template.json")) is True
    assert scanner.can_handle_file(Path("arm-template.json")) is True
    assert scanner.can_handle_file(Path("test.txt")) is False
    assert scanner.can_handle_file(Path("main.tf")) is False


def test_arm_template_scanner_basic_vm_resource():
    """Test scanning basic Azure VM ARM template resource."""
    scanner = ARMTemplateScanner()
    
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {},
        "variables": {},
        "resources": [
            {
                "type": "Microsoft.Compute/virtualMachines",
                "apiVersion": "2021-04-01",
                "name": "myVM",
                "location": "[resourceGroup().location]",
                "properties": {
                    "hardwareProfile": {
                        "vmSize": "Standard_B1s"
                    },
                    "osProfile": {
                        "computerName": "myVM",
                        "adminUsername": "azureuser"
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(arm_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.IaC
        assert component.name == "myVM"
        assert component.service == "arm-template"
        assert component.subtype == "Microsoft.Compute/virtualMachines"
        assert component.configuration["properties"]["hardwareProfile"]["vmSize"] == "Standard_B1s"


def test_arm_template_scanner_storage_account():
    """Test scanning ARM template with Azure Storage Account."""
    scanner = ARMTemplateScanner()
    
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "resources": [
            {
                "type": "Microsoft.Storage/storageAccounts",
                "apiVersion": "2021-04-01",
                "name": "mystorageaccount",
                "location": "East US",
                "sku": {
                    "name": "Standard_LRS"
                },
                "kind": "StorageV2",
                "properties": {
                    "accessTier": "Hot"
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(arm_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.name == "mystorageaccount"
        assert component.subtype == "Microsoft.Storage/storageAccounts"
        assert component.configuration["sku"]["name"] == "Standard_LRS"


def test_arm_template_scanner_multiple_resources():
    """Test scanning ARM template with multiple Azure resources."""
    scanner = ARMTemplateScanner()
    
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "resources": [
            {
                "type": "Microsoft.Network/virtualNetworks",
                "apiVersion": "2021-02-01",
                "name": "myVNet",
                "location": "East US",
                "properties": {
                    "addressSpace": {
                        "addressPrefixes": ["10.0.0.0/16"]
                    }
                }
            },
            {
                "type": "Microsoft.Network/publicIPAddresses",
                "apiVersion": "2021-02-01",
                "name": "myPublicIP",
                "location": "East US",
                "properties": {
                    "publicIPAllocationMethod": "Static"
                }
            },
            {
                "type": "Microsoft.Network/networkSecurityGroups",
                "apiVersion": "2021-02-01",
                "name": "myNSG",
                "location": "East US",
                "properties": {
                    "securityRules": []
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(arm_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 3
        resource_names = [comp.name for comp in components]
        assert "myVNet" in resource_names
        assert "myPublicIP" in resource_names
        assert "myNSG" in resource_names


def test_arm_template_scanner_with_parameters():
    """Test scanning ARM template with parameters."""
    scanner = ARMTemplateScanner()
    
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "vmName": {
                "type": "string",
                "defaultValue": "myVM",
                "metadata": {
                    "description": "Name of the virtual machine"
                }
            },
            "vmSize": {
                "type": "string",
                "defaultValue": "Standard_B1s",
                "allowedValues": [
                    "Standard_B1s",
                    "Standard_B2s",
                    "Standard_D2s_v3"
                ]
            }
        },
        "resources": [
            {
                "type": "Microsoft.Compute/virtualMachines",
                "apiVersion": "2021-04-01",
                "name": "[parameters('vmName')]",
                "location": "East US",
                "properties": {
                    "hardwareProfile": {
                        "vmSize": "[parameters('vmSize')]"
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(arm_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should detect parameters and resources
        assert len(components) >= 1
        
        # Check that we have the resource
        resource_components = [c for c in components if c.subtype == "Microsoft.Compute/virtualMachines"]
        assert len(resource_components) == 1


def test_arm_template_scanner_app_service():
    """Test scanning ARM template with Azure App Service."""
    scanner = ARMTemplateScanner()
    
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "resources": [
            {
                "type": "Microsoft.Web/serverfarms",
                "apiVersion": "2021-02-01",
                "name": "myAppServicePlan",
                "location": "East US",
                "sku": {
                    "name": "F1",
                    "tier": "Free"
                },
                "properties": {}
            },
            {
                "type": "Microsoft.Web/sites",
                "apiVersion": "2021-02-01",
                "name": "myWebApp",
                "location": "East US",
                "dependsOn": [
                    "[resourceId('Microsoft.Web/serverfarms', 'myAppServicePlan')]"
                ],
                "properties": {
                    "serverFarmId": "[resourceId('Microsoft.Web/serverfarms', 'myAppServicePlan')]"
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(arm_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 2
        resource_types = [comp.subtype for comp in components]
        assert "Microsoft.Web/serverfarms" in resource_types
        assert "Microsoft.Web/sites" in resource_types


def test_arm_template_scanner_invalid_json():
    """Test scanning invalid JSON ARM template file."""
    scanner = ARMTemplateScanner()
    
    invalid_json = '{"invalid": json content}'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(invalid_json)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for invalid files
        assert components == []


def test_arm_template_scanner_empty_file():
    """Test scanning empty ARM template file."""
    scanner = ARMTemplateScanner()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("")
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for empty files
        assert components == []


def test_arm_template_scanner_non_arm_template():
    """Test scanning non-ARM template JSON file."""
    scanner = ARMTemplateScanner()
    
    non_arm_json = {
        "name": "test",
        "version": "1.0.0",
        "dependencies": {}
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(non_arm_json, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for non-ARM template files
        assert components == []


def test_arm_template_scanner_sql_database():
    """Test scanning ARM template with Azure SQL Database."""
    scanner = ARMTemplateScanner()
    
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "resources": [
            {
                "type": "Microsoft.Sql/servers",
                "apiVersion": "2021-05-01-preview",
                "name": "mySqlServer",
                "location": "East US",
                "properties": {
                    "administratorLogin": "sqladmin",
                    "administratorLoginPassword": "Password123!"
                }
            },
            {
                "type": "Microsoft.Sql/servers/databases",
                "apiVersion": "2021-05-01-preview",
                "name": "mySqlServer/myDatabase",
                "location": "East US",
                "dependsOn": [
                    "[resourceId('Microsoft.Sql/servers', 'mySqlServer')]"
                ],
                "properties": {
                    "collation": "SQL_Latin1_General_CP1_CI_AS",
                    "edition": "Basic"
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(arm_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 2
        resource_types = [comp.subtype for comp in components]
        assert "Microsoft.Sql/servers" in resource_types
        assert "Microsoft.Sql/servers/databases" in resource_types


def test_arm_template_scanner_file_not_found():
    """Test scanning non-existent file."""
    scanner = ARMTemplateScanner()
    
    components = scanner.scan_file(Path("/non/existent/file.json"))
    
    # Should return empty list for non-existent files
    assert components == []


def test_arm_template_scanner_complex_template():
    """Test scanning complex ARM template with nested resources."""
    scanner = ARMTemplateScanner()
    
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "resources": [
            {
                "type": "Microsoft.ContainerInstance/containerGroups",
                "apiVersion": "2021-03-01",
                "name": "myContainerGroup",
                "location": "East US",
                "properties": {
                    "containers": [
                        {
                            "name": "mycontainer",
                            "properties": {
                                "image": "nginx:latest",
                                "ports": [{"port": 80}]
                            }
                        }
                    ],
                    "osType": "Linux"
                }
            },
            {
                "type": "Microsoft.KeyVault/vaults",
                "apiVersion": "2021-04-01-preview",
                "name": "myKeyVault",
                "location": "East US",
                "properties": {
                    "tenantId": "[subscription().tenantId]",
                    "sku": {
                        "family": "A",
                        "name": "standard"
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(arm_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 2
        
        # Verify all resource types are detected
        resource_types = [comp.subtype for comp in components]
        assert "Microsoft.ContainerInstance/containerGroups" in resource_types
        assert "Microsoft.KeyVault/vaults" in resource_types